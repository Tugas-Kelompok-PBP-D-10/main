import json
import uuid
from decimal import Decimal, ROUND_HALF_UP
from urllib.parse import urlencode

from django.db import IntegrityError, transaction
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import render
from django.urls import NoReverseMatch, reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from .forms import RecipeSubmissionForm
from .models import Recipe, RecipeCookingEvent, RecipeInteraction
from .services import (
    calculate_and_store_recipe_nutrition,
    get_recipe_by_id,
    get_recipe_detail,
    get_recipe_image_url,
)

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


def _authentication_error(request, message="Silakan masuk untuk menyimpan interaksi resep."):
    if request.user.is_authenticated:
        return None
    return JsonResponse(
        {
            "error": {
                "code": "authentication_required",
            "message": message,
            },
            "login_url": _login_url(request, reverse("recipe:home")),
        },
        status=401,
    )


def _json_error(code, message, status):
    return JsonResponse({"error": {"code": code, "message": message}}, status=status)


def _get_recipe_for_request(request, recipe_id):
    recipe = get_recipe_by_id(recipe_id)
    if recipe is not None or not request.user.is_authenticated:
        return recipe

    # Resep arsip tetap bisa dibuka pemilik bookmark/riwayat tanpa dipublikasikan kembali.
    return (
        Recipe.objects.filter(pk=recipe_id, is_published=False)
        .filter(
            Q(author=request.user)
            | Q(bookmarked_by__user=request.user)
            | Q(interactions__user=request.user)
            | Q(cooking_events__user=request.user)
        )
        .distinct()
        .first()
    )


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
            "cooking_count": 0,
        }

    interaction = RecipeInteraction.objects.filter(
        user=user,
        recipe=recipe,
    ).first()
    events = RecipeCookingEvent.objects.filter(user=user, recipe=recipe)
    cooking_count = events.count()
    latest_event = events.order_by("-completed_at", "-pk").first()
    completed_at = (
        latest_event.completed_at
        if latest_event
        else interaction.completed_at
        if interaction
        else None
    )
    cooking_count = max(cooking_count, int(bool(interaction and interaction.completed_at)))
    return {
        "authenticated": True,
        "viewed": bool(interaction and interaction.viewed_at),
        "completed": bool(completed_at),
        "viewed_at": (
            interaction.viewed_at.isoformat()
            if interaction and interaction.viewed_at
            else None
        ),
        "completed_at": completed_at.isoformat() if completed_at else None,
        "cooking_count": cooking_count,
    }


def _recipe_submission_response(recipe, status=201, duplicate=False):
    return JsonResponse(
        {
            "success": True,
            "duplicate": duplicate,
            "message": "Resep berhasil dikirim!",
            "recipe": {
                "id": recipe.pk,
                "title": recipe.title,
                "image": get_recipe_image_url(recipe),
                "servings": recipe.servings,
                "detail_url": reverse("recipe:api_detail", args=(recipe.pk,)),
            },
        },
        status=status,
    )


@require_POST
def submit_recipe(request):
    authentication_error = _authentication_error(
        request,
        "Masuk terlebih dahulu untuk mengirim resep.",
    )
    if authentication_error:
        return authentication_error

    try:
        submission_key = uuid.UUID(str(request.POST.get("submission_id", "")))
    except (ValueError, TypeError, AttributeError):
        return _json_error(
            "invalid_submission_id",
            "ID pengiriman resep tidak valid. Coba kirim kembali.",
            400,
        )

    existing = Recipe.objects.filter(submission_key=submission_key).first()
    if existing:
        if existing.author_id == request.user.pk:
            return _recipe_submission_response(existing, status=200, duplicate=True)
        return _json_error(
            "submission_id_conflict",
            "Pengiriman tidak dapat diproses. Muat ulang formulir dan coba lagi.",
            409,
        )

    form = RecipeSubmissionForm(request.POST, request.FILES)
    if not form.is_valid():
        errors = {
            field: [error["message"] for error in messages]
            for field, messages in form.errors.get_json_data().items()
        }
        return JsonResponse(
            {
                "error": {
                    "code": "invalid_recipe",
                    "message": "Periksa kembali isian resep, ya.",
                },
                "errors": errors,
            },
            status=400,
        )

    try:
        with transaction.atomic():
            recipe = form.save(commit=False)
            recipe.author = request.user
            recipe.submission_key = submission_key
            recipe.source_type = "local"
            recipe.source_name = "Komunitas OlahRasa"
            recipe.is_published = True
            recipe.nutrition_basis = "unknown"
            recipe.save()
    except IntegrityError:
        existing = Recipe.objects.filter(submission_key=submission_key).first()
        if existing and existing.author_id == request.user.pk:
            return _recipe_submission_response(existing, status=200, duplicate=True)
        return _json_error(
            "submission_id_conflict",
            "Pengiriman tidak dapat diproses. Muat ulang formulir dan coba lagi.",
            409,
        )

    # Analisis eksternal berjalan setelah commit dan tidak boleh membatalkan kiriman.
    try:
        calculate_and_store_recipe_nutrition(recipe)
    except Exception:
        pass

    return _recipe_submission_response(recipe)


