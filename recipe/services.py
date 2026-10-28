import hashlib
import json
import math
import os
import socket
from decimal import Decimal, InvalidOperation
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen

from django.core.cache import cache

from .models import Recipe


SPOONACULAR_API_BASE = "https://api.spoonacular.com"
SPOONACULAR_TIMEOUT = 6


class SpoonacularError(Exception):
    def __init__(self, code, message):
        self.code = code
        self.message = message
        super().__init__(message)


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
    return " ".join(" ".join(parser.parts).split()).strip()


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


def normalize_recipe_ingredients(
    ingredients,
    *,
    require_items=False,
    require_quantities=False,
):
    """Validasi bahan agar Admin dan form pengguna memakai format yang sama."""
    if not isinstance(ingredients, list):
        raise ValueError("Bahan harus berupa daftar.")

    normalized = []
    for index, ingredient in enumerate(ingredients, start=1):
        if isinstance(ingredient, str):
            name = ingredient.strip()
            if name:
                if require_quantities:
                    raise ValueError(f"Jumlah bahan ke-{index} belum diisi.")
                normalized.append(name)
            continue
        if not isinstance(ingredient, dict):
            raise ValueError(f"Format bahan ke-{index} tidak valid.")

        name = str(ingredient.get("name") or "").strip()
        unit = str(ingredient.get("unit") or "").strip()
        if not name:
            raise ValueError(f"Nama bahan ke-{index} belum diisi.")
        if len(name) > 100 or len(unit) > 40:
            raise ValueError(f"Nama atau satuan bahan ke-{index} terlalu panjang.")

        raw_amount = ingredient.get("amount")
        if raw_amount in (None, ""):
            if require_quantities:
                raise ValueError(f"Jumlah bahan ke-{index} belum diisi.")
            amount = None
        else:
            try:
                decimal_amount = Decimal(str(raw_amount))
            except (InvalidOperation, TypeError, ValueError):
                raise ValueError(f"Jumlah bahan ke-{index} harus berupa angka.")
            if (
                not decimal_amount.is_finite()
                or decimal_amount <= 0
                or decimal_amount > Decimal("1000000000000")
            ):
                raise ValueError(f"Jumlah bahan ke-{index} harus lebih besar dari nol.")
            amount = (
                int(decimal_amount)
                if decimal_amount == decimal_amount.to_integral_value()
                else float(decimal_amount)
            )
            if isinstance(amount, float) and not math.isfinite(amount):
                raise ValueError(f"Jumlah bahan ke-{index} tidak valid.")

        if require_quantities and not unit:
            raise ValueError(f"Satuan bahan ke-{index} belum dipilih.")

        record = {"name": name, "amount": amount, "unit": unit}
        original = str(ingredient.get("original") or "").strip()
        if original:
            record["original"] = original
        normalized.append(record)

    if require_items and not normalized:
        raise ValueError("Tambahkan sedikitnya satu bahan yang valid.")
    return normalized


def _request_spoonacular(endpoint, params, api_key, method="GET", body=None):
    query = urlencode({**params, "apiKey": api_key})
    data = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {
        "Accept": "application/json",
        "User-Agent": "OlahRasa/1.0",
    }
    if data is not None:
        headers["Content-Type"] = "application/json"
    request = Request(
        f"{SPOONACULAR_API_BASE}/{endpoint}?{query}",
        data=data,
        headers=headers,
        method=method,
    )

    try:
        with urlopen(request, timeout=SPOONACULAR_TIMEOUT) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        if error.code in (401, 403):
            raise SpoonacularError(
                "invalid_api_key",
                "Kunci API Spoonacular tidak valid atau tidak memiliki akses.",
            ) from error
        if error.code in (402, 429):
            raise SpoonacularError(
                "quota_exceeded",
                "Kuota API Spoonacular sedang habis atau dibatasi.",
            ) from error
        if error.code == 404:
            raise SpoonacularError(
                "not_found",
                "Resep tidak ditemukan di Spoonacular.",
            ) from error
        raise SpoonacularError(
            "upstream_error",
            "Spoonacular gagal memproses permintaan.",
        ) from error
    except (socket.timeout, TimeoutError) as error:
        raise SpoonacularError(
            "timeout",
            "Spoonacular tidak merespons dalam batas waktu.",
        ) from error
    except URLError as error:
        raise SpoonacularError(
            "unavailable",
            "Spoonacular tidak dapat dijangkau.",
        ) from error
    except OSError as error:
        raise SpoonacularError(
            "unavailable",
            "Spoonacular tidak dapat dijangkau.",
        ) from error
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise SpoonacularError(
            "invalid_response",
            "Spoonacular mengirim respons yang tidak dapat dibaca.",
        ) from error

    if not isinstance(payload, (dict, list)):
        raise SpoonacularError(
            "invalid_response",
            "Format respons Spoonacular tidak sesuai.",
        )
    return payload


