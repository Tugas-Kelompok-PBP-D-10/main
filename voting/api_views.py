from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import (
    api_view, authentication_classes, permission_classes,
)
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response

from recipe.models import Recipe, RecipeInteraction
from .models import Bookmark
from .serializers import BookmarkSerializer, VoteInputSerializer
from .services import (
    available_categories,
    cast_vote,
    filter_bookmarks,
    get_vote_summary,
    remove_vote,
    user_bookmark_count,
)
from .services import toggle_bookmark as toggle_bookmark_service
from .views import PAGE_SIZE, SORT_ORDERING


@api_view(["GET", "HEAD", "POST", "DELETE"])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticatedOrReadOnly])
def recipe_vote(request, recipe_id):
    recipe = get_object_or_404(Recipe, pk=recipe_id)

    if request.method in ("GET", "HEAD"):
        summary = get_vote_summary(recipe, request.user)
        if not request.user.is_authenticated:
            return Response({"score": summary["score"]})
        return Response(summary)

    if request.method == "DELETE":
        return Response(remove_vote(request.user, recipe))

    serializer = VoteInputSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    return Response(
        cast_vote(request.user, recipe, serializer.validated_data["value"])
    )


@api_view(["POST"])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticated])
def recipe_bookmark(request, recipe_id):
    recipe = get_object_or_404(Recipe, pk=recipe_id)
    bookmarked = toggle_bookmark_service(request.user, recipe)
    return Response({
        "bookmarked": bookmarked,
        "bookmark_count": user_bookmark_count(request.user),
    })


@api_view(["GET", "HEAD", "DELETE"])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticated])
def bookmark_list(request):
    if request.method == "DELETE":
        Bookmark.objects.filter(user=request.user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    bookmarks = Bookmark.objects.filter(user=request.user).select_related("recipe")

    query = request.query_params.get("q", "").strip()
    if query:
        bookmarks = bookmarks.filter(recipe__title__icontains=query)

    bookmarks = filter_bookmarks(bookmarks, request.query_params)

    ordering = SORT_ORDERING.get(
        request.query_params.get("sort", "newest"), "-created_at",
    )
    bookmarks = bookmarks.order_by(ordering, "-pk")

    paginator = Paginator(bookmarks, PAGE_SIZE)
    page_obj = paginator.get_page(request.query_params.get("page"))
    page_bookmarks = list(page_obj)

    # Status "dilihat" / "sudah dimasak" diambil dengan satu query untuk seluruh halaman.
    interactions = {
        row["recipe_id"]: row
        for row in RecipeInteraction.objects.filter(
            user=request.user,
            recipe_id__in=[bookmark.recipe_id for bookmark in page_bookmarks],
        ).values("recipe_id", "viewed_at", "completed_at")
    }

    serializer = BookmarkSerializer(
        page_bookmarks, many=True,
        context={"request": request, "interactions": interactions},
    )
    return Response({
        "results": serializer.data,
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