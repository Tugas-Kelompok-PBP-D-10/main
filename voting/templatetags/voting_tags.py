from urllib.parse import quote

from django import template
from django.conf import settings
from django.middleware.csrf import get_token
from django.shortcuts import resolve_url

from voting.models import Bookmark
from voting.services import get_vote_summary

register = template.Library()


@register.inclusion_tag("voting/_recipe_actions.html", takes_context=True)
def recipe_actions(context, recipe, size=""):
    request = context["request"]
    user = request.user
    is_authenticated = user.is_authenticated

    login_url = ""
    if not is_authenticated:
        login_url = f"{resolve_url(settings.LOGIN_URL)}?next={quote(request.get_full_path())}"

    return {
        "recipe": recipe,
        "size": size,
        "summary": get_vote_summary(recipe, user),
        "is_authenticated": is_authenticated,
        "login_url": login_url,
        "bookmarked": is_authenticated
        and Bookmark.objects.filter(user=user, recipe=recipe).exists(),
        "csrf_token": get_token(request),
    }