from django import forms

from .models import Recipe
from .services import normalize_recipe_ingredients


MAX_RECIPE_IMAGE_BYTES = 5 * 1024 * 1024
MAX_RECIPE_INGREDIENTS = 50
MAX_RECIPE_STEPS = 50


class RecipeIngredientsValidationMixin:
    def clean_ingredients(self):
        ingredients = self.cleaned_data.get("ingredients")
        try:
            return normalize_recipe_ingredients(ingredients)
        except ValueError as error:
            raise forms.ValidationError(str(error)) from error


class RecipeAdminForm(RecipeIngredientsValidationMixin, forms.ModelForm):
    class Meta:
        model = Recipe
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.is_bound and not self.instance.pk:
            # Resep yang dibuat langsung di admin merupakan data lokal.
            self.initial["source_type"] = "local"
        if "calories" in self.fields:
            self.fields["calories"].help_text = "Masukkan kilokalori (kcal)."
        for field in ("protein", "fat", "carbohydrates"):
            if field in self.fields:
                self.fields[field].help_text = "Masukkan gram (g)."
        if "nutrition_basis" in self.fields:
            self.fields["nutrition_basis"].help_text = (
                "Pilih apakah nilai berlaku per porsi, untuk seluruh resep, "
                "atau biarkan belum diketahui."
            )


class RecipeSubmissionForm(RecipeIngredientsValidationMixin, forms.ModelForm):
    ingredients = forms.JSONField(widget=forms.HiddenInput())
    instructions = forms.CharField(widget=forms.HiddenInput())

    class Meta:
        model = Recipe
        fields = ("title", "description", "image", "servings", "ingredients", "instructions")

    def clean_ingredients(self):
        ingredients = self.cleaned_data.get("ingredients")
        try:
            normalized = normalize_recipe_ingredients(
                ingredients,
                require_items=True,
                require_quantities=True,
            )
            if len(normalized) > MAX_RECIPE_INGREDIENTS:
                raise ValueError("Maksimal 50 bahan untuk satu resep.")
            return normalized
        except ValueError as error:
            raise forms.ValidationError(str(error)) from error

    def clean_instructions(self):
        instructions = self.cleaned_data.get("instructions", "")
        steps = [step.strip() for step in instructions.splitlines() if step.strip()]
        if not steps:
            raise forms.ValidationError("Tambahkan sedikitnya satu langkah memasak.")
        if len(steps) > MAX_RECIPE_STEPS:
            raise forms.ValidationError("Maksimal 50 langkah untuk satu resep.")
        return "\n".join(steps)

    def clean_image(self):
        image = self.cleaned_data.get("image")
        if image and image.size > MAX_RECIPE_IMAGE_BYTES:
            raise forms.ValidationError("Ukuran foto maksimal 5 MB.")
        return image