def _normalized_title(value):
    return "".join(character.casefold() for character in value if character.isalnum())


def _recipe_cache_key(recipe):
    title_hash = hashlib.sha256(recipe.title.encode("utf-8")).hexdigest()[:16]
    recipe_id = recipe.spoonacular_id or "search"
    return f"recipe:spoonacular:{recipe.pk}:{recipe_id}:{title_hash}"


def _find_spoonacular_id(recipe, api_key, cache_key):
    search_cache_key = f"{cache_key}:matched_id"
    cached_id = cache.get(search_cache_key)
    if cached_id is not None:
        return cached_id or None

    payload = _request_spoonacular(
        "recipes/complexSearch",
        {
            "query": recipe.title,
            "number": 5,
            "instructionsRequired": "true",
        },
        api_key,
    )
    results = payload.get("results", []) if isinstance(payload, dict) else []
    expected_title = _normalized_title(recipe.title)
    matched = next(
        (
            result
            for result in results
            if isinstance(result, dict)
            and _normalized_title(str(result.get("title", ""))) == expected_title
            and result.get("id")
        ),
        None,
    )
    matched_id = int(matched["id"]) if matched else 0
    cache.set(search_cache_key, matched_id, 60 * 60 * 24 if matched_id else 60 * 15)
    return matched_id or None


def _service_error(error):
    if isinstance(error, SpoonacularError):
        return {"status": error.code, "message": error.message, "data": None}
    return {
        "status": "invalid_response",
        "message": "Data resep Spoonacular tidak valid.",
        "data": None,
    }


def get_spoonacular_recipe(recipe):
    """Ambil detail API untuk resep bertipe otomatis atau Spoonacular."""
    if recipe.source_type == "local":
        return {
            "status": "local",
            "message": "Resep lokal OlahRasa ditampilkan.",
            "data": None,
        }

    api_key = os.environ.get("SPOONACULAR_API_KEY", "").strip()
    if not api_key:
        return {
            "status": "not_configured",
            "message": "Kunci API Spoonacular belum dikonfigurasi.",
            "data": None,
        }

    cache_key = _recipe_cache_key(recipe)
    try:
        spoonacular_id = recipe.spoonacular_id or _find_spoonacular_id(
            recipe,
            api_key,
            cache_key,
        )
        if not spoonacular_id:
            return {
                "status": "not_found",
                "message": "Tidak ada resep Spoonacular dengan judul yang sama.",
                "data": None,
            }

        details_cache_key = f"{cache_key}:details:{spoonacular_id}"
        cached_details = cache.get(details_cache_key)
        if cached_details is not None:
            return {"status": "ok", "message": "", "data": cached_details}

        details = _request_spoonacular(
            f"recipes/{int(spoonacular_id)}/information",
            {"includeNutrition": "true"},
            api_key,
        )
        if not isinstance(details, dict) or not details.get("id"):
            raise SpoonacularError(
                "invalid_response",
                "Detail resep Spoonacular tidak lengkap.",
            )
        cache.set(details_cache_key, details, 60 * 60 * 6)
        return {"status": "ok", "message": "", "data": details}
    except (SpoonacularError, TypeError, ValueError) as error:
        return _service_error(error)


