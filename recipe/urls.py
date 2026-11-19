from django.urls import path
from .api_views import RecipeListAPIView, RecipeDetailAPIView
from . import views

app_name = "recipe"

urlpatterns = [
    path("", views.recipe_home, name="home"),

    # Endpoint DRF utama (bisa dipakai Flutter)
    path("api/recipes/", RecipeListAPIView.as_view(), name="drf-recipe-list"),
    path("api/recipes/<int:pk>/detail/", RecipeDetailAPIView.as_view(), name="drf-recipe-detail"),

    # Endpoint API yang sudah ada sebelumnya
    path(
        "api/spoonacular/search/",
        views.spoonacular_recipe_search_api,
        name="api_spoonacular_search",
    ),
    path(
        "api/spoonacular/recipes/<int:spoonacular_id>/",
        views.spoonacular_recipe_detail_api,
        name="api_spoonacular_detail",
    ),
    path(
        "api/recipes/submit/",
        views.submit_recipe,
        name="api_submit",
    ),
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
    path(
        "api/spoonacular/recipes/<int:spoonacular_id>/complete/",
        views.complete_spoonacular_recipe,
        name="api_spoonacular_complete",
    ),
]