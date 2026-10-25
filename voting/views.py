from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET, require_POST

from recipe.models import Recipe
from .decorators import ajax_login_required
from .services import cast_vote, get_vote_summary, remove_vote


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