from django.contrib import admin
from .models import Bookmark, Vote


@admin.register(Vote)
class VoteAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "recipe", "value", "created_at")
    list_filter = ("value", "created_at")
    search_fields = ("user__username", "recipe__title")


@admin.register(Bookmark)
class BookmarkAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "recipe", "created_at")
    list_filter = ("created_at",)
    search_fields = ("user__username", "recipe__title")