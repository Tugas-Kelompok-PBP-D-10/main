from django.contrib import admin, messages

from .forms import RecipeAdminForm
from .models import Ingredient, Recipe, RecipeCookingEvent, RecipeInteraction
from .services import (
    calculate_and_store_recipe_nutrition,
    recipe_has_missing_nutrition,
)


@admin.action(description="Hitung ulang nutrisi yang masih kosong dari Spoonacular")
def recalculate_missing_recipe_nutrition(modeladmin, request, queryset):
    updated = 0
    skipped = 0
    for recipe in queryset:
        if not recipe_has_missing_nutrition(recipe):
            skipped += 1
            continue
        try:
            result = calculate_and_store_recipe_nutrition(recipe)
        except Exception:
            result = {"status": "upstream_error", "updated": []}
        if result.get("status") == "ok":
            updated += 1
        else:
            skipped += 1

    modeladmin.message_user(
        request,
        f"Nutrisi diperbarui untuk {updated} resep; {skipped} resep tetap tanpa perubahan.",
        level=messages.INFO,
    )


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    form = RecipeAdminForm
    actions = (recalculate_missing_recipe_nutrition,)
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

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        # Pembuatan resep baru di admin menghitung nutrisi sekali; data lama
        # hanya dihitung ulang melalui action yang dipilih secara eksplisit.
        if not change and recipe_has_missing_nutrition(obj):
            try:
                result = calculate_and_store_recipe_nutrition(obj)
            except Exception:
                result = {"status": "upstream_error", "updated": []}
            if result.get("status") not in {"ok", "complete"}:
                self.message_user(
                    request,
                    "Resep tersimpan. Nutrisi belum tersedia; gunakan action hitung ulang jika diperlukan.",
                    level=messages.INFO,
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
