from django.conf import settings
from django.db import models
from django.db.models import Q


class Vote(models.Model):
    UPVOTE = 1
    DOWNVOTE = -1
    VALUE_CHOICES = [
        (UPVOTE, "Upvote"),
        (DOWNVOTE, "Downvote"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="recipe_votes",
    )
    recipe = models.ForeignKey(
        "recipe.Recipe",
        on_delete=models.CASCADE,
        related_name="votes",
    )
    value = models.SmallIntegerField(choices=VALUE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "recipe"],
                name="unique_vote_per_user_recipe",
            ),
            models.CheckConstraint(
                condition=Q(value__in=[1, -1]),
                name="vote_value_must_be_plus_or_minus_one",
            ),
        ]
        indexes = [models.Index(fields=["recipe", "value"])]

    def __str__(self):
        return f"{self.user} -> {self.recipe} ({self.value})"


class Bookmark(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="bookmarks",
    )
    recipe = models.ForeignKey(
        "recipe.Recipe",
        on_delete=models.CASCADE,
        related_name="bookmarked_by",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "recipe"],
                name="unique_bookmark_per_user_recipe",
            ),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} bookmarked {self.recipe}"