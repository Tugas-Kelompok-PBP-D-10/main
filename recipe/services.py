import hashlib
import json
import math
import os
import re
import socket
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen

from django.core.cache import cache

from .models import Recipe


SPOONACULAR_API_BASE = "https://api.spoonacular.com"
SPOONACULAR_TIMEOUT = 6
SPOONACULAR_SEARCH_PAGE_SIZE = 12
SPOONACULAR_SEARCH_CACHE_SECONDS = 15 * 60

_INDONESIAN_RECIPE_TERMS = {
    "daging ayam": "chicken",
    "ayam": "chicken",
    "daging sapi": "beef",
    "sapi": "beef",
    "daging kambing": "lamb",
    "kambing": "lamb",
    "ikan": "fish",
    "udang": "shrimp",
    "cumi": "squid",
    "telur": "egg",
    "tahu": "tofu",
    "tempe": "tempeh",
    "nasi": "rice",
    "mie": "noodles",
    "mi": "noodles",
    "sayur": "vegetables",
    "sayuran": "vegetables",
    "kentang": "potato",
    "bayam": "spinach",
    "kangkung": "water spinach",
    "wortel": "carrot",
    "bawang putih": "garlic",
    "bawang merah": "shallot",
    "bawang bombai": "onion",
    "tomat": "tomato",
    "jagung": "corn",
    "santan": "coconut milk",
    "kelapa": "coconut",
    "cabai": "chili",
    "cabe": "chili",
    "sambal": "chili sauce",
    "kecap manis": "sweet soy sauce",
    "kecap": "soy sauce",
    "roti": "bread",
    "sup": "soup",
    "goreng": "fried",
    "bakar": "grilled",
    "rebus": "boiled",
    "tumis": "stir fry",
    "kukus": "steamed",
}


def normalize_indonesian_recipe_query(query):
    """Terjemahkan istilah masak umum; kata di luar glosarium tetap apa adanya."""
    normalized = str(query or "").strip()
    for source, target in sorted(
        _INDONESIAN_RECIPE_TERMS.items(), key=lambda item: len(item[0]), reverse=True
    ):
        normalized = re.sub(
            rf"(?<!\w){re.escape(source)}(?!\w)",
            target,
            normalized,
            flags=re.IGNORECASE,
        )
    return " ".join(normalized.split())


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


def _complex_search_payload(api_key, query, parameters):
    request_parameters = {"query": query, **parameters}
    cache_key = "recipe:spoonacular:complex-search:" + hashlib.sha256(
        json.dumps(request_parameters, sort_keys=True).encode("utf-8")
    ).hexdigest()
    cached_payload = cache.get(cache_key)
    if cached_payload is not None:
        return cached_payload
    payload = _request_spoonacular(
        "recipes/complexSearch",
        request_parameters,
        api_key,
    )
    if not isinstance(payload, dict):
        raise SpoonacularError(
            "invalid_response",
            "Hasil pencarian Spoonacular tidak sesuai format.",
        )
    cache.set(cache_key, payload, SPOONACULAR_SEARCH_CACHE_SECONDS)
    return payload


