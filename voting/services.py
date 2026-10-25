from django.core.exceptions import FieldDoesNotExist
from django.db import transaction
from django.db.models import Count, IntegerField, OuterRef, Q, Subquery, Sum
from django.db.models.functions import Coalesce

from recipe.models import Recipe
from .models import Bookmark, Vote

DOWNVOTE_LIMIT = 100

# Ganti sesuai nama field kategori di model Recipe asli, atau None kalau tidak ada.
CATEGORY_FIELD = "category"


def get_vote_summary(recipe, user=None):
    stats = recipe.votes.aggregate(
        upvotes=Count("id", filter=Q(value=Vote.UPVOTE)),
        downvotes=Count("id", filter=Q(value=Vote.DOWNVOTE)),
        score=Sum("value"),
    )

    user_vote = None
    if user is not None and getattr(user, "is_authenticated", False):
        user_vote = (
            Vote.objects.filter(recipe=recipe, user=user)
            .values_list("value", flat=True)
            .first()
        )

    return {
        "upvotes": stats["upvotes"] or 0,
        "downvotes": stats["downvotes"] or 0,
        "score": stats["score"] or 0,
        "user_vote": user_vote,
    }


def check_auto_delete(recipe):
    if recipe.author_id is None:
        return False

    downvotes = recipe.votes.filter(value=Vote.DOWNVOTE).count()
    if downvotes >= DOWNVOTE_LIMIT:
        recipe.delete()
        return True
    return False


def cast_vote(user, recipe, value):
    try:
        value = int(value)
    except (TypeError, ValueError):
        raise ValueError("Vote harus bernilai 1 atau -1.")

    if value not in (Vote.UPVOTE, Vote.DOWNVOTE):
        raise ValueError("Vote harus bernilai 1 atau -1.")

    with transaction.atomic():
        locked_recipe = Recipe.objects.select_for_update().get(pk=recipe.pk)
        current_vote = Vote.objects.filter(user=user, recipe=locked_recipe).first()

        if current_vote is None:
            Vote.objects.create(user=user, recipe=locked_recipe, value=value)
        elif current_vote.value == value:
            current_vote.delete()
        else:
            current_vote.value = value
            current_vote.save(update_fields=["value"])

        summary = get_vote_summary(locked_recipe, user)
        summary["deleted"] = check_auto_delete(locked_recipe)
        return summary


def remove_vote(user, recipe):
    with transaction.atomic():
        Vote.objects.filter(user=user, recipe=recipe).delete()
        summary = get_vote_summary(recipe, user)
        summary["deleted"] = False
        return summary


def user_bookmark_count(user):
    return Bookmark.objects.filter(user=user).count()


def toggle_bookmark(user, recipe):
    with transaction.atomic():
        bookmark = Bookmark.objects.filter(user=user, recipe=recipe).first()
        if bookmark:
            bookmark.delete()
            return False

        Bookmark.objects.create(user=user, recipe=recipe)
        return True


def with_popularity(queryset):
    return queryset.annotate(popularity=Coalesce(Sum("votes__value"), 0))


def recipe_has_field(name):
    try:
        Recipe._meta.get_field(name)
    except FieldDoesNotExist:
        return False
    return True


def available_categories(user):
    if not (CATEGORY_FIELD and recipe_has_field(CATEGORY_FIELD)):
        return []
    path = f"recipe__{CATEGORY_FIELD}"
    return list(
        Bookmark.objects.filter(user=user)
        .exclude(**{f"{path}__isnull": True})
        .exclude(**{path: ""})
        .order_by(path)
        .values_list(path, flat=True)
        .distinct()
    )


def filter_bookmarks(queryset, params):
    source = params.get("source", "")
    if source == "community":
        queryset = queryset.filter(recipe__author__isnull=False)
    elif source == "api":
        queryset = queryset.filter(recipe__author__isnull=True)

    lookup = {
        "up": {"my_vote": Vote.UPVOTE},
        "down": {"my_vote": Vote.DOWNVOTE},
        "none": {"my_vote__isnull": True},
    }.get(params.get("vote", ""))
    if lookup:
        my_vote = Subquery(
            Vote.objects.filter(user=OuterRef("user"), recipe=OuterRef("recipe"))
            .values("value")[:1]
        )
        queryset = queryset.annotate(my_vote=my_vote).filter(**lookup)

    try:
        min_score = int(params.get("min_score", ""))
    except (TypeError, ValueError):
        min_score = None
    if min_score is not None:
        score = Subquery(
            Vote.objects.filter(recipe=OuterRef("recipe"))
            .order_by()
            .values("recipe")
            .annotate(total=Sum("value"))
            .values("total")
        )
        queryset = queryset.annotate(
            recipe_score=Coalesce(score, 0, output_field=IntegerField())
        ).filter(recipe_score__gte=min_score)

    category = params.get("category", "")
    if category and CATEGORY_FIELD and recipe_has_field(CATEGORY_FIELD):
        queryset = queryset.filter(**{f"recipe__{CATEGORY_FIELD}": category})

    return queryset