import hashlib
import json
import os
import socket
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.core.cache import cache


SPOONACULAR_API_BASE = "https://api.spoonacular.com"
SPOONACULAR_TIMEOUT = 6


class SpoonacularError(Exception):
    def __init__(self, code, message):
        self.code = code
        self.message = message
        super().__init__(message)


def _request_spoonacular(endpoint, params, api_key):
    query = urlencode({**params, "apiKey": api_key})
    request = Request(
        f"{SPOONACULAR_API_BASE}/{endpoint}?{query}",
        headers={
            "Accept": "application/json",
            "User-Agent": "OlahRasa/1.0",
        },
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


def get_spoonacular_recipe(recipe):
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
            return {
                "status": "ok",
                "message": "",
                "data": cached_details,
            }

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
        if isinstance(error, SpoonacularError):
            code, message = error.code, error.message
        else:
            code, message = "invalid_response", "Data resep Spoonacular tidak valid."
        return {"status": code, "message": message, "data": None}
