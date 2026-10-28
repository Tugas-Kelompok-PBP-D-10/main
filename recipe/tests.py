import json
import os
import base64
from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Recipe, RecipeInteraction
from .services import (
    analyze_recipe_with_spoonacular,
    get_spoonacular_recipe,
    scale_ingredient_quantities,
)


class RecipePageTests(TestCase):
    def setUp(self):
        self.recipe = Recipe.objects.create(
            title="Sup Bayam",
            description="Sup dengan sayuran.",
            cooking_time=20,
            protein="12.50",
            ingredients=["Bayam", "Wortel"],
            instructions="Rebus air.\nMasukkan sayuran.",
        )

    @patch(
        "recipe.services.get_spoonacular_recipe",
        return_value={
            "status": "not_configured",
            "message": "Kunci API Spoonacular belum dikonfigurasi.",
            "data": None,
        },
    )
    def test_recipe_page_renders_module_template_and_card_urls(self, _spoonacular):
        response = self.client.get(reverse("recipe:home"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "Recipe/recipe.html")
        self.assertContains(response, 'data-detail-url="/recipe/api/recipes/')
        self.assertContains(response, 'data-login-url="/login/?next=%2Frecipe%2F"')
        self.assertContains(response, "Masuk untuk vote &amp; simpan")
        self.assertNotContains(response, 'class="vote__btn')
        self.assertContains(response, "12.50")
        self.assertNotContains(response, "350 kcal")

    def test_authenticated_recipe_page_is_readable_if_voting_urls_are_unwired(self):
        user = get_user_model().objects.create_user(
            username="recipe-page-user",
            password="test-password",
        )
        self.client.force_login(user)

        response = self.client.get(reverse("recipe:home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Vote dan simpan belum tersedia")
        self.assertNotContains(response, 'class="vote__btn')

    @patch(
        "recipe.services.get_spoonacular_recipe",
        return_value={
            "status": "not_configured",
            "message": "Kunci API Spoonacular belum dikonfigurasi.",
            "data": None,
        },
    )
    def test_detail_returns_only_available_local_fields(self, _spoonacular):
        response = self.client.get(
            reverse("recipe:api_detail", args=(self.recipe.pk,))
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["recipe"]["title"], "Sup Bayam")
        self.assertIsNone(payload["recipe"]["spoonacular_id"])
        self.assertEqual(payload["nutrition"]["protein"], {"value": 12.5, "unit": "g"})
        self.assertIsNone(payload["nutrition"]["calories"])
        self.assertEqual(
            payload["ingredients"],
            [
                {"name": "Bayam", "amount": None, "unit": "", "original": "Bayam"},
                {"name": "Wortel", "amount": None, "unit": "", "original": "Wortel"},
            ],
        )
        self.assertEqual(payload["nutrition"]["basis"], "unknown")
        self.assertEqual(
            payload["instructions"],
            ["Rebus air.", "Masukkan sayuran."],
        )
        self.assertEqual(payload["external"]["status"], "not_configured")

    @patch(
        "recipe.services.get_spoonacular_recipe",
        return_value={
            "status": "not_configured",
            "message": "",
            "data": None,
        },
    )
    def test_unknown_recipe_uses_json_error_response(self, _spoonacular):
        response = self.client.get(
            reverse("recipe:api_detail", args=(99999,))
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            response.json()["error"]["code"],
            "recipe_not_found",
        )

    @patch(
        "recipe.services.get_spoonacular_recipe",
        return_value={
            "status": "invalid_response",
            "message": "Format data eksternal tidak lengkap.",
            "data": {
                "nutrition": None,
                "extendedIngredients": None,
                "analyzedInstructions": None,
            },
        },
    )
    def test_missing_external_fields_fall_back_to_local_data(self, _spoonacular):
        response = self.client.get(
            reverse("recipe:api_detail", args=(self.recipe.pk,))
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["ingredients"][0]["original"],
            "Bayam",
        )
        self.assertEqual(
            response.json()["instructions"],
            ["Rebus air.", "Masukkan sayuran."],
        )

    @patch(
        "recipe.services.get_spoonacular_recipe",
        return_value={
            "status": "ok",
            "message": "",
            "data": {
                "id": 42,
                "title": "Sup Bayam",
                "summary": "<p>Ringkasan <strong>resep</strong>.</p>",
                "image": "https://images.example.test/sup.jpg",
                "nutrition": {
                    "nutrients": [
                        {"name": "Calories", "amount": 180, "unit": "kcal"},
                        {"name": "Protein", "amount": 9, "unit": "g"},
                        {"name": "Carbohydrates", "amount": 21, "unit": "g"},
                        {"name": "Fat", "amount": 5, "unit": "g"},
                        {"name": "Fiber", "amount": 4, "unit": "g"},
                    ]
                },
                "extendedIngredients": [{"original": "2 cups bayam"}],
                "analyzedInstructions": [
                    {"steps": [{"number": 1, "step": "Cuci bayam."}]}
                ],
            },
        },
    )
    def test_detail_merges_spoonacular_data_without_rendering_html(self, _spoonacular):
        response = self.client.get(
            reverse("recipe:api_detail", args=(self.recipe.pk,))
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["recipe"]["source"], "database+spoonacular")
        self.assertEqual(payload["recipe"]["spoonacular_id"], 42)
        self.assertEqual(payload["recipe"]["description"], "Sup dengan sayuran.")
        self.assertEqual(
            payload["nutrition"]["calories"],
            {"value": 180, "unit": "kcal"},
        )
        self.assertEqual(
            payload["nutrition"]["additional"],
            [{"name": "Fiber", "value": 4, "unit": "g"}],
        )
        self.assertEqual(payload["ingredients"][0]["original"], "Bayam")
        self.assertEqual(
            payload["instructions"],
            ["Rebus air.", "Masukkan sayuran."],
        )

    @patch(
        "recipe.services.get_spoonacular_recipe",
        return_value={
            "status": "ok",
            "message": "",
            "data": {
                "id": 77,
                "servings": 4,
                "nutrition": {
                    "nutrients": [
                        {"name": "Calories", "amount": 210, "unit": "kcal"},
                        {"name": "Protein", "amount": 11, "unit": "g"},
                    ]
                },
                "extendedIngredients": [
                    {
                        "name": "tomato",
                        "original": "2 medium tomatoes",
                        "amount": 2,
                        "unit": "medium",
                    },
                    {"name": "salt", "original": "salt"},
                ],
            },
        },
    )
    def test_servings_and_numeric_ingredient_quantities_are_returned(self, _spoonacular):
        recipe = Recipe.objects.create(title="Tomato soup", servings=None)

        response = self.client.get(reverse("recipe:api_detail", args=(recipe.pk,)))

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["recipe"]["servings"], 4)
        self.assertEqual(payload["nutrition"]["basis"], "per_serving")
        self.assertEqual(
            payload["ingredients"],
            [
                {
                    "name": "tomato",
                    "amount": 2,
                    "unit": "medium",
                    "original": "2 medium tomatoes",
                },
                {"name": "salt", "amount": None, "unit": "", "original": "salt"},
            ],
        )

    def test_local_gado_gado_does_not_search_for_an_unrelated_api_recipe(self):
        local_recipe = Recipe.objects.create(
            title="Gado-Gado",
            source_type="local",
            ingredients=[{"name": "tauge", "amount": 100, "unit": "g"}],
            instructions="Rebus tauge hingga matang.",
        )
        with patch("recipe.services._request_spoonacular") as request_api:
            response = self.client.get(
                reverse("recipe:api_detail", args=(local_recipe.pk,))
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["external"]["status"], "local")
        self.assertEqual(response.json()["nutrition"]["calories"], None)
        request_api.assert_not_called()

    def test_unpublished_recipe_is_not_public(self):
        draft = Recipe.objects.create(title="Resep draf", is_published=False)

        page = self.client.get(reverse("recipe:home"))
        detail = self.client.get(reverse("recipe:api_detail", args=(draft.pk,)))

        self.assertEqual(page.status_code, 200)
        self.assertNotContains(page, "Resep draf")
        self.assertEqual(detail.status_code, 404)

    def test_admin_recipe_management_page_is_available_to_staff_user(self):
        staff_user = get_user_model().objects.create_superuser(
            username="recipe-admin-test",
            email="recipe-admin@example.test",
            password="test-password",
        )
        self.client.force_login(staff_user)

        response = self.client.get(reverse("admin:recipe_recipe_changelist"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Nama resep")

    def test_uploaded_recipe_image_is_stored_and_linked_to_its_recipe(self):
        png_data = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/"
            "lV8AAAAASUVORK5CYII="
        )
        recipe = Recipe.objects.create(
            title="Resep dengan foto",
            image=SimpleUploadedFile(
                "resep.png",
                png_data,
                content_type="image/png",
            ),
        )
        try:
            self.assertTrue(os.path.exists(recipe.image.path))
            page = self.client.get(reverse("recipe:home"))

            self.assertEqual(page.status_code, 200)
            self.assertContains(page, recipe.image.url)
        finally:
            recipe.image.delete(save=False)


class RecipeManagementCommandTests(TestCase):
    def test_demo_command_creates_specific_local_recipe_and_is_repeatable(self):
        output = StringIO()

        call_command("seed_gado_gado_demo", stdout=output)
        first_recipe = Recipe.objects.get(title="Gado-Gado")
        first_description = first_recipe.description
        call_command("seed_gado_gado_demo", stdout=output)
        first_recipe.refresh_from_db()

        self.assertEqual(Recipe.objects.filter(title="Gado-Gado").count(), 1)
        self.assertEqual(first_recipe.description, first_description)
        self.assertEqual(first_recipe.source_type, "local")
        self.assertEqual(first_recipe.servings, 4)
        self.assertEqual(first_recipe.preparation_time, 25)
        self.assertEqual(first_recipe.cooking_time, 25)
        self.assertEqual(first_recipe.nutrition_basis, "unknown")
        self.assertIsNone(first_recipe.calories)
        self.assertGreaterEqual(len(first_recipe.ingredients), 10)
        self.assertEqual(len(first_recipe.instructions.splitlines()), 8)
        self.assertIn("tidak diubah", output.getvalue())

    def test_demo_command_does_not_overwrite_existing_recipe_with_same_name(self):
        existing = Recipe.objects.create(
            title="Gado-Gado",
            description="Resep milik pengguna.",
            ingredients=["data lama"],
        )

        call_command("seed_gado_gado_demo", stdout=StringIO())
        existing.refresh_from_db()

        self.assertEqual(Recipe.objects.filter(title="Gado-Gado").count(), 1)
        self.assertEqual(existing.description, "Resep milik pengguna.")
        self.assertEqual(existing.ingredients, ["data lama"])


class RecipeServiceUtilityTests(TestCase):
    def test_scale_helper_changes_numeric_amounts_without_mutating_base_list(self):
        ingredients = [
            {"name": "kentang", "amount": 400, "unit": "g"},
            {"name": "garam", "amount": None, "unit": "secukupnya"},
        ]

        result = scale_ingredient_quantities(ingredients, 4, 2)

        self.assertEqual(result[0]["amount"], 200)
        self.assertEqual(result[1]["amount"], None)
        self.assertEqual(ingredients[0]["amount"], 400)

    @patch("recipe.services._request_spoonacular")
    def test_custom_recipe_analysis_is_explicit_and_passes_local_data(self, request_api):
        recipe = Recipe(
            title="Gado-Gado",
            source_type="local",
            servings=4,
            ingredients=[{"name": "kacang tanah", "amount": 200, "unit": "g"}],
            instructions="Haluskan kacang tanah.",
        )
        request_api.return_value = {"nutrition": {"nutrients": []}}

        with patch.dict(os.environ, {"SPOONACULAR_API_KEY": "test-key"}):
            result = analyze_recipe_with_spoonacular(recipe, include_nutrition=True)

        self.assertEqual(result["status"], "ok")
        request_api.assert_called_once()
        self.assertEqual(request_api.call_args.kwargs["method"], "POST")
        self.assertEqual(request_api.call_args.kwargs["body"]["servings"], 4)
        self.assertEqual(
            request_api.call_args.kwargs["body"]["ingredients"],
            ["200 g kacang tanah"],
        )
        self.assertEqual(
            request_api.call_args.args[1]["includeNutrition"],
            "true",
        )


class RecipeInteractionTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="recipe-user",
            password="test-password",
        )
        self.recipe = Recipe.objects.create(title="Tumis Kangkung")
        self.status_url = reverse(
            "recipe:api_interactions",
            args=(self.recipe.pk,),
        )
        self.view_url = reverse(
            "recipe:api_record_view",
            args=(self.recipe.pk,),
        )
        self.complete_url = reverse(
            "recipe:api_complete",
            args=(self.recipe.pk,),
        )

    def test_anonymous_user_can_read_empty_status_but_cannot_write(self):
        status = self.client.get(self.status_url)
        response = self.client.post(self.view_url)

        self.assertEqual(status.status_code, 200)
        self.assertFalse(status.json()["authenticated"])
        self.assertFalse(status.json()["viewed"])
        self.assertEqual(response.status_code, 401)
        self.assertIn("/login/?next=%2Frecipe%2F", response.json()["login_url"])

    def test_view_is_recorded_once_and_status_is_available(self):
        self.client.force_login(self.user)

        first_response = self.client.post(self.view_url)
        second_response = self.client.post(self.view_url)

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(second_response.status_code, 200)
        self.assertTrue(second_response.json()["viewed"])
        self.assertEqual(
            RecipeInteraction.objects.filter(
                user=self.user,
                recipe=self.recipe,
            ).count(),
            1,
        )

    def test_state_change_requires_csrf_token(self):
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.user)

        response = csrf_client.post(self.view_url)

        self.assertEqual(response.status_code, 403)

    def test_completion_requires_explicit_confirmation_and_is_idempotent(self):
        self.client.force_login(self.user)

        missing_confirmation = self.client.post(
            self.complete_url,
            data=json.dumps({"confirmed": False}),
            content_type="application/json",
        )
        self.assertEqual(missing_confirmation.status_code, 400)
        self.assertFalse(
            RecipeInteraction.objects.filter(
                user=self.user,
                recipe=self.recipe,
            ).exists()
        )

        first_response = self.client.post(
            self.complete_url,
            data=json.dumps({"confirmed": True}),
            content_type="application/json",
        )
        first_completed_at = first_response.json()["completed_at"]
        second_response = self.client.post(
            self.complete_url,
            data=json.dumps({"confirmed": True}),
            content_type="application/json",
        )

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(second_response.status_code, 200)
        self.assertTrue(second_response.json()["viewed"])
        self.assertTrue(second_response.json()["completed"])
        self.assertEqual(second_response.json()["completed_at"], first_completed_at)
        self.assertEqual(RecipeInteraction.objects.count(), 1)

    def test_database_rejects_completion_without_a_view_timestamp(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                RecipeInteraction.objects.create(
                    user=self.user,
                    recipe=self.recipe,
                    completed_at=timezone.now(),
                )


class SpoonacularServiceTests(TestCase):
    def setUp(self):
        cache.clear()
        self.recipe = Recipe.objects.create(title="Sup Bayam")

    def tearDown(self):
        cache.clear()

    @patch("recipe.services._request_spoonacular")
    def test_exact_title_search_then_recipe_information_is_cached(self, request_api):
        request_api.side_effect = [
            {"results": [{"id": 925, "title": "Sup Bayam"}]},
            {"id": 925, "title": "Sup Bayam", "nutrition": {"nutrients": []}},
        ]
        with patch.dict(os.environ, {"SPOONACULAR_API_KEY": "test-key"}):
            first_result = get_spoonacular_recipe(self.recipe)
            second_result = get_spoonacular_recipe(self.recipe)

        self.assertEqual(first_result["status"], "ok")
        self.assertEqual(second_result["status"], "ok")
        self.assertEqual(request_api.call_count, 2)
        self.assertIn(
            "recipes/complexSearch",
            request_api.call_args_list[0].args[0],
        )
        self.assertEqual(
            request_api.call_args_list[1].args[0],
            "recipes/925/information",
        )