def search_spoonacular_recipes(query, offset=0):
    """Cari beberapa resep, urutkan protein tinggi, dan cache tiap halaman."""
    query = " ".join(str(query or "").split())
    normalized_query = normalize_indonesian_recipe_query(query)
    try:
        offset = int(offset)
    except (TypeError, ValueError):
        return {"status": "invalid_offset", "message": "Halaman pencarian tidak valid."}
    if not query or len(query) < 2 or len(query) > 100:
        return {"status": "invalid_query", "message": "Ketik minimal 2 karakter untuk mencari."}
    if offset < 0 or offset > 900 or offset % SPOONACULAR_SEARCH_PAGE_SIZE:
        return {"status": "invalid_offset", "message": "Halaman pencarian tidak valid."}

    api_key = os.environ.get("SPOONACULAR_API_KEY", "").strip()
    if not api_key:
        return {
            "status": "not_configured",
            "message": "Kunci API Spoonacular belum dikonfigurasi.",
        }

    parameters = {
        "number": SPOONACULAR_SEARCH_PAGE_SIZE,
        "offset": offset,
        "sort": "protein",
        "sortDirection": "desc",
        "instructionsRequired": "true",
    }
    try:
        payload = _complex_search_payload(api_key, normalized_query, parameters)
        raw_results = payload.get("results", [])
        if not isinstance(raw_results, list):
            raise SpoonacularError(
                "invalid_response",
                "Hasil pencarian Spoonacular tidak sesuai format.",
            )
        results = []
        for item in raw_results:
            if not isinstance(item, dict):
                continue
            try:
                spoonacular_id = int(item.get("id"))
            except (TypeError, ValueError):
                continue
            if spoonacular_id < 1:
                continue
            results.append(
                {
                    "id": spoonacular_id,
                    "title": _plain_text(item.get("title")) or "Resep Spoonacular",
                    "image": _safe_image_url(item.get("image")),
                    "cooking_time": _positive_integer(item.get("readyInMinutes")),
                    "servings": _positive_integer(item.get("servings")),
                    "protein": _search_protein(item),
                }
            )
        try:
            total_results = max(0, int(payload.get("totalResults", offset + len(results))))
        except (TypeError, ValueError):
            total_results = offset + len(results)
        next_offset = offset + SPOONACULAR_SEARCH_PAGE_SIZE
        has_more = bool(results) and offset < 900 and next_offset < total_results
        return {
            "status": "ok",
            "query": query,
            "normalized_query": normalized_query,
            "translation_status": "partial",
            "results": results,
            "offset": offset,
            "next_offset": next_offset if has_more else None,
            "total_results": total_results,
            "has_more": has_more,
        }
    except (SpoonacularError, TypeError, ValueError) as error:
        service_error = _service_error(error)
        return {"status": service_error["status"], "message": service_error["message"]}


def get_spoonacular_recipe_detail(spoonacular_id):
    """Ambil dan normalkan detail API ke payload yang dipakai modal resep."""
    try:
        spoonacular_id = int(spoonacular_id)
    except (TypeError, ValueError):
        return {"status": "not_found", "message": "Resep tidak ditemukan.", "data": None}
    if spoonacular_id < 1:
        return {"status": "not_found", "message": "Resep tidak ditemukan.", "data": None}

    api_key = os.environ.get("SPOONACULAR_API_KEY", "").strip()
    if not api_key:
        return {
            "status": "not_configured",
            "message": "Kunci API Spoonacular belum dikonfigurasi.",
            "data": None,
        }
    cache_key = f"recipe:spoonacular:search-detail:{spoonacular_id}:nutrition"
    cached_payload = cache.get(cache_key)
    if cached_payload is not None:
        return {"status": "ok", "message": "", "data": cached_payload}
    try:
        data = _request_spoonacular(
            f"recipes/{spoonacular_id}/information",
            {"includeNutrition": "true"},
            api_key,
        )
        if not isinstance(data, dict) or int(data.get("id", 0)) != spoonacular_id:
            raise SpoonacularError(
                "invalid_response",
                "Detail resep Spoonacular tidak sesuai format.",
            )
        recipe = _recipe_from_spoonacular_data(data)
        detail = get_recipe_detail(recipe, spoonacular_data=data)
        detail["translation_status"] = "unavailable"
        cache.set(cache_key, detail, 60 * 60 * 6)
        return {"status": "ok", "message": "", "data": detail}
    except (SpoonacularError, TypeError, ValueError) as error:
        service_error = _service_error(error)
        return {"status": service_error["status"], "message": service_error["message"], "data": None}


