from rest_framework import serializers
from .models import Recipe


class RecipeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recipe
        fields = [
            "id",
            "title",
            "description",
            "preparation_time",
            "cooking_time",
            "servings",
            "image",
            "image_url",
            "source_type",
            "source_name",
            "is_published",
            "calories",
            "protein",
            "carbohydrates",
            "fat",
            "nutrition_basis",
            "ingredients",
            "instructions",
            "created_at",
        ]