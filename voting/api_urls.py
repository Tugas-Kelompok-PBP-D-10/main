from django.urls import path

from . import api_views

app_name = "api-voting"

urlpatterns = [
    path("recipes/<int:recipe_id>/vote/", api_views.recipe_vote, name="recipe-vote"),
    path(
        "recipes/<int:recipe_id>/bookmark/",
        api_views.recipe_bookmark,
        name="recipe-bookmark",
    ),
    path("bookmarks/", api_views.bookmark_list, name="bookmark-list"),
]