def get_recipe_by_id(recipe_id, published_only=True):
    """Ambil resep lokal dari primary key; resep draft tidak terbuka untuk publik."""
    queryset = Recipe.objects.all()
    if published_only:
        queryset = queryset.filter(is_published=True)
    return queryset.filter(pk=recipe_id).first()


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
        name = original
        amount = None
        unit = ""
    if not original and amount is not None:
        original = f"{amount} {unit} {name}".strip()
    return {"name": name, "amount": amount, "unit": unit, "original": original}


def get_recipe_ingredients(recipe, spoonacular_data=None):
    """Normalisasi bahan lokal atau Spoonacular tanpa menebak takaran."""
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


def get_recipe_instructions(recipe, spoonacular_data=None):
    """Kembalikan langkah lokal berurutan, lalu fallback ke langkah API."""
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


def get_recipe_nutrition(recipe, spoonacular_data=None):
    """Gabungkan nutrisi lokal dan API sambil mempertahankan dasar sumbernya."""
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
                nutrition["additional"].append({"name": str(name), **normalized})

    local_has_nutrition = any(
        _number(getattr(recipe, field)) is not None
        for field in ("calories", "protein", "carbohydrates", "fat")
    ) or bool(nutrition["additional"])
    if not isinstance(spoonacular_data, dict):
        nutrition["basis"] = recipe.nutrition_basis
        return nutrition

    api_nutrition = spoonacular_data.get("nutrition")
    raw_nutrients = (
        api_nutrition.get("nutrients", [])
        if isinstance(api_nutrition, dict)
        else []
    )
    if not isinstance(raw_nutrients, list):
        raw_nutrients = []
    api_nutrients = {}
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
        nutrient = api_nutrients.get(api_name)
        if nutrition[key] is None and nutrient:
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


def scale_ingredient_quantities(ingredients, original_servings, target_servings):
    """Skalakan hanya jumlah numerik dan kembalikan salinan data bahan."""
    base = _number(original_servings)
    target = _number(target_servings)
    if base is None or target is None or base < 1 or target < 1:
        return [dict(item) if isinstance(item, dict) else item for item in ingredients]

    factor = target / base
    scaled = []
    for ingredient in ingredients:
        if not isinstance(ingredient, dict):
            scaled.append(ingredient)
            continue
        item = dict(ingredient)
        amount = _number(item.get("amount"))
        if amount is not None:
            item["amount"] = round(amount * factor, 3)
        scaled.append(item)
    return scaled


def _safe_image_url(value):
    value = str(value or "").strip()
    if not value or any(
        character.isspace()
        or ord(character) < 32
        or ord(character) == 127
        or character == "\\"
        for character in value
    ):
        return ""
    if value.startswith("/") and not value.startswith("//"):
        return value
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError:
        return ""
    if (
        parsed.scheme.casefold() in {"http", "https"}
        and parsed.hostname
        and not parsed.username
        and not parsed.password
        and (port is None or 0 < port < 65536)
    ):
        return value
    return ""


def _stored_image_url(recipe):
    if not recipe.image or not recipe.image.name:
        return ""
    try:
        return _safe_image_url(recipe.image.url)
    except (OSError, ValueError):
        return ""


def get_recipe_image_url(recipe, spoonacular_data=None):
    """Pilih satu URL foto aman yang dapat dipakai kartu dan detail."""
    image_url = _stored_image_url(recipe) or _safe_image_url(recipe.image_url)
    if image_url:
        return image_url
    if isinstance(spoonacular_data, dict):
        return _safe_image_url(spoonacular_data.get("image"))
    return ""


