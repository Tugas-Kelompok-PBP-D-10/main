import json
import math
import re
from decimal import Decimal, InvalidOperation
from html.parser import HTMLParser
from urllib.parse import urlencode

from django.http import JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from .models import Ingredient, Recipe, RecipeInteraction
from .services import get_spoonacular_recipe


class _PlainTextParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag in {"br", "div", "li", "p", "ol", "ul"}:
            self.parts.append("\n")

    def handle_data(self, data):
        self.parts.append(data)


def _plain_text(value):
    if not value:
        return ""
    parser = _PlainTextParser()
    parser.feed(str(value))
    parser.close()
    return re.sub(r"\s+", " ", " ".join(parser.parts)).strip()


def _number(value):
    if value in (None, ""):
        return None
    try:
        number = float(Decimal(str(value)))
    except (InvalidOperation, TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    return int(number) if number.is_integer() else number


def _nutrition_value(value, unit):
    number = _number(value)
    if number is None:
        return None
    return {"value": number, "unit": unit}


def _nutrition_for_recipe(recipe, spoonacular_data=None):
    nutrition = {
        "calories": _nutrition_value(recipe.calories, "kcal"),
        "protein": _nutrition_value(recipe.protein, "g"),
        "carbohydrates": _nutrition_value(recipe.carbohydrates, "g"),
        "fat": _nutrition_value(recipe.fat, "g"),
        "additional": [],
    }

    additional = recipe.additional_nutrition or {}
    if isinstance(additional, dict):
        for name, nutrient in additional.items():
            if isinstance(nutrient, dict):
                value = nutrient.get("value", nutrient.get("amount"))
                unit = str(nutrient.get("unit", "")).strip()
            else:
                value, unit = nutrient, ""
            normalized = _nutrition_value(value, unit)
            if normalized:
                nutrition["additional"].append(
                    {"name": str(name), **normalized}
                )

    local_has_nutrition = any(
        _number(getattr(recipe, field)) is not None
        for field in ("calories", "protein", "carbohydrates", "fat")
    ) or bool(nutrition["additional"])
    if not isinstance(spoonacular_data, dict):
        nutrition["basis"] = recipe.nutrition_basis
        return nutrition

    api_nutrients = {}
    api_nutrition = spoonacular_data.get("nutrition")
    raw_nutrients = (
        api_nutrition.get("nutrients", [])
        if isinstance(api_nutrition, dict)
        else []
    )
    if not isinstance(raw_nutrients, list):
        raw_nutrients = []
    api_has_nutrition = False
    for nutrient in raw_nutrients:
        if isinstance(nutrient, dict):
            api_nutrients[str(nutrient.get("name", "")).casefold()] = nutrient
            api_has_nutrition = api_has_nutrition or (
                _number(nutrient.get("amount")) is not None
            )

    names = {
        "calories": ("calories", "kcal"),
        "protein": ("protein", "g"),
        "carbohydrates": ("carbohydrates", "g"),
        "fat": ("fat", "g"),
    }
    for key, (api_name, fallback_unit) in names.items():
        current = nutrition[key]
        nutrient = api_nutrients.get(api_name)
        if current is None and nutrient:
            nutrition[key] = _nutrition_value(
                nutrient.get("amount"),
                str(nutrient.get("unit") or fallback_unit),
            )

    known_names = {name for name, _unit in names.values()}
    for nutrient in raw_nutrients:
        if not isinstance(nutrient, dict):
            continue
        name = str(nutrient.get("name", "")).strip()
        if not name or name.casefold() in known_names:
            continue
        normalized = _nutrition_value(
            nutrient.get("amount"),
            str(nutrient.get("unit") or ""),
        )
        if normalized:
            nutrition["additional"].append({"name": name, **normalized})

    if api_has_nutrition:
        if not local_has_nutrition or recipe.nutrition_basis == "per_serving":
            nutrition["basis"] = "per_serving"
        else:
            nutrition["basis"] = "mixed"
    else:
        nutrition["basis"] = recipe.nutrition_basis
    return nutrition


def _ingredient_record(ingredient):
    if isinstance(ingredient, str):
        original = _plain_text(ingredient)
        return {"name": original, "amount": None, "unit": "", "original": original}
    if not isinstance(ingredient, dict):
        return None

    name = _plain_text(
        ingredient.get("name") or ingredient.get("originalName") or ""
    )
    original = _plain_text(ingredient.get("original") or name)
    amount = _number(ingredient.get("amount"))
    unit = _plain_text(ingredient.get("unit") or "")
    if not name:
        # Jangan menebak nama atau mem-parsing teks jumlah yang tidak terstruktur.
        name = original
        amount = None
        unit = ""
    return {"name": name, "amount": amount, "unit": unit, "original": original}


def _ingredients_for_recipe(recipe, spoonacular_data=None):
    local_ingredients = recipe.ingredients or []
    if isinstance(local_ingredients, list) and local_ingredients:
        result = []
        for ingredient in local_ingredients:
            record = _ingredient_record(ingredient)
            if record and record["name"]:
                result.append(record)
        if result:
            return result

    if isinstance(spoonacular_data, dict):
        api_ingredients = spoonacular_data.get("extendedIngredients", [])
        if not isinstance(api_ingredients, list):
            api_ingredients = []
        records = [_ingredient_record(ingredient) for ingredient in api_ingredients]
        return [record for record in records if record and record["name"]]
    return []


def _instructions_for_recipe(recipe, spoonacular_data=None):
    if recipe.instructions:
        local_steps = [
            _plain_text(step)
            for step in str(recipe.instructions).splitlines()
            if _plain_text(step)
        ]
        if local_steps:
            return local_steps

    if not isinstance(spoonacular_data, dict):
        return []

    instructions = []
    instruction_groups = spoonacular_data.get("analyzedInstructions", [])
    if not isinstance(instruction_groups, list):
        instruction_groups = []
    for group in instruction_groups:
        if not isinstance(group, dict):
            continue
        steps = group.get("steps", [])
        if not isinstance(steps, list):
            continue
        for step in steps:
            if isinstance(step, dict):
                text = _plain_text(step.get("step", ""))
                if text:
                    instructions.append(text)
    if instructions:
        return instructions

    fallback = _plain_text(spoonacular_data.get("instructions", ""))
    return [fallback] if fallback else []


def _safe_image_url(value):
    value = str(value or "").strip()
    if value.startswith(("https://", "http://")):
        return value
    return ""


def _recipe_detail_payload(recipe, spoonacular_result):
    api_data = spoonacular_result.get("data")
    if not isinstance(api_data, dict):
        api_data = None

    title = recipe.title
    description = _plain_text(recipe.description)
    if not description and api_data:
        description = _plain_text(api_data.get("summary"))

    image_url = _safe_image_url(recipe.image_url)
    if not image_url and api_data:
        image_url = _safe_image_url(api_data.get("image"))

    cooking_time = recipe.cooking_time
    if api_data and not cooking_time:
        cooking_time = api_data.get("readyInMinutes")

    servings = recipe.servings
    if not servings and api_data:
        servings = api_data.get("servings")
    servings = _number(servings)
    if servings is not None and (servings < 1 or not float(servings).is_integer()):
        servings = None

    return {
        "recipe": {
            "id": recipe.pk,
            "spoonacular_id": (
                api_data.get("id") if api_data else recipe.spoonacular_id
            ),
            "title": title,
            "description": description,
            "image": image_url,
            "cooking_time": cooking_time,
            "servings": servings,
            "source": "database+spoonacular" if api_data else "database",
        },
        "nutrition": _nutrition_for_recipe(recipe, api_data),
        "ingredients": _ingredients_for_recipe(recipe, api_data),
        "instructions": _instructions_for_recipe(recipe, api_data),
        "external": {
            "status": spoonacular_result.get("status", "not_configured"),
            "message": spoonacular_result.get("message", ""),
        },
    }


def _interaction_payload(user, recipe):
    if not user.is_authenticated:
        return {
            "authenticated": False,
            "viewed": False,
            "completed": False,
            "viewed_at": None,
            "completed_at": None,
        }

    interaction = RecipeInteraction.objects.filter(
        user=user,
        recipe=recipe,
    ).first()
    return {
        "authenticated": True,
        "viewed": bool(interaction and interaction.viewed_at),
        "completed": bool(interaction and interaction.completed_at),
        "viewed_at": (
            interaction.viewed_at.isoformat()
            if interaction and interaction.viewed_at
            else None
        ),
        "completed_at": (
            interaction.completed_at.isoformat()
            if interaction and interaction.completed_at
            else None
        ),
    }


def _json_error(code, message, status):
    return JsonResponse(
        {"error": {"code": code, "message": message}},
        status=status,
    )


def _get_api_recipe(recipe_id):
    try:
        return Recipe.objects.get(pk=recipe_id)
    except Recipe.DoesNotExist:
        return None


def _authentication_error(request):
    if request.user.is_authenticated:
        return None
    return JsonResponse(
        {
            "error": {
                "code": "authentication_required",
                "message": "Silakan masuk untuk menyimpan interaksi resep.",
            },
            "login_url": _login_url(request, reverse("recipe:home")),
        },
        status=401,
    )


def _login_url(request, next_path=None):
    destination = next_path or request.get_full_path()
    return f"{reverse('authentication:login')}?{urlencode({'next': destination})}"


def recipe_home(request):
    if request.method == "POST":
        ingredient_name = request.POST.get("ingredient_name", "")
        quantity = request.POST.get("quantity", "").strip()
        if ingredient_name.strip():
            for item in ingredient_name.split(","):
                clean_name = item.strip()
                if clean_name:
                    Ingredient.objects.create(
                        user=request.user if request.user.is_authenticated else None,
                        name=clean_name,
                        quantity=quantity,
                    )

    if request.user.is_authenticated:
        saved_ingredients = Ingredient.objects.filter(
            user=request.user
        ).order_by("-created_at")
    else:
        saved_ingredients = Ingredient.objects.filter(
            user=None
        ).order_by("-created_at")

    recipes = list(Recipe.objects.all().order_by("-created_at"))
    statuses = {}
    if request.user.is_authenticated and recipes:
        statuses = {
            row["recipe_id"]: row
            for row in RecipeInteraction.objects.filter(
                user=request.user,
                recipe_id__in=[recipe.pk for recipe in recipes],
            ).values("recipe_id", "viewed_at", "completed_at")
        }

    for recipe in recipes:
        status = statuses.get(recipe.pk, {})
        recipe.interaction_viewed = bool(status.get("viewed_at"))
        recipe.interaction_completed = bool(status.get("completed_at"))

    return render(
        request,
        "Recipe/recipe.html",
        {
            "ingredients": saved_ingredients,
            "recipes": recipes,
            "recipe_login_url": _login_url(request),
        },
    )


@require_GET
def recipe_detail_api(request, recipe_id):
    recipe = _get_api_recipe(recipe_id)
    if recipe is None:
        return _json_error("recipe_not_found", "Resep tidak ditemukan.", 404)
    spoonacular_result = get_spoonacular_recipe(recipe)
    payload = _recipe_detail_payload(recipe, spoonacular_result)
    payload["interaction"] = _interaction_payload(request.user, recipe)
    return JsonResponse(payload)


@require_GET
def recipe_interaction_status(request, recipe_id):
    recipe = _get_api_recipe(recipe_id)
    if recipe is None:
        return _json_error("recipe_not_found", "Resep tidak ditemukan.", 404)
    return JsonResponse(_interaction_payload(request.user, recipe))


@require_POST
def record_recipe_view(request, recipe_id):
    authentication_error = _authentication_error(request)
    if authentication_error:
        return authentication_error

    recipe = _get_api_recipe(recipe_id)
    if recipe is None:
        return _json_error("recipe_not_found", "Resep tidak ditemukan.", 404)
    now = timezone.now()
    interaction, created = RecipeInteraction.objects.get_or_create(
        user=request.user,
        recipe=recipe,
        defaults={"viewed_at": now},
    )
    if not created:
        interaction.viewed_at = now
        interaction.save(update_fields=("viewed_at", "updated_at"))
    return JsonResponse(_interaction_payload(request.user, recipe))


@require_POST
def complete_recipe(request, recipe_id):
    authentication_error = _authentication_error(request)
    if authentication_error:
        return authentication_error

    if request.content_type != "application/json":
        return _json_error(
            "invalid_confirmation",
            "Konfirmasi memasak harus dikirim dalam format JSON.",
            400,
        )
    try:
        payload = json.loads(request.body or b"{}")
    except (TypeError, ValueError):
        return _json_error(
            "invalid_confirmation",
            "Data konfirmasi tidak valid.",
            400,
        )
    if not isinstance(payload, dict) or payload.get("confirmed") is not True:
        return _json_error(
            "confirmation_required",
            "Konfirmasi bahwa resep sudah dimasak terlebih dahulu.",
            400,
        )

    recipe = _get_api_recipe(recipe_id)
    if recipe is None:
        return _json_error("recipe_not_found", "Resep tidak ditemukan.", 404)
    now = timezone.now()
    interaction, created = RecipeInteraction.objects.get_or_create(
        user=request.user,
        recipe=recipe,
        defaults={"viewed_at": now, "completed_at": now},
    )
    if not created:
        update_fields = []
        if not interaction.viewed_at:
            interaction.viewed_at = now
            update_fields.append("viewed_at")
        if not interaction.completed_at:
            interaction.completed_at = now
            update_fields.append("completed_at")
        if update_fields:
            interaction.save(update_fields=(*update_fields, "updated_at"))
    return JsonResponse(_interaction_payload(request.user, recipe))
