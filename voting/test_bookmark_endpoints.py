from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from recipe.models import Recipe, RecipeInteraction
from .models import Bookmark
from .services import cast_vote

User = get_user_model()


class BookmarkToggleEndpointTests(TestCase):
    def setUp(self):
        self.author = User.objects.create_user(username="bt-author")
        self.user = User.objects.create_user(username="bt-user")
        self.recipe = Recipe.objects.create(title="Nasi Goreng Sisa", author=self.author)
        self.url = reverse("voting:toggle_bookmark", args=[self.recipe.pk])

    def test_bookmark_endpoint_returns_counter(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {"bookmarked": True, "bookmark_count": 1})

    def test_anonymous_bookmark_returns_401(self):
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 401)
        self.assertFalse(Bookmark.objects.exists())


class BookmarkClearEndpointTests(TestCase):
    def setUp(self):
        author = User.objects.create_user(username="c-author")
        self.user = User.objects.create_user(username="c-user")
        self.other = User.objects.create_user(username="c-other")
        recipe = Recipe.objects.create(title="Gado-Gado", author=author)
        Bookmark.objects.create(user=self.user, recipe=recipe)
        Bookmark.objects.create(user=self.other, recipe=recipe)
        self.url = reverse("voting:bookmark_clear")

    def test_clear_removes_only_own_bookmarks(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["bookmark_count"], 0)
        self.assertEqual(Bookmark.objects.filter(user=self.user).count(), 0)
        self.assertEqual(Bookmark.objects.filter(user=self.other).count(), 1)

    def test_clear_rejects_get(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(self.url).status_code, 405)


class BookmarkApiTests(TestCase):
    def setUp(self):
        self.author = User.objects.create_user(username="api-author")
        self.user = User.objects.create_user(username="api-user")
        self.other = User.objects.create_user(username="api-other")
        self.nasi = Recipe.objects.create(title="Nasi Goreng", author=self.author)
        self.gado = Recipe.objects.create(title="Gado-Gado", author=self.author)
        Bookmark.objects.create(user=self.user, recipe=self.nasi)
        Bookmark.objects.create(user=self.other, recipe=self.gado)
        self.url = reverse("voting:bookmark_list_api")

    def titles(self, **params):
        response = self.client.get(self.url, params)
        self.assertEqual(response.status_code, 200)
        return [item["fields"]["title"] for item in response.json()["results"]]

    def test_anonymous_gets_401(self):
        self.assertEqual(self.client.get(self.url).status_code, 401)

    def test_lists_only_own_bookmarks_with_totals(self):
        self.client.force_login(self.user)
        data = self.client.get(self.url).json()
        self.assertEqual(len(data["results"]), 1)
        self.assertEqual(data["total"], 1)
        self.assertEqual(data["results"][0]["fields"]["title"], "Nasi Goreng")

    def test_search_without_result_keeps_total(self):
        self.client.force_login(self.user)
        data = self.client.get(self.url, {"q": "zzz"}).json()
        self.assertEqual(data["results"], [])
        self.assertEqual(data["filtered_count"], 0)
        self.assertEqual(data["total"], 1)

    def test_sort_by_title(self):
        Bookmark.objects.create(user=self.user, recipe=self.gado)
        self.client.force_login(self.user)
        self.assertEqual(self.titles(sort="title"), ["Gado-Gado", "Nasi Goreng"])

    def test_includes_vote_summary_of_the_viewer(self):
        cast_vote(self.user, self.nasi, 1)
        self.client.force_login(self.user)
        fields = self.client.get(self.url).json()["results"][0]["fields"]
        self.assertEqual(fields["score"], 1)
        self.assertEqual(fields["user_vote"], 1)
        self.assertEqual(fields["source"], "community")

    def test_includes_recipe_card_fields(self):
        Recipe.objects.filter(pk=self.nasi.pk).update(
            image_url="https://example.com/nasi.jpg",
            preparation_time=10,
            cooking_time=25,
            servings=4,
        )
        self.client.force_login(self.user)
        fields = self.client.get(self.url).json()["results"][0]["fields"]
        self.assertEqual(fields["image_url"], "https://example.com/nasi.jpg")
        self.assertEqual(fields["preparation_time"], 10)
        self.assertEqual(fields["cooking_time"], 25)
        self.assertEqual(fields["servings"], 4)
        self.assertTrue(fields["is_published"])
        self.assertFalse(fields["viewed"])
        self.assertFalse(fields["completed"])

    def test_uploaded_image_is_preferred_over_image_url(self):
        Recipe.objects.filter(pk=self.nasi.pk).update(
            image="recipes/nasi.jpg",
            image_url="https://example.com/lama.jpg",
        )
        self.client.force_login(self.user)
        fields = self.client.get(self.url).json()["results"][0]["fields"]
        self.assertTrue(fields["image_url"].endswith("recipes/nasi.jpg"))

    def test_unpublished_recipe_is_flagged_but_stays_listed(self):
        Recipe.objects.filter(pk=self.nasi.pk).update(is_published=False)
        self.client.force_login(self.user)
        data = self.client.get(self.url).json()
        self.assertEqual(data["total"], 1)
        self.assertFalse(data["results"][0]["fields"]["is_published"])

    def test_reports_only_the_viewers_interaction_status(self):
        now = timezone.now()
        RecipeInteraction.objects.create(user=self.user, recipe=self.nasi, viewed_at=now)
        RecipeInteraction.objects.create(
            user=self.other, recipe=self.nasi, viewed_at=now, completed_at=now
        )
        self.client.force_login(self.user)
        fields = self.client.get(self.url).json()["results"][0]["fields"]
        self.assertTrue(fields["viewed"])
        self.assertFalse(fields["completed"])

    def test_missing_optional_recipe_fields_do_not_break_the_api(self):
        self.client.force_login(self.user)
        fields = self.client.get(self.url).json()["results"][0]["fields"]
        self.assertEqual(fields["image_url"], "")
        self.assertIsNone(fields["preparation_time"])
        self.assertIsNone(fields["cooking_time"])
        self.assertIsNone(fields["servings"])

    def test_filter_by_source(self):
        api_recipe = Recipe.objects.create(title="Resep API", author=None)
        Bookmark.objects.create(user=self.user, recipe=api_recipe)
        self.client.force_login(self.user)
        self.assertEqual(self.titles(source="api"), ["Resep API"])
        self.assertEqual(self.titles(source="community"), ["Nasi Goreng"])

    def test_pagination_has_two_pages_for_13_bookmarks(self):
        for i in range(12):
            recipe = Recipe.objects.create(title=f"Resep {i:02d}", author=self.author)
            Bookmark.objects.create(user=self.user, recipe=recipe)
        self.client.force_login(self.user)
        first = self.client.get(self.url).json()
        self.assertEqual(len(first["results"]), 12)
        self.assertEqual(first["pagination"]["num_pages"], 2)
        self.assertTrue(first["pagination"]["has_next"])
        second = self.client.get(self.url, {"page": 2}).json()
        self.assertEqual(len(second["results"]), 1)
        self.assertFalse(second["pagination"]["has_next"])