def get_recipe_detail(recipe):
    """Susun respons detail untuk satu resep dan gabungkan API bila diizinkan."""
    spoonacular_result = get_spoonacular_recipe(recipe)
    api_data = spoonacular_result.get("data")
    if not isinstance(api_data, dict):
        api_data = None

    description = _plain_text(recipe.description)
    if not description and api_data:
        description = _plain_text(api_data.get("summary"))

    image_url = get_recipe_image_url(recipe, api_data)

    preparation_time = recipe.preparation_time
    if preparation_time is None and api_data:
        preparation_time = api_data.get("preparationMinutes")
    cooking_time = recipe.cooking_time
    if cooking_time is None and api_data:
        cooking_time = api_data.get("readyInMinutes")
    servings = recipe.servings
    if servings is None and api_data:
        servings = api_data.get("servings")
    servings = _number(servings)
    if servings is not None and (servings < 1 or not float(servings).is_integer()):
        servings = None

    source_name = recipe.source_name or (
        api_data.get("sourceName", "") if api_data else ""
    )
    if not source_name:
        source_name = "Spoonacular" if api_data else "Resep lokal OlahRasa"

    return {
        "recipe": {
            "id": recipe.pk,
            "spoonacular_id": (
                api_data.get("id") if api_data else recipe.spoonacular_id
            ),
            "title": recipe.title,
            "description": description,
            "image": image_url,
            "preparation_time": preparation_time,
            "cooking_time": cooking_time,
            "servings": servings,
            "source": "database+spoonacular" if api_data else "database",
            "source_type": recipe.source_type,
            "source_name": source_name,
        },
        "nutrition": get_recipe_nutrition(recipe, api_data),
        "ingredients": get_recipe_ingredients(recipe, api_data),
        "instructions": get_recipe_instructions(recipe, api_data),
        "external": {
            "status": spoonacular_result.get("status", "not_configured"),
            "message": spoonacular_result.get("message", ""),
        },
    }


def analyze_recipe_with_spoonacular(recipe, include_nutrition=False):
    """Minta analisis resep lokal hanya saat dipanggil eksplisit oleh admin/kode."""
    api_key = os.environ.get("SPOONACULAR_API_KEY", "").strip()
    if not api_key:
        return {
            "status": "not_configured",
            "message": "Kunci API Spoonacular belum dikonfigurasi.",
            "data": None,
        }

    ingredients = []
    for ingredient in get_recipe_ingredients(recipe):
        if ingredient.get("amount") is not None:
            amount = ingredient["amount"]
            unit = ingredient.get("unit", "")
            name = ingredient.get("name", "")
            ingredients.append(f"{amount} {unit} {name}".strip())
        else:
            ingredients.append(ingredient.get("original") or ingredient.get("name", ""))
    ingredients = [item for item in ingredients if item]
    if not ingredients:
        return {
            "status": "insufficient_data",
            "message": "Analisis memerlukan daftar bahan resep.",
            "data": None,
        }

    body = {
        "title": recipe.title,
        "servings": recipe.servings,
        "ingredients": ingredients,
        "instructions": recipe.instructions,
    }
    body = {key: value for key, value in body.items() if value not in (None, "")}
    params = {"includeNutrition": "true" if include_nutrition else "false"}
    cache_key = "recipe:spoonacular:analyze:" + hashlib.sha256(
        json.dumps([body, include_nutrition], sort_keys=True).encode("utf-8")
    ).hexdigest()
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        return {"status": "ok", "message": "", "data": cached_result}

    try:
        data = _request_spoonacular(
            "recipes/analyze",
            params,
            api_key,
            method="POST",
            body=body,
        )
        if not isinstance(data, dict):
            raise SpoonacularError(
                "invalid_response",
                "Hasil analisis Spoonacular tidak sesuai format.",
            )
        cache.set(cache_key, data, 60 * 60 * 6)
        return {"status": "ok", "message": "", "data": data}
    except (SpoonacularError, TypeError, ValueError) as error:
        return _service_error(error)
