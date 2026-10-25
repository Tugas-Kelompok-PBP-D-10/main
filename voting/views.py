from django.core.paginator import Paginator
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render, resolve_url

from recipe.models import Recipe
from .decorators import ajax_login_required
from .models import Bookmark
from .services import (
    CATEGORY_FIELD,
    available_categories,
    cast_vote,
    filter_bookmarks,
    get_vote_summary,
    remove_vote,
    user_bookmark_count,
)
from .services import toggle_bookmark as toggle_bookmark_service


# Upvote/Downvote
@require_POST
@ajax_login_required
def vote(request, recipe_id):
    recipe = get_object_or_404(Recipe, pk=recipe_id)
    try:
        result = cast_vote(request.user, recipe, request.POST.get("value", ""))
    except ValueError as exc:
        return JsonResponse({"message": str(exc)}, status=400)
    return JsonResponse(result)


@require_POST
@ajax_login_required
def vote_remove(request, recipe_id):
    recipe = get_object_or_404(Recipe, pk=recipe_id)
    return JsonResponse(remove_vote(request.user, recipe))


@require_GET
def vote_summary(request, recipe_id):
    recipe = get_object_or_404(Recipe, pk=recipe_id)
    summary = get_vote_summary(recipe, request.user)
    if not request.user.is_authenticated:
        return JsonResponse({"score": summary["score"]})
    return JsonResponse(summary)

PAGE_SIZE = 12
SORT_ORDERING = {
    "newest": "-created_at",
    "oldest": "created_at",
    "title": "recipe__title",
}

# Bookmark
@require_POST
@ajax_login_required
def toggle_bookmark(request, recipe_id):
    recipe = get_object_or_404(Recipe, pk=recipe_id)
    bookmarked = toggle_bookmark_service(request.user, recipe)
    return JsonResponse({
        "bookmarked": bookmarked,
        "bookmark_count": user_bookmark_count(request.user),
    })


@require_POST
@ajax_login_required
def bookmark_clear(request):
    Bookmark.objects.filter(user=request.user).delete()
    return JsonResponse({"message": "Semua bookmark dihapus.", "bookmark_count": 0})


@require_GET
@ajax_login_required
def bookmark_list_api(request):
    bookmarks = Bookmark.objects.filter(user=request.user).select_related("recipe")

    query = request.GET.get("q", "").strip()
    if query:
        bookmarks = bookmarks.filter(recipe__title__icontains=query)

    bookmarks = filter_bookmarks(bookmarks, request.GET)

    ordering = SORT_ORDERING.get(request.GET.get("sort", "newest"), "-created_at")
    bookmarks = bookmarks.order_by(ordering, "-pk")

    paginator = Paginator(bookmarks, PAGE_SIZE)
    page_obj = paginator.get_page(request.GET.get("page"))

    results = []
    for bookmark in page_obj:
        recipe = bookmark.recipe
        summary = get_vote_summary(recipe, request.user)
        category = getattr(recipe, CATEGORY_FIELD, "") if CATEGORY_FIELD else ""
        results.append({
            "pk": bookmark.pk,
            "fields": {
                "recipe_id": recipe.pk,
                "title": recipe.title,
                "saved_at": bookmark.created_at.isoformat(),
                "source": "community" if recipe.author_id else "api",
                "category": str(category) if category else "",
                "upvotes": summary["upvotes"],
                "downvotes": summary["downvotes"],
                "score": summary["score"],
                "user_vote": summary["user_vote"],
            },
        })

    return JsonResponse({
        "results": results,
        "pagination": {
            "page": page_obj.number,
            "num_pages": paginator.num_pages,
            "has_previous": page_obj.has_previous(),
            "has_next": page_obj.has_next(),
        },
        "total": user_bookmark_count(request.user),
        "filtered_count": paginator.count,
        "categories": available_categories(request.user),
    })

@login_required
def bookmark_list(request):
    filters = {
        key: request.GET.get(key, "")
        for key in ("q", "sort", "source", "vote", "min_score", "category")
    }
    if filters["sort"] not in SORT_ORDERING:
        filters["sort"] = "newest"

    return render(request, "voting/bookmark_list.html", {
        "total": user_bookmark_count(request.user),
        "filters": filters,
        "login_url": resolve_url(settings.LOGIN_URL),
    })