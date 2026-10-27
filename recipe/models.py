from django.conf import settings
from django.db import models
from django.db.models import Q
from django.core.validators import MinValueValidator


class Ingredient(models.Model):
    # Bahan tersimpan per pengguna; data lama tanpa akun tetap didukung.
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=100)
    quantity = models.CharField(max_length=50, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Recipe(models.Model):
    SOURCE_TYPE_CHOICES = [
        ("auto", "Pencarian Spoonacular otomatis"),
        ("local", "Resep lokal"),
        ("spoonacular", "Spoonacular"),
    ]
    NUTRITION_BASIS_CHOICES = [
        ("unknown", "Belum diketahui"),
        ("per_serving", "Per porsi"),
        ("whole_recipe", "Total resep"),
        ("mixed", "Campuran sumber"),
    ]

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="recipes",
    )
    title = models.CharField(max_length=255, verbose_name="Nama resep")
    description = models.TextField(blank=True, null=True, verbose_name="Deskripsi")
    preparation_time = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        verbose_name="Waktu persiapan (menit)",
    )
    cooking_time = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        verbose_name="Waktu memasak (menit)",
    )
    servings = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1)],
        verbose_name="Jumlah porsi",
    )
    image = models.ImageField(
        upload_to="recipes/",
        blank=True,
        verbose_name="Foto resep",
    )
    image_url = models.URLField(blank=True)
    source_type = models.CharField(
        max_length=16,
        choices=SOURCE_TYPE_CHOICES,
        default="auto",
        verbose_name="Jenis sumber data",
    )
    source_name = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Nama sumber resep",
    )
    is_published = models.BooleanField(
        default=True,
        verbose_name="Tampilkan di katalog",
    )
    spoonacular_id = models.PositiveBigIntegerField(
        null=True,
        blank=True,
        unique=True,
    )
    calories = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True
    )
    protein = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True
    )
    carbohydrates = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True
    )
    fat = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True
    )
    nutrition_basis = models.CharField(
        max_length=16,
        choices=NUTRITION_BASIS_CHOICES,
        default="unknown",
    )
    additional_nutrition = models.JSONField(default=dict, blank=True)
    ingredients = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Bahan dan takaran",
        help_text=(
            'Gunakan JSON berupa daftar, misalnya '
            '[{"name": "kentang", "amount": 300, "unit": "g"}]. '
            "Bahan tanpa jumlah numerik boleh disimpan sebagai teks."
        ),
    )
    instructions = models.TextField(
        blank=True,
        verbose_name="Langkah memasak",
        help_text="Tulis satu langkah per baris. Urutan baris menjadi nomor langkah.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class RecipeInteraction(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="recipe_interactions",
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name="interactions",
    )
    viewed_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("user", "recipe"),
                name="unique_recipe_interaction_user_recipe",
            ),
            models.CheckConstraint(
                condition=Q(completed_at__isnull=True)
                | Q(viewed_at__isnull=False),
                name="completed_recipe_was_viewed",
            ),
        ]

    def __str__(self):
        return f"{self.user} - {self.recipe}"
