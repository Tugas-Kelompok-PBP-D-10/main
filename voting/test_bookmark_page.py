from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

User = get_user_model()


class BookmarkPageTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="page-user")
        self.url = reverse("voting:bookmark_list")

    def test_anonymous_is_redirected(self):
        self.assertEqual(self.client.get(self.url).status_code, 302)

    def test_page_is_a_skeleton_that_points_to_the_api(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("voting:bookmark_list_api"))
        self.assertContains(response, "data-bookmark-count")

    def test_filters_are_prefilled_from_query_string(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url, {"q": "nasi", "source": "api"})
        self.assertContains(response, 'value="nasi"')
        self.assertContains(response, 'value="api" selected')

    def test_page_includes_recipe_modal_and_recipe_api_urls(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertContains(response, 'id="nutritionModal"')
        self.assertContains(response, "JS/recipe.js")
        self.assertContains(response, reverse("recipe:api_detail", args=[0]))
        self.assertContains(response, reverse("recipe:api_complete", args=[0]))
