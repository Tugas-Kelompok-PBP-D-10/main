from django.urls import path
from . import views

app_name = "voting"

urlpatterns = [
    path("<int:recipe_id>/vote/", views.vote, name="vote"),
    path("<int:recipe_id>/vote/remove/", views.vote_remove, name="vote_remove"),
    path("<int:recipe_id>/summary/", views.vote_summary, name="vote_summary"),
    path("<int:recipe_id>/bookmark/", views.toggle_bookmark, name="toggle_bookmark"),
    path("bookmarks/clear/", views.bookmark_clear, name="bookmark_clear"),
    path("api/bookmarks/", views.bookmark_list_api, name="bookmark_list_api"),
]