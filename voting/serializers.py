from rest_framework import serializers

from .models import Bookmark, Vote
from .services import CATEGORY_FIELD, get_vote_summary


class VoteInputSerializer(serializers.Serializer):
    value = serializers.ChoiceField(choices=[Vote.UPVOTE, Vote.DOWNVOTE])


class BookmarkSerializer(serializers.ModelSerializer):
    recipe_id = serializers.IntegerField(read_only=True)
    title = serializers.CharField(source="recipe.title", read_only=True)
    saved_at = serializers.DateTimeField(source="created_at", read_only=True)
    preparation_time = serializers.IntegerField(
        source="recipe.preparation_time", read_only=True,
    )
    cooking_time = serializers.IntegerField(
        source="recipe.cooking_time", read_only=True,
    )
    servings = serializers.IntegerField(source="recipe.servings", read_only=True)
    is_published = serializers.BooleanField(
        source="recipe.is_published", read_only=True,
    )
    source = serializers.SerializerMethodField()
    category = serializers.SerializerMethodField()
    image_url = serializers.SerializerMethodField()
    votes = serializers.SerializerMethodField()
    viewed = serializers.SerializerMethodField()
    completed = serializers.SerializerMethodField()

    class Meta:
        model = Bookmark
        fields = [
            "id", "recipe_id", "title", "saved_at", "source", "category",
            "image_url", "preparation_time", "cooking_time", "servings",
            "is_published", "votes", "viewed", "completed",
        ]

    def get_source(self, obj):
        return "community" if obj.recipe.author_id else "api"

    def get_category(self, obj):
        category = getattr(obj.recipe, CATEGORY_FIELD, "") if CATEGORY_FIELD else ""
        return str(category) if category else ""

    def get_image_url(self, obj):
        recipe = obj.recipe
        try:
            stored = recipe.image.url if recipe.image else ""
        except (OSError, ValueError):
            stored = ""
        url = stored or recipe.image_url or ""
        request = self.context.get("request")
        # Foto unggahan berupa path relatif (/media/...), aplikasi mobile butuh URL absolut.
        if url and request is not None:
            return request.build_absolute_uri(url)
        return url

    def get_votes(self, obj):
        return get_vote_summary(obj.recipe, self.context["request"].user)

    def _interaction(self, obj):
        return self.context.get("interactions", {}).get(obj.recipe_id, {})

    def get_viewed(self, obj):
        return bool(self._interaction(obj).get("viewed_at"))

    def get_completed(self, obj):
        return bool(self._interaction(obj).get("completed_at"))