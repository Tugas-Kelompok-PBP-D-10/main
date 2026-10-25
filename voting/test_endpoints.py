from django.conf import settings
from django.contrib.auth import get_user_model
from django.shortcuts import resolve_url
from django.test import TestCase
from django.urls import reverse

from recipe.models import Recipe
from .models import Vote
from .services import cast_vote

User = get_user_model()


class VoteEndpointTests(TestCase):
    def setUp(self):
        self.author = User.objects.create_user(username="recipe-author")
        self.user = User.objects.create_user(username="signed-in")
        self.recipe = Recipe.objects.create(title="Nasi Goreng Sisa", author=self.author)
        self.url = reverse("voting:vote", args=[self.recipe.pk])

    def test_anonymous_vote_returns_401_json(self):
        response = self.client.post(self.url, {"value": "1"})
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["login_url"], resolve_url(settings.LOGIN_URL))
        self.assertFalse(Vote.objects.exists())

    def test_vote_endpoint_returns_json(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url, {"value": "1"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["score"], 1)
        self.assertEqual(data["user_vote"], 1)
        self.assertFalse(data["deleted"])

    def test_invalid_vote_returns_400(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url, {"value": "0"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("message", response.json())

    def test_vote_endpoint_rejects_get(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(self.url).status_code, 405)

    def test_vote_unknown_recipe_is_404(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse("voting:vote", args=[9999]), {"value": "1"})
        self.assertEqual(response.status_code, 404)


class VoteReadDeleteTests(TestCase):
    def setUp(self):
        self.author = User.objects.create_user(username="rd-author")
        self.voter = User.objects.create_user(username="rd-voter")
        self.user = User.objects.create_user(username="rd-user")
        self.recipe = Recipe.objects.create(title="Rawon", author=self.author)
        cast_vote(self.voter, self.recipe, 1)

    def test_summary_for_anonymous_hides_breakdown(self):
        response = self.client.get(reverse("voting:vote_summary", args=[self.recipe.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {"score": 1})

    def test_summary_for_signed_in_user_shows_breakdown(self):
        self.client.force_login(self.user)
        data = self.client.get(reverse("voting:vote_summary", args=[self.recipe.pk])).json()
        self.assertEqual(data["upvotes"], 1)
        self.assertEqual(data["downvotes"], 0)
        self.assertEqual(data["score"], 1)
        self.assertIsNone(data["user_vote"])

    def test_summary_unknown_recipe_is_404(self):
        response = self.client.get(reverse("voting:vote_summary", args=[9999]))
        self.assertEqual(response.status_code, 404)

    def test_remove_vote_deletes_own_vote(self):
        cast_vote(self.user, self.recipe, -1)
        self.client.force_login(self.user)
        data = self.client.post(reverse("voting:vote_remove", args=[self.recipe.pk])).json()
        self.assertEqual(data["score"], 1)
        self.assertIsNone(data["user_vote"])
        self.assertFalse(Vote.objects.filter(user=self.user, recipe=self.recipe).exists())

    def test_remove_vote_without_vote_is_harmless(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse("voting:vote_remove", args=[self.recipe.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["score"], 1)

    def test_remove_vote_requires_login_and_post(self):
        url = reverse("voting:vote_remove", args=[self.recipe.pk])
        self.assertEqual(self.client.post(url).status_code, 401)
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(url).status_code, 405)     