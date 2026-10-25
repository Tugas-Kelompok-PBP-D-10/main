from unittest import skipUnless

from django.contrib.auth import get_user_model
from django.test import TestCase

from recipe.models import Recipe
from .models import Bookmark, Vote
from .services import (
    cast_vote,
    filter_bookmarks,
    recipe_has_field,
    remove_vote,
    toggle_bookmark,
    user_bookmark_count,
    with_popularity,
)

User = get_user_model()


class VotingServiceTests(TestCase):
    def setUp(self):
        self.author = User.objects.create_user(username="author")
        self.user = User.objects.create_user(username="voter")
        self.recipe = Recipe.objects.create(title="Sup Sayur", author=self.author)

    def seed_downvotes(self, count):
        voters = [
            User.objects.create_user(username=f"downvoter-{i}")
            for i in range(count)
        ]
        Vote.objects.bulk_create([
            Vote(user=voter, recipe=self.recipe, value=Vote.DOWNVOTE)
            for voter in voters
        ])

    def test_new_upvote(self):
        result = cast_vote(self.user, self.recipe, 1)
        self.assertEqual(result["upvotes"], 1)
        self.assertEqual(result["score"], 1)
        self.assertEqual(result["user_vote"], 1)
        self.assertFalse(result["deleted"])

    def test_same_vote_toggles_off(self):
        cast_vote(self.user, self.recipe, 1)
        result = cast_vote(self.user, self.recipe, 1)
        self.assertEqual(result["score"], 0)
        self.assertIsNone(result["user_vote"])
        self.assertFalse(Vote.objects.filter(user=self.user, recipe=self.recipe).exists())

    def test_opposite_vote_switches_value(self):
        cast_vote(self.user, self.recipe, 1)
        result = cast_vote(self.user, self.recipe, -1)
        self.assertEqual(result["upvotes"], 0)
        self.assertEqual(result["downvotes"], 1)
        self.assertEqual(result["score"], -1)
        self.assertEqual(result["user_vote"], -1)
        self.assertEqual(Vote.objects.filter(user=self.user, recipe=self.recipe).count(), 1)

    def test_invalid_vote_is_rejected(self):
        with self.assertRaises(ValueError):
            cast_vote(self.user, self.recipe, 0)
        with self.assertRaises(ValueError):
            cast_vote(self.user, self.recipe, 2)
        with self.assertRaises(ValueError):
            cast_vote(self.user, self.recipe, "abc")

    def test_99_downvotes_do_not_delete_recipe(self):
        self.seed_downvotes(98)
        result = cast_vote(self.user, self.recipe, -1)
        self.assertEqual(result["downvotes"], 99)
        self.assertFalse(result["deleted"])
        self.assertTrue(Recipe.objects.filter(pk=self.recipe.pk).exists())

    def test_100_downvotes_delete_recipe(self):
        self.seed_downvotes(99)
        recipe_id = self.recipe.pk
        result = cast_vote(self.user, self.recipe, -1)
        self.assertEqual(result["downvotes"], 100)
        self.assertTrue(result["deleted"])
        self.assertFalse(Recipe.objects.filter(pk=recipe_id).exists())

    def test_recipe_without_author_is_never_auto_deleted(self):
        recipe = Recipe.objects.create(title="Resep API", author=None)
        voters = [
            User.objects.create_user(username=f"api-voter-{i}")
            for i in range(100)
        ]
        Vote.objects.bulk_create([
            Vote(user=v, recipe=recipe, value=Vote.DOWNVOTE) for v in voters
        ])
        result = cast_vote(self.user, recipe, -1)
        self.assertFalse(result["deleted"])
        self.assertTrue(Recipe.objects.filter(pk=recipe.pk).exists())

    def test_remove_vote_deletes_only_own_vote(self):
        other = User.objects.create_user(username="other-voter")
        cast_vote(other, self.recipe, 1)
        cast_vote(self.user, self.recipe, -1)
        result = remove_vote(self.user, self.recipe)
        self.assertEqual(result["score"], 1)
        self.assertIsNone(result["user_vote"])
        self.assertFalse(result["deleted"])
        self.assertTrue(Vote.objects.filter(user=other, recipe=self.recipe).exists())

    def test_remove_vote_without_vote_is_harmless(self):
        result = remove_vote(self.user, self.recipe)
        self.assertEqual(result["score"], 0)
        self.assertIsNone(result["user_vote"])

    def test_bookmark_toggles_and_counts(self):
        other = Recipe.objects.create(title="Gado-Gado", author=self.author)
        self.assertTrue(toggle_bookmark(self.user, self.recipe))
        self.assertTrue(toggle_bookmark(self.user, other))
        self.assertEqual(user_bookmark_count(self.user), 2)
        self.assertFalse(toggle_bookmark(self.user, self.recipe))
        self.assertEqual(user_bookmark_count(self.user), 1)

    def test_bookmark_counter_is_per_user(self):
        toggle_bookmark(self.author, self.recipe)
        self.assertEqual(user_bookmark_count(self.user), 0)

    def test_bookmark_cascades_when_recipe_is_deleted(self):
        toggle_bookmark(self.user, self.recipe)
        self.seed_downvotes(99)
        recipe_id = self.recipe.pk
        cast_vote(self.user, self.recipe, -1)
        self.assertFalse(Recipe.objects.filter(pk=recipe_id).exists())
        self.assertFalse(Bookmark.objects.filter(user=self.user, recipe_id=recipe_id).exists())

    def test_popularity_ordering(self):
        popular = Recipe.objects.create(title="Populer", author=self.author)
        cast_vote(self.user, popular, 1)
        cast_vote(self.user, self.recipe, -1)
        ordered = list(with_popularity(Recipe.objects.all()).order_by("-popularity"))
        self.assertEqual(ordered[0].pk, popular.pk)
        self.assertEqual(ordered[0].popularity, 1)


