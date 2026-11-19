
from django.contrib import admin
from django.conf import settings
from django.urls import path, include
from django.shortcuts import redirect
from django.conf.urls.static import static


def home_redirect(request):
    if request.user.is_authenticated:
        return redirect("recipe:home")

    return redirect("authentication:login")


urlpatterns = [
    path("admin/", admin.site.urls),

    path("api-auth/", include("rest_framework.urls")),

    # Django Allauth
    path("accounts/", include("allauth.urls")),

    # Halaman pertama website
    path("", home_redirect, name="home"),

    # Modul Authentication
    path("", include("authentication.urls")),

    # Modul Recipe
    path("recipe/", include("recipe.urls")),

    # Modul Tracker
    path("tracker/", include("tracker.urls")),

    # Modul Inventori
    path("inventori/", include("inventori.urls")),
    path("api-inventori/v1/", include("inventori.api_urls")),

    # Modul Voting / Bookmark
    path("voting/", include("voting.urls")),
    path("api-voting/v1/", include("voting.api_urls")),
]


if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )
