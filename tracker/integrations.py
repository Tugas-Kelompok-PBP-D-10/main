
import uuid
from dataclasses import dataclass
from django.db import transaction

from .services import record_cook


@dataclass(frozen=True)
class RecipeSnapshot:
    """
    Data resep yang sudah divalidasi oleh backend Recipe.

    Tidak mengambil data langsung dari browser.
    """
    name: str
    protein_g: int
    carbs_g: int
    fat_g: int
    calories: int


def validate_recipe_snapshot(recipe):
    """Memastikan data resep valid sebelum dicatat."""

    if not isinstance(recipe, RecipeSnapshot):
        raise ValueError("Format data resep tidak valid.")

    if not isinstance(recipe.name, str) or not recipe.name.strip():
        raise ValueError("Nama resep tidak boleh kosong.")

    for field in (
        "protein_g",
        "carbs_g",
        "fat_g",
        "calories",
    ):
        value = getattr(recipe, field)

        if type(value) is not int or value < 0:
            raise ValueError(
                f"Nilai {field} harus bilangan bulat nonnegatif."
            )


@transaction.atomic
def complete_recipe_cooking(
    *,
    user,
    recipe,
    request_id,
):
    """
    Jembatan antara Recipe dan Tracker.

    Saat ini:
    - validasi data resep
    - catat CookingLog
    - perbarui CookingStreak
    - berikan Achievement Badge

    Belum melakukan auto-deduct Inventory.
    """

    if not user.is_authenticated:
        raise ValueError("Pengguna harus login.")

    validate_recipe_snapshot(recipe)

    try:
        request_id = uuid.UUID(str(request_id))
    except (ValueError, TypeError, AttributeError):
        raise ValueError("Request ID tidak valid.")

    new_badges = record_cook(
        user=user,
        recipe_name=recipe.name.strip(),
        protein_g=recipe.protein_g,
        carbs_g=recipe.carbs_g,
        fat_g=recipe.fat_g,
        calories=recipe.calories,
        request_id=request_id,
    )

    return new_badges
