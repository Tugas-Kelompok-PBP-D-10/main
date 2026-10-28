import json
from urllib.parse import urlencode

from django.http import JsonResponse
from django.shortcuts import render
from django.urls import NoReverseMatch, reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from .models import Ingredient, Recipe, RecipeInteraction
from .services import get_recipe_by_id, get_recipe_detail

import uuid
from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction

from tracker.integrations import (
    RecipeSnapshot,
    complete_recipe_cooking,
)


def make_recipe_snapshot(recipe):
    def convert_nutrient(value, field):
        if value is None:
            raise ValueError(
                f"Data {field} pada resep belum tersedia."
            )

        number = Decimal(str(value))

        if not number.is_finite() or number < 0:
            raise ValueError(
                f"Nilai {field} tidak valid."
            )

        return int(
            number.quantize(
                Decimal("1"),
                rounding=ROUND_HALF_UP
            )
        )

    return RecipeSnapshot(
        name=recipe.title,
        protein_g=convert_nutrient(
            recipe.protein, "protein"
        ),
        carbs_g=convert_nutrient(
            recipe.carbohydrates, "carbohydrates"
        ),
        fat_g=convert_nutrient(
            recipe.fat, "fat"
        ),
        calories=convert_nutrient(
            recipe.calories, "calories"
        ),
    )


def _login_url(request, next_path=None):
    destination = next_path or request.get_full_path()
    return f"{reverse('authentication:login')}?{urlencode({'next': destination})}"


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


def _json_error(code, message, status):
    return JsonResponse({"error": {"code": code, "message": message}}, status=status)


def _voting_routes_available():
    try:
        reverse("voting:vote", args=(1,))
    except NoReverseMatch:
        return False
    return True


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

    recipes = list(
        Recipe.objects.filter(is_published=True).order_by("-created_at", "-pk")
    )
    if request.user.is_authenticated and recipes:
        statuses = {
            row["recipe_id"]: row
            for row in RecipeInteraction.objects.filter(
                user=request.user,
                recipe_id__in=[recipe.pk for recipe in recipes],
            ).values("recipe_id", "viewed_at", "completed_at")
        }
    else:
        statuses = {}

    for recipe in recipes:
        status = statuses.get(recipe.pk, {})
        recipe.interaction_viewed = bool(status.get("viewed_at"))
        recipe.interaction_completed = bool(status.get("completed_at"))
        try:
            recipe.card_image_url = recipe.image.url if recipe.image else ""
        except (OSError, ValueError):
            recipe.card_image_url = ""
        if not recipe.card_image_url:
            recipe.card_image_url = recipe.image_url

    return render(
        request,
        "Recipe/recipe.html",
        {
            "ingredients": saved_ingredients,
            "recipes": recipes,
            "recipe_login_url": _login_url(request),
            "voting_routes_available": _voting_routes_available(),
        },
    )


@require_GET
def recipe_detail_api(request, recipe_id):
    recipe = get_recipe_by_id(recipe_id)
    if recipe is None:
        return _json_error("recipe_not_found", "Resep tidak ditemukan.", 404)
    payload = get_recipe_detail(recipe)
    payload["interaction"] = _interaction_payload(request.user, recipe)
    return JsonResponse(payload)


@require_GET
def recipe_interaction_status(request, recipe_id):
    recipe = get_recipe_by_id(recipe_id)
    if recipe is None:
        return _json_error("recipe_not_found", "Resep tidak ditemukan.", 404)
    return JsonResponse(_interaction_payload(request.user, recipe))


@require_POST
def record_recipe_view(request, recipe_id):
    authentication_error = _authentication_error(request)
    if authentication_error:
        return authentication_error

    recipe = get_recipe_by_id(recipe_id)
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
            "Konfirmasi harus dalam format JSON.",
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
            "Konfirmasi bahwa resep sudah dimasak.",
            400,
        )

    # Ambil data resep dari database
    recipe = get_recipe_by_id(recipe_id)

    if recipe is None:
        return _json_error(
            "recipe_not_found",
            "Resep tidak ditemukan.",
            404,
        )

    # Validasi ID aktivitas memasak
    try:
        request_id = uuid.UUID(str(payload.get("request_id")))
    except (ValueError, TypeError, AttributeError):
        return _json_error(
            "invalid_request_id",
            "Request ID harus berupa UUID valid.",
            400,
        )

    # Konversi data Recipe menjadi RecipeSnapshot
    try:
        recipe_snapshot = make_recipe_snapshot(recipe)
    except ValueError as error:
        return _json_error(
            "invalid_recipe_data",
            str(error),
            400,
        )

    # Simpan interaksi Recipe dan aktivitas Tracker
    # dalam satu transaksi
    with transaction.atomic():
        now = timezone.now()

        interaction, created = RecipeInteraction.objects.get_or_create(
            user=request.user,
            recipe=recipe,
            defaults={
                "viewed_at": now,
                "completed_at": now,
            },
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
                interaction.save(
                    update_fields=(*update_fields, "updated_at")
                )

        # INTEGRASI RECIPE KE TRACKER
        new_badges = complete_recipe_cooking(
            user=request.user,
            recipe=recipe_snapshot,
            request_id=request_id,
        )

    # Pertahankan data response Recipe yang lama
    response_data = _interaction_payload(request.user, recipe)

    # Tambahkan informasi untuk Tracker
    response_data["tracker_recorded"] = True
    response_data["new_badges"] = [
        badge.name for badge in new_badges
    ]

    return JsonResponse(response_data)