def import_high_protein_spoonacular_recipes(query, limit=10):
    """Impor resep baru dengan protein API >=30 g/porsi; resep yang ada tetap utuh."""
    query = " ".join(str(query or "").split())
    normalized_query = normalize_indonesian_recipe_query(query)
    try:
        limit = int(limit)
    except (TypeError, ValueError):
        return {
            "status": "invalid_limit",
            "message": "Batas impor harus berupa angka 1 sampai 50.",
            "created": 0,
            "duplicates": 0,
            "skipped": 0,
        }
    if not query or len(query) < 2 or len(query) > 100 or not 1 <= limit <= 50:
        return {
            "status": "invalid_request",
            "message": "Gunakan kata kunci 2–100 karakter dan batas impor 1–50.",
            "created": 0,
            "duplicates": 0,
            "skipped": 0,
        }

    api_key = os.environ.get("SPOONACULAR_API_KEY", "").strip()
    if not api_key:
        return {
            "status": "not_configured",
            "message": "Kunci API Spoonacular belum dikonfigurasi.",
            "created": 0,
            "duplicates": 0,
            "skipped": 0,
        }
    parameters = {
        "number": limit,
        "offset": 0,
        "minProtein": 30,
        "sort": "protein",
        "sortDirection": "desc",
        "instructionsRequired": "true",
        "addRecipeInformation": "true",
        "addRecipeInstructions": "true",
        "addRecipeNutrition": "true",
    }
    try:
        payload = _complex_search_payload(api_key, normalized_query, parameters)
        raw_results = payload.get("results", [])
        if not isinstance(raw_results, list):
            raise SpoonacularError(
                "invalid_response",
                "Hasil impor Spoonacular tidak sesuai format.",
            )
    except (SpoonacularError, TypeError, ValueError) as error:
        service_error = _service_error(error)
        return {
            "status": service_error["status"],
            "message": service_error["message"],
            "created": 0,
            "duplicates": 0,
            "skipped": 0,
        }

    created = duplicates = skipped = 0
    for data in raw_results:
        if not isinstance(data, dict):
            skipped += 1
            continue
        try:
            spoonacular_id = int(data.get("id"))
        except (TypeError, ValueError):
            skipped += 1
            continue
        try:
            recipe = _recipe_from_spoonacular_data(data)
        except (TypeError, ValueError):
            skipped += 1
            continue
        if recipe.protein is None or recipe.protein < Decimal("30") or not recipe.title:
            skipped += 1
            continue
        defaults = {
            "title": recipe.title,
            "description": recipe.description,
            "preparation_time": recipe.preparation_time,
            "cooking_time": recipe.cooking_time,
            "servings": recipe.servings,
            "image_url": recipe.image_url,
            "source_type": "spoonacular",
            "source_name": "Spoonacular (teks sumber; belum diterjemahkan)",
            "is_published": True,
            "calories": recipe.calories,
            "protein": recipe.protein,
            "carbohydrates": recipe.carbohydrates,
            "fat": recipe.fat,
            "nutrition_basis": recipe.nutrition_basis,
            "additional_nutrition": recipe.additional_nutrition,
            "ingredients": recipe.ingredients,
            "instructions": recipe.instructions,
        }
        try:
            _saved_recipe, was_created = Recipe.objects.get_or_create(
                spoonacular_id=spoonacular_id,
                defaults=defaults,
            )
        except (TypeError, ValueError):
            skipped += 1
            continue
        if was_created:
            created += 1
        else:
            duplicates += 1
    return {
        "status": "ok",
        "query": query,
        "normalized_query": normalized_query,
        "message": "",
        "created": created,
        "duplicates": duplicates,
        "skipped": skipped,
    }


