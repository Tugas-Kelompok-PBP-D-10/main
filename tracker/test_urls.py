
from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect
from tracker import views

tracker_patterns = [
    path("", views.tracker_view, name="tracker"),
    path(
        "api/dashboard/",
        views.tracker_dashboard_api,
        name="dashboard_api"
    ),
    path(
        "complete/",
        views.complete_cooking,
        name="complete_cooking"
    ),
    path(
        "api/history/",
        views.cooking_history_api,
        name="history_api"
        ),
]

urlpatterns = [
    path("", lambda request: redirect("/tracker/")),

    path(
        "tracker/",
        include((tracker_patterns, "tracker"),
                namespace="tracker")
    ),

    path("admin/", admin.site.urls),

    path(
        "accounts/login/",
        lambda request: redirect(
            "/admin/login/?next=/tracker/"
        ),
        name="login"
    ),

]
