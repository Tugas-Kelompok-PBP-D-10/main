from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import render
from django.utils import timezone
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_http_methods
from .services import record_cook
from .models import Badge, CookingLog, CookingStreak, UserBadge, NutritionTarget
from voting.models import Bookmark
import uuid, json

# Target nutrisi mingguan (sesuaikan dengan kebutuhan)
WEEKLY_TARGET = {"protein": 120, "carbs": 120, "fat": 70}
DAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def _week_data(user, monday):
    logs = CookingLog.objects.filter(user=user, cooked_on__gte=monday, cooked_on__lte=monday + timedelta(days=6))
    per_day = {}
    for log in logs:
        per_day[log.cooked_on] = per_day.get(log.cooked_on, 0) + 1

    week = []
    for i, label in enumerate(DAY_LABELS):
        count = per_day.get(monday + timedelta(days=i), 0)
        week.append({"label": label, "cooked": count > 0, "percent": min(100, count * 50)})
    return week


def _nutrients(user, monday):
    totals = CookingLog.objects.filter(
        user=user,
        cooked_on__gte=monday,
        cooked_on__lt=monday + timedelta(days=7),
    ).aggregate(
        protein=Sum("protein_g"),
        carbs=Sum("carbs_g"),
        fat=Sum("fat_g"),
    )

    nutrition_target = NutritionTarget.objects.filter(
        user=user
    ).first()

    rows = [
        ("Protein", "protein", "green"),
        ("Carbs", "carbs", "green"),
        ("Fat", "fat", "yellow"),
    ]

    result = []

    for name, key, color in rows:
        current = totals[key] or 0

        target = (
            getattr(nutrition_target, f"{key}_g")
            if nutrition_target
            else None
        )

        percent = (
            min(100, round(current / target * 100))
            if target is not None and target > 0
            else None
        )

        result.append({
            "name": name,
            "current": current,
            "target": target,
            "unit": "g",
            "percent": percent,
            "color": color,
        })

    return result


@login_required
@require_http_methods(["GET", "POST", "DELETE"])
def nutrition_target_api(request):

    if request.method == "DELETE":
        deleted_count, _ = NutritionTarget.objects.filter(user=request.user).delete()

        return JsonResponse({
            "success": True,
            "message": "Nutrition Target berhasil dihapus.",
            "deleted": deleted_count > 0
        })

    if request.method == "GET":
        target = NutritionTarget.objects.filter(
            user=request.user
        ).first()

        return JsonResponse({
            "success": True,
            "has_target": target is not None,
            "target": {
                "protein_g": target.protein_g,
                "carbs_g": target.carbs_g,
                "fat_g": target.fat_g,
            } if target else None,
        })

    try:    
        data = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({
            "success": False,
            "message": "Format JSON tidak valid.",
        }, status=400)

    if not isinstance(data, dict):
        return JsonResponse({
            "success": False,
            "message": "Data target harus berupa objek JSON.",
        }, status=400)

    values = {}

    for field in ("protein_g", "carbs_g", "fat_g"):
        value = data.get(field)

        if type(value) is not int or not (1 <= value <= 10000):
            return JsonResponse({
                "success": False,
                "message": (
                    f"{field} harus berupa bilangan bulat "
                    "antara 1 sampai 10000."
                ),
            }, status=400)

        values[field] = value

    target, created = NutritionTarget.objects.update_or_create(
        user=request.user,
        defaults=values,
    )

    return JsonResponse({
        "success": True,
        "message": (
            "Nutrition target berhasil disimpan."
            if created
            else "Nutrition target berhasil diperbarui."
        ),
        "target": {
            "protein_g": target.protein_g,
            "carbs_g": target.carbs_g,
            "fat_g": target.fat_g,
        },
    })

def _badges(user, streak):
    total = CookingLog.objects.filter(
        user=user
    ).count()

    earned_ids = set(
        UserBadge.objects.filter(
            user=user
        ).values_list("badge_id", flat=True)
    )

    items = []

    for b in Badge.objects.all():
        value = (
            streak.longest_streak
            if b.kind == Badge.Kind.STREAK
            else total
        )

        earned = b.id in earned_ids

        items.append({
            "name": b.name,
            "description": b.description,

           
            "icon": b.icon.url if b.icon else None,

            "earned": earned,

            "progress": (
                100 if earned
                else min(
                    99,
                    round(value / b.threshold * 100)
                )
            ) if b.threshold > 0 else 0,
        })

    items.sort(
        key=lambda x: not x["earned"]
    )

    return items


@login_required
def tracker_view(request):
    user = request.user

    print(
    "LOGIN TRACKER:",
    "ID =", user.id,
    "USERNAME =", user.username
)

    today = timezone.localdate()
    monday = today - timedelta(days=today.weekday())

    streak, _ = CookingStreak.objects.get_or_create(user=user)
    current = streak.active_streak
    badges = _badges(user, streak)

    # Mengambil 5 bookmark terbaru milik pengguna yang login
    bookmarks = (
        Bookmark.objects
        .filter(user=user)
        .select_related("recipe")
        .order_by("-created_at")[:3]
    )

    context = {
        "streak": {
            "current": current,
            "longest": streak.longest_streak,
            "is_record": current > 1 and current >= streak.longest_streak,
        },
        "week": _week_data(user, monday),
        "nutrients": _nutrients(user, monday),
        "badges": badges,
        "badges_earned": sum(1 for b in badges if b["earned"]),
        "bookmarks": bookmarks,
    }
    return render(request, "tracker/tracker.html", context)


@login_required
@require_POST
def complete_cooking(request):

    if not request.user.is_staff:
        return JsonResponse({
            "success": False,
            "message": "Fitur masih dalam tahap pengujian."
        }, status=403)

    recipe_name = "Test Cooking"


    try:
        request_id = uuid.UUID(request.POST["request_id"])
    except (KeyError, ValueError, TypeError):
        return JsonResponse(
            {"success": False, "message": "Request ID tidak valid."},
            status=400
        )

    new_badges = record_cook(
        user=request.user,
        recipe_name=recipe_name,
        protein_g=15,
        carbs_g=40,
        fat_g=10,
        calories=310,
        request_id=request_id,
    )

    return JsonResponse({
        "success": True,
        "message": "Aktivitas memasak berhasil dicatat!",
        "new_badges": [
            badge.name for badge in new_badges
        ]
    })


@login_required
def tracker_dashboard_api(request):
    user = request.user

    print(
    "TRACKER LOGIN:",
    "user_id =", user.id,
    "username =", user.username
    )

    today = timezone.localdate()
    monday = today - timedelta(days=today.weekday())

    streak, _ = CookingStreak.objects.get_or_create(
        user=user
    )

    badges = _badges(user, streak)

    return JsonResponse({
        "streak": {
            "current": streak.active_streak,
            "longest": streak.longest_streak,
        },
        "week": _week_data(user, monday),
        "nutrients": _nutrients(user, monday),
        "badges": badges,
        "badges_earned": sum(
            1 for badge in badges if badge["earned"]
        ),
    })


@login_required
def cooking_history_api(request):
    logs = CookingLog.objects.filter(
        user=request.user
    ).order_by("-cooked_on", "-id")[:3]

    history = []

    for log in logs:
        history.append({
            "id": log.id,
            "recipe_name": log.recipe_name,
            "cooked_on": log.cooked_on.isoformat(),
            "protein": log.protein_g,
            "carbs": log.carbs_g,
            "fat": log.fat_g,
            "calories": log.calories,
        })

    return JsonResponse({
        "success": True,
        "history": history
    })