def get_spoonacular_recipe(recipe, include_nutrition=True):
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

        details_cache_key = (
            f"{cache_key}:details:{spoonacular_id}:"
            f"nutrition:{int(bool(include_nutrition))}"
        )
        cached_details = cache.get(details_cache_key)
        if cached_details is not None:
            return {"status": "ok", "message": "", "data": cached_details}

        details = _request_spoonacular(
            f"recipes/{int(spoonacular_id)}/information",
            {"includeNutrition": "true" if include_nutrition else "false"},
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


def get_recipe_detail(recipe, spoonacular_data=None):
    """Susun detail dari DB; minta API hanya untuk metadata yang benar-benar hilang."""
    if isinstance(spoonacular_data, dict):
        spoonacular_result = {
            "status": "ok",
            "message": "",
            "data": spoonacular_data,
        }
    else:
        local_ingredients = get_recipe_ingredients(recipe)
        needs_external_metadata = bool(
            recipe.spoonacular_id
            and recipe.source_type != "local"
            and (
                not recipe.description
                or recipe.preparation_time is None
                or recipe.cooking_time is None
                or not _stored_image_url(recipe) and not _safe_image_url(recipe.image_url)
                or not local_ingredients
                or not recipe.instructions
            )
        )
        if needs_external_metadata:
            spoonacular_result = get_spoonacular_recipe(
                recipe,
                include_nutrition=False,
            )
        else:
            spoonacular_result = {
                "status": "local" if recipe.source_type == "local" else "stored",
                "message": "Data resep dari database ditampilkan.",
                "data": None,
            }
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
        # Nutrisi modal selalu berasal dari nilai yang sudah tersimpan.
        "nutrition": get_recipe_nutrition(recipe),
        "ingredients": get_recipe_ingredients(recipe, api_data),
        "instructions": get_recipe_instructions(recipe, api_data),
        "translation_status": (
            "unavailable"
            if recipe.source_type == "spoonacular" or api_data
            else "not_needed"
        ),
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

    try:
        servings = Decimal(str(recipe.servings))
    except (InvalidOperation, TypeError, ValueError):
        servings = None
    if (
        include_nutrition
        and (servings is None or not servings.is_finite() or servings < 1)
    ):
        return {
            "status": "insufficient_data",
            "message": "Analisis nutrisi memerlukan jumlah porsi yang valid.",
            "data": None,
        }

    try:
        normalized_ingredients = normalize_recipe_ingredients(
            get_recipe_ingredients(recipe),
            require_items=True,
            require_quantities=include_nutrition,
        )
    except ValueError:
        return {
            "status": "insufficient_data",
            "message": "Analisis nutrisi memerlukan takaran numerik dan satuan untuk setiap bahan.",
            "data": None,
        }

    ingredients = []
    unit_aliases = {
        "gram": "g",
        "grams": "g",
        "kilogram": "kg",
        "kilograms": "kg",
        "milliliter": "ml",
        "milliliters": "ml",
        "liter": "l",
        "liters": "l",
        "sdm": "tbsp",
        "sendok makan": "tbsp",
        "sendok makan penuh": "tbsp",
        "sdt": "tsp",
        "sendok teh": "tsp",
        "butir": "piece",
        "buah": "piece",
        "pcs": "piece",
        "biji": "piece",
        "siung": "clove",
        "ikat": "bunch",
    }
    for ingredient in normalized_ingredients:
        amount = ingredient.get("amount")
        unit = str(ingredient.get("unit") or "").strip()
        name = ingredient.get("name", "")
        if include_nutrition and (amount is None or not unit):
            return {
                "status": "insufficient_data",
                "message": "Analisis nutrisi memerlukan takaran numerik dan satuan untuk setiap bahan.",
                "data": None,
            }
        normalized_unit = unit_aliases.get(unit.casefold(), unit)
        if amount is not None:
            ingredients.append(f"{amount} {normalized_unit} {name}".strip())
        else:
            ingredients.append(ingredient.get("original") or name)

    servings_value = None
    if servings is not None:
        servings_value = (
            int(servings)
            if servings == servings.to_integral_value()
            else float(servings)
        )
    body = {
        "title": recipe.title,
        "servings": servings_value,
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


def recipe_has_missing_nutrition(recipe):
    return any(
        getattr(recipe, field) is None
        for field in ("calories", "protein", "fat", "carbohydrates")
    )


def _nutrition_decimal(nutrient, expected_unit):
    if not isinstance(nutrient, dict):
        return None
    try:
        value = Decimal(str(nutrient.get("amount")))
    except (InvalidOperation, TypeError, ValueError):
        return None
    if not value.is_finite() or value < 0:
        return None

    unit = str(nutrient.get("unit") or expected_unit).strip().casefold()
    if expected_unit == "kcal":
        if unit in {"cal", "calorie", "calories"}:
            value /= Decimal("1000")
        elif unit not in {"kcal", "kilocalorie", "kilocalories"}:
            return None
    elif unit in {"mg", "milligram", "milligrams"}:
        value /= Decimal("1000")
    elif unit not in {"g", "gram", "grams"}:
        return None

    try:
        value = value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except InvalidOperation:
        return None
    # Recipe fields use max_digits=8 and decimal_places=2.
    if value > Decimal("999999.99"):
        return None
    return value


def _positive_integer(value):
    number = _number(value)
    if number is None or number < 1 or not float(number).is_integer() or number > 32767:
        return None
    return int(number)


def _search_protein(recipe_data):
    nutrition = recipe_data.get("nutrition")
    nutrients = nutrition.get("nutrients", []) if isinstance(nutrition, dict) else []
    if not isinstance(nutrients, list):
        return None
    for nutrient in nutrients:
        if isinstance(nutrient, dict) and str(nutrient.get("name", "")).casefold() == "protein":
            value = _nutrition_decimal(nutrient, "g")
            return _number(value)
    return None


def _recipe_from_spoonacular_data(data):
    """Buat model Recipe transient dari response resmi tanpa menebak data."""
    try:
        spoonacular_id = int(data.get("id"))
    except (AttributeError, TypeError, ValueError):
        spoonacular_id = None
    if spoonacular_id is None or spoonacular_id < 1:
        raise ValueError("ID resep Spoonacular tidak valid.")

    nutrition = data.get("nutrition") if isinstance(data, dict) else None
    nutrients = nutrition.get("nutrients", []) if isinstance(nutrition, dict) else []
    if not isinstance(nutrients, list):
        nutrients = []
    api_nutrients = {
        str(item.get("name", "")).strip().casefold(): item
        for item in nutrients
        if isinstance(item, dict)
    }
    fields = {
        "calories": ("calories", "kcal"),
        "protein": ("protein", "g"),
        "fat": ("fat", "g"),
        "carbohydrates": ("carbohydrates", "g"),
    }
    stored_nutrients = {
        field: _nutrition_decimal(api_nutrients.get(api_name), unit)
        for field, (api_name, unit) in fields.items()
    }
    additional_nutrition = {}
    for item in nutrients:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "")).strip()
        if not name or name.casefold() in fields:
            continue
        value = _number(item.get("amount"))
        if value is not None:
            additional_nutrition[name] = {
                "value": value,
                "unit": str(item.get("unit") or "").strip(),
            }

    transient = Recipe(ingredients=[], instructions="")
    ingredients = get_recipe_ingredients(transient, data)
    instructions = get_recipe_instructions(transient, data)
    servings = _positive_integer(data.get("servings"))
    preparation_time = _positive_integer(data.get("preparationMinutes"))
    cooking_time = _positive_integer(
        data.get("cookingMinutes") or data.get("readyInMinutes")
    )
    source_name = _plain_text(data.get("sourceName"))
    if not source_name:
        source_name = "Spoonacular (teks sumber; belum diterjemahkan)"
    return Recipe(
        pk=spoonacular_id,
        spoonacular_id=spoonacular_id,
        title=_plain_text(data.get("title")) or "Resep Spoonacular",
        description=_plain_text(data.get("summary")),
        preparation_time=preparation_time,
        cooking_time=cooking_time,
        servings=servings,
        image_url=_safe_image_url(data.get("image")),
        source_type="spoonacular",
        source_name=source_name,
        calories=stored_nutrients["calories"],
        protein=stored_nutrients["protein"],
        fat=stored_nutrients["fat"],
        carbohydrates=stored_nutrients["carbohydrates"],
        nutrition_basis=(
            "per_serving"
            if any(value is not None for value in stored_nutrients.values())
            else "unknown"
        ),
        additional_nutrition=additional_nutrition,
        ingredients=ingredients,
        instructions="\n".join(instructions),
    )


