from django.urls import path,include
from . import views
from authentication.views import login_page
from django.contrib import admin

app_name = "voting"

urlpatterns = [
    path("<int:recipe_id>/vote/", views.vote, name="vote"),
    path("<int:recipe_id>/vote/remove/", views.vote_remove, name="vote_remove"),
    path("<int:recipe_id>/summary/", views.vote_summary, name="vote_summary"),
    path("<int:recipe_id>/bookmark/", views.toggle_bookmark, name="toggle_bookmark"),
    path("bookmarks/clear/", views.bookmark_clear, name="bookmark_clear"),
    path("api/bookmarks/", views.bookmark_list_api, name="bookmark_list_api"),

    path('admin/', admin.site.urls),
    path('accounts/login/', login_page, name='account_login'),
    path('accounts/', include('allauth.urls')),

    path('auth/', include('authentication.urls')),
    path('recipe/', include('recipe.urls')),
]