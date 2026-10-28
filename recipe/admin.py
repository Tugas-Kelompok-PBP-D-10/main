from django.contrib import admin

from .forms import RecipeAdminForm
from .models import Ingredient, Recipe, RecipeCookingEvent, RecipeInteraction


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    form = RecipeAdminForm
    list_display = (
        "title",
        "source_type",
        "servings",
        "preparation_time",
        "cooking_time",
        "is_published",
        "created_at",
    )
    list_filter = ("is_published", "source_type", "nutrition_basis")
    search_fields = ("title", "description", "source_name")
    readonly_fields = ("created_at",)
    ordering = ("title", "pk")
    fieldsets = (
        (
            "Identitas resep",
            {
                "fields": (
                    "title",
                    "description",
                    "image",
                    "image_url",
                    "source_type",
                    "source_name",
                    "spoonacular_id",
                    "is_published",
                    "author",
                )
            },
        ),
        (
            "Bahan dan cara memasak",
            {"fields": ("ingredients", "instructions")},
        ),
        (
            "Waktu dan porsi",
            {"fields": ("preparation_time", "cooking_time", "servings")},
        ),
        (
            "Nutrisi terverifikasi",
            {
                "fields": (
                    "nutrition_basis",
                    "calories",
                    "protein",
                    "carbohydrates",
                    "fat",
                    "additional_nutrition",
                )
            },
        ),
        ("Metadata", {"fields": ("created_at",), "classes": ("collapse",)}),
    )


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ("name", "quantity", "user", "created_at")
    list_filter = ("created_at",)
    search_fields = ("name", "user__username")
    readonly_fields = ("created_at",)
    ordering = ("name", "pk")


@admin.register(RecipeInteraction)
class RecipeInteractionAdmin(admin.ModelAdmin):
    list_display = ("recipe", "user", "viewed_at", "completed_at")
    list_filter = ("viewed_at", "completed_at")
    search_fields = ("recipe__title", "user__username")
    readonly_fields = (
        "user",
        "recipe",
        "viewed_at",
        "completed_at",
        "created_at",
        "updated_at",
    )
    ordering = ("-updated_at",)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(RecipeCookingEvent)
class RecipeCookingEventAdmin(admin.ModelAdmin):
    list_display = ("recipe", "user", "completed_at", "request_id")
    list_filter = ("completed_at",)
    search_fields = ("recipe__title", "user__username", "request_id")
    readonly_fields = ("user", "recipe", "request_id", "completed_at")
    ordering = ("-completed_at", "-pk")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