@require_GET
def recipe_home(request):
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

    recipe_ids = [recipe.pk for recipe in recipes]
    if request.user.is_authenticated and recipe_ids:
        cooking_counts = dict(
            RecipeCookingEvent.objects.filter(
                user=request.user,
                recipe_id__in=recipe_ids,
            )
            .values("recipe_id")
            .annotate(total=Count("pk"))
            .values_list("recipe_id", "total")
        )
        for recipe_id, status in statuses.items():
            if status.get("completed_at"):
                cooking_counts[recipe_id] = max(1, cooking_counts.get(recipe_id, 0))
    else:
        cooking_counts = {}

    for recipe in recipes:
        status = statuses.get(recipe.pk, {})
        recipe.interaction_viewed = bool(status.get("viewed_at"))
        recipe.cooking_count = cooking_counts.get(recipe.pk, 0)
        recipe.interaction_completed = recipe.cooking_count > 0 or bool(
            status.get("completed_at")
        )
        recipe.card_image_url = get_recipe_image_url(recipe)

    return render(
        request,
        "Recipe/recipe.html",
        {
            "recipes": recipes,
            "recipe_login_url": _login_url(request),
            "recipe_submission_url": reverse("recipe:api_submit"),
            "voting_routes_available": _voting_routes_available(),
        },
    )


@require_GET
def recipe_detail_api(request, recipe_id):
    recipe = _get_recipe_for_request(request, recipe_id)
    if recipe is None:
        return _json_error("recipe_not_found", "Resep tidak ditemukan.", 404)
    payload = get_recipe_detail(recipe)
    payload["interaction"] = _interaction_payload(request.user, recipe)
    return JsonResponse(payload)


@require_GET
def recipe_interaction_status(request, recipe_id):
    recipe = _get_recipe_for_request(request, recipe_id)
    if recipe is None:
        return _json_error("recipe_not_found", "Resep tidak ditemukan.", 404)
    return JsonResponse(_interaction_payload(request.user, recipe))


@require_POST
def record_recipe_view(request, recipe_id):
    authentication_error = _authentication_error(request)
    if authentication_error:
        return authentication_error

    recipe = _get_recipe_for_request(request, recipe_id)
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

    recipe = _get_recipe_for_request(request, recipe_id)

    if recipe is None:
        return _json_error(
            "recipe_not_found",
            "Resep tidak ditemukan.",
            404,
        )

    try:
        request_id = uuid.UUID(str(payload.get("request_id")))
    except (ValueError, TypeError, AttributeError):
        return _json_error(
            "invalid_request_id",
            "Request ID harus berupa UUID valid.",
            400,
        )

    recipe_snapshot = None
    try:
        recipe_snapshot = make_recipe_snapshot(recipe)
    except ValueError:
        # Data memasak tetap dicatat di Recipe walau nutrisi belum lengkap.
        pass

    with transaction.atomic():
        now = timezone.now()
        event, event_created = RecipeCookingEvent.objects.get_or_create(
            request_id=request_id,
            defaults={
                "user": request.user,
                "recipe": recipe,
                "completed_at": now,
            },
        )
        if event.user_id != request.user.pk or event.recipe_id != recipe.pk:
            return _json_error(
                "request_id_conflict",
                "ID aktivitas ini sudah digunakan. Coba catat kembali.",
                409,
            )

        interaction, created = RecipeInteraction.objects.get_or_create(
            user=request.user,
            recipe=recipe,
            defaults={
                "viewed_at": now,
                "completed_at": event.completed_at,
            },
        )
        if not created and (
            interaction.completed_at is None
            or interaction.completed_at < event.completed_at
        ):
            interaction.viewed_at = interaction.viewed_at or now
            interaction.completed_at = event.completed_at
            interaction.save(
                update_fields=("viewed_at", "completed_at", "updated_at")
            )

    new_badges = []
    tracker_recorded = False
    tracker_unavailable = False
    if recipe_snapshot is not None:
        try:
            new_badges = complete_recipe_cooking(
                user=request.user,
                recipe=recipe_snapshot,
                request_id=request_id,
            )
            tracker_recorded = True
        except Exception:
            # Kegagalan Tracker tidak membatalkan riwayat yang sudah tersimpan di Recipe.
            tracker_unavailable = True

    response_data = _interaction_payload(request.user, recipe)
    response_data["event_created"] = event_created
    response_data["tracker_recorded"] = tracker_recorded
    response_data["new_badges"] = [
        badge.name for badge in new_badges
    ]
    if not tracker_recorded and not tracker_unavailable:
        response_data["tracker_message"] = (
            "Riwayat resep tersimpan. Nutrisi belum lengkap untuk dikirim ke Tracker."
        )
    elif tracker_unavailable:
        response_data["tracker_message"] = (
            "Riwayat resep tersimpan, tetapi aktivitas Tracker belum tersedia."
        )

    return JsonResponse(response_data)