class BookmarkFilterServiceTests(TestCase):
    def setUp(self):
        self.author = User.objects.create_user(username="f-author")
        self.user = User.objects.create_user(username="f-user")
        self.voter = User.objects.create_user(username="f-voter")
        self.nasi = Recipe.objects.create(title="Nasi Goreng", author=self.author)
        self.gado = Recipe.objects.create(title="Gado-Gado", author=self.author)
        self.api = Recipe.objects.create(title="Resep API", author=None)
        for recipe in (self.nasi, self.gado, self.api):
            Bookmark.objects.create(user=self.user, recipe=recipe)
        # Skor awal: Nasi Goreng 2, Gado-Gado -1, Resep API 0
        cast_vote(self.user, self.nasi, 1)
        cast_vote(self.voter, self.nasi, 1)
        cast_vote(self.user, self.gado, -1)

    def titles(self, **params):
        queryset = Bookmark.objects.filter(user=self.user).select_related("recipe")
        return sorted(b.recipe.title for b in filter_bookmarks(queryset, params))

    def test_filter_by_source(self):
        self.assertEqual(self.titles(source="community"), ["Gado-Gado", "Nasi Goreng"])
        self.assertEqual(self.titles(source="api"), ["Resep API"])

    def test_filter_by_my_vote(self):
        self.assertEqual(self.titles(vote="up"), ["Nasi Goreng"])
        self.assertEqual(self.titles(vote="down"), ["Gado-Gado"])
        self.assertEqual(self.titles(vote="none"), ["Resep API"])

    def test_filter_by_min_score(self):
        self.assertEqual(self.titles(min_score="1"), ["Nasi Goreng"])
        self.assertEqual(self.titles(min_score="0"), ["Nasi Goreng", "Resep API"])

    def test_invalid_min_score_is_ignored(self):
        self.assertEqual(
            self.titles(min_score="abc"),
            ["Gado-Gado", "Nasi Goreng", "Resep API"],
        )

    def test_filters_can_be_combined(self):
        self.assertEqual(self.titles(source="community", vote="up"), ["Nasi Goreng"])
        self.assertEqual(self.titles(source="api", vote="up"), [])

    @skipUnless(recipe_has_field("category"), "Recipe belum punya field category")
    def test_filter_by_category(self):
        Recipe.objects.filter(pk=self.nasi.pk).update(category="Vegan")
        self.assertEqual(self.titles(category="Vegan"), ["Nasi Goreng"])