def calculate_and_store_recipe_nutrition(recipe):
    """Isi nutrisi yang kosong dari analisis Spoonacular per porsi.

    Nilai manual tidak pernah ditimpa. Data dengan basis yang belum jelas atau
    total resep tidak dicampur dengan hasil API yang dihitung per porsi.
    """
    if not recipe_has_missing_nutrition(recipe):
        return {"status": "complete", "updated": []}

    fields = {
        "calories": ("Calories", "kcal"),
        "protein": ("Protein", "g"),
        "fat": ("Fat", "g"),
        "carbohydrates": ("Carbohydrates", "g"),
    }
    existing_values = [getattr(recipe, field) for field in fields]
    has_existing_values = any(value is not None for value in existing_values)
    if has_existing_values and recipe.nutrition_basis != "per_serving":
        return {"status": "manual_values_preserved", "updated": []}

    try:
        result = analyze_recipe_with_spoonacular(recipe, include_nutrition=True)
    except Exception:
        # External service failures must not undo a saved recipe.
        return {"status": "upstream_error", "updated": []}
    if result.get("status") != "ok" or not isinstance(result.get("data"), dict):
        return {"status": result.get("status", "invalid_response"), "updated": []}

    nutrition = result["data"].get("nutrition")
    nutrients = nutrition.get("nutrients", []) if isinstance(nutrition, dict) else []
    if not isinstance(nutrients, list):
        return {"status": "invalid_response", "updated": []}
    api_nutrients = {
        str(item.get("name", "")).strip().casefold(): item
        for item in nutrients
        if isinstance(item, dict)
    }

    updates = {}
    updated_fields = []
    for field, (api_name, unit) in fields.items():
        if getattr(recipe, field) is not None:
            continue
        nutrient = api_nutrients.get(api_name.casefold())
        value = _nutrition_decimal(nutrient, unit)
        if value is not None:
            updates[field] = value
            updated_fields.append(field)

    if not updates:
        return {"status": "nutrition_unavailable", "updated": []}

    updates["nutrition_basis"] = "per_serving"
    for field, value in updates.items():
        setattr(recipe, field, value)
    recipe.save(update_fields=(*updated_fields, "nutrition_basis"))
    return {"status": "ok", "updated": updated_fields}
