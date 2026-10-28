from functools import wraps

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import resolve_url


def ajax_login_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse(
                {
                    "message": "Silakan login terlebih dahulu.",
                    "login_url": resolve_url(settings.LOGIN_URL),
                },
                status=401,
            )
        return view_func(request, *args, **kwargs)

    return wrapper