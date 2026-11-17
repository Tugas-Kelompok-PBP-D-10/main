from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import render
from django.utils import timezone
from django.urls import reverse
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_http_methods
from .services import record_cook
from .models import Badge, CookingLog, CookingStreak, UserBadge, NutritionTarget
from voting.models import Bookmark
import uuid, json

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .serializers import (
    CookingHistorySerializer,
    NutritionTargetSerializer,
)

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


@api_view(["GET", "POST", "DELETE"])
@permission_classes([IsAuthenticated])
def nutrition_target_api(request):

    if request.method == "GET":
        target = NutritionTarget.objects.filter(
            user=request.user
        ).first()

        return Response({
            "success": True,
            "has_target": target is not None,
            "target": (
                NutritionTargetSerializer(target).data
                if target else None
            ),
        })

    if request.method == "DELETE":
        deleted_count, _ = NutritionTarget.objects.filter(
            user=request.user
        ).delete()

        return Response({
            "success": True,
            "message": "Nutrition Target berhasil dihapus.",
            "deleted": deleted_count > 0,
        })

    serializer = NutritionTargetSerializer(data=request.data)

    if not serializer.is_valid():
        return Response(
            {
                "success": False,
                "errors": serializer.errors,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    target, created = NutritionTarget.objects.update_or_create(
        user=request.user,
        defaults=serializer.validated_data,
    )

    return Response({
        "success": True,
        "message": (
            "Nutrition target berhasil disimpan."
            if created
            else "Nutrition target berhasil diperbarui."
        ),
        "target": NutritionTargetSerializer(target).data,
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

    # Mengambil 3 bookmark terbaru milik pengguna yang login
    bookmarks = (
        Bookmark.objects
        .filter(user=user)
        .select_related("recipe")
        .order_by("-created_at")[:5]
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


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def tracker_dashboard_api(request):
    user = request.user

    today = timezone.localdate()
    monday = today - timedelta(days=today.weekday())

    streak, _ = CookingStreak.objects.get_or_create(
        user=user
    )

    badges = _badges(user, streak)

    return Response({
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
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def cooking_history_api(request):
    logs = CookingLog.objects.filter(
        user=request.user
    ).order_by("-cooked_on", "-id")[:5]

    serializer = CookingHistorySerializer(
        logs,
        many=True,
    )

    return Response({
        "success": True,
        "history": serializer.data,
    })