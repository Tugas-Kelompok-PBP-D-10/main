from rest_framework import serializers

from .models import (
    CookingLog,
    CookingStreak,
    Badge,
    UserBadge,
    NutritionTarget,
)


class CookingHistorySerializer(serializers.ModelSerializer):
    protein = serializers.IntegerField(source="protein_g", read_only=True)
    carbs = serializers.IntegerField(source="carbs_g", read_only=True)
    fat = serializers.IntegerField(source="fat_g", read_only=True)

    class Meta:
        model = CookingLog
        fields = [
            "id",
            "recipe_name",
            "cooked_on",
            "protein",
            "carbs",
            "fat",
            "calories",
        ]

    def get_earned(self, obj):
        earned_badge_ids = self.context.get("earned_badge_ids", set())
        return obj.id in earned_badge_ids

class NutritionTargetSerializer(serializers.ModelSerializer):
    protein_g = serializers.IntegerField(min_value=1, max_value=10000)
    carbs_g = serializers.IntegerField(min_value=1, max_value=10000)
    fat_g = serializers.IntegerField(min_value=1, max_value=10000)

    class Meta:
        model = NutritionTarget
        fields = [
            "protein_g",
            "carbs_g",
            "fat_g",
            "updated_at",
        ]
        read_only_fields = ["updated_at"]