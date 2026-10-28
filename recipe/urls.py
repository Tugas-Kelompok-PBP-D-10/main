from django.urls import path

from . import views


app_name = "recipe"

urlpatterns = [
    path("", views.recipe_home, name="home"),
    path(
        "api/recipes/<int:recipe_id>/",
        views.recipe_detail_api,
        name="api_detail",
    ),
    path(
        "api/recipes/<int:recipe_id>/interactions/",
        views.recipe_interaction_status,
        name="api_interactions",
    ),
    path(
        "api/recipes/<int:recipe_id>/interactions/view/",
        views.record_recipe_view,
        name="api_record_view",
    ),
    path(
        "api/recipes/<int:recipe_id>/interactions/complete/",
        views.complete_recipe,
        name="api_complete",
    ),
]
