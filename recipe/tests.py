import json
import os
import base64
import tempfile
import uuid
from io import BytesIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image
from voting.models import Bookmark

from .forms import RecipeAdminForm
from .models import Recipe, RecipeCookingEvent, RecipeInteraction
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

    def test_empty_database_shows_friendly_empty_state(self):
        Recipe.objects.all().delete()

        response = self.client.get(reverse("recipe:home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Belum ada resep yang tersedia.")

    def test_authenticated_recipe_page_preserves_existing_voting_controls(self):
        user = get_user_model().objects.create_user(
            username="recipe-page-user",
            password="test-password",
        )
        self.client.force_login(user)

        response = self.client.get(reverse("recipe:home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'class="vote__btn')
        self.assertNotContains(response, "Vote dan simpan belum tersedia")

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

    def test_local_recipe_does_not_search_for_an_unrelated_api_recipe(self):
        local_recipe = Recipe.objects.create(
            title="Sup Sayur Lokal",
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

    def test_same_origin_media_image_is_returned_for_card_and_detail(self):
        recipe = Recipe.objects.create(
            title="Resep lokal dengan foto",
            image_url="/media/recipes/lokal.jpg",
        )
        with patch(
            "recipe.services.get_spoonacular_recipe",
            return_value={"status": "not_configured", "message": "", "data": None},
        ):
            detail = self.client.get(reverse("recipe:api_detail", args=(recipe.pk,)))
        page = self.client.get(reverse("recipe:home"))

        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.json()["recipe"]["image"], "/media/recipes/lokal.jpg")
        self.assertContains(page, "/media/recipes/lokal.jpg")

    def test_unpublished_recipe_is_not_public(self):
        draft = Recipe.objects.create(title="Resep draf", is_published=False)

        page = self.client.get(reverse("recipe:home"))
        detail = self.client.get(reverse("recipe:api_detail", args=(draft.pk,)))

        self.assertEqual(page.status_code, 200)
        self.assertNotContains(page, "Resep draf")
        self.assertEqual(detail.status_code, 404)

    def test_archived_recipe_stays_available_to_its_bookmarker_only(self):
        archived = Recipe.objects.create(
            title="Resep arsip",
            source_type="local",
            is_published=False,
        )
        owner = get_user_model().objects.create_user(username="archived-bookmarker")
        other_user = get_user_model().objects.create_user(username="not-a-bookmarker")
        Bookmark.objects.create(user=owner, recipe=archived)
        detail_url = reverse("recipe:api_detail", args=(archived.pk,))
        interaction_url = reverse("recipe:api_interactions", args=(archived.pk,))
        view_url = reverse("recipe:api_record_view", args=(archived.pk,))
        complete_url = reverse("recipe:api_complete", args=(archived.pk,))

        self.assertEqual(self.client.get(detail_url).status_code, 404)
        self.client.force_login(other_user)
        self.assertEqual(self.client.get(detail_url).status_code, 404)

        self.client.force_login(owner)
        self.assertEqual(self.client.get(detail_url).status_code, 200)
        self.assertEqual(self.client.get(interaction_url).status_code, 200)
        self.assertEqual(self.client.post(view_url).status_code, 200)
        cooked = self.client.post(
            complete_url,
            data=json.dumps({"confirmed": True, "request_id": str(uuid.uuid4())}),
            content_type="application/json",
        )
        self.assertEqual(cooked.status_code, 200)
        self.assertEqual(cooked.json()["cooking_count"], 1)

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


class RecipeSubmissionTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="menu-contributor",
            password="test-password",
        )
        self.url = reverse("recipe:api_submit")
        self.submission_id = str(uuid.uuid4())
        self.payload = {
            "submission_id": self.submission_id,
            "title": "Sate Ayam Rumahan",
            "description": "Sate ayam dengan bumbu kacang.",
            "servings": "4",
            "ingredients": json.dumps([
                {"name": "Daging ayam", "amount": 500, "unit": "gram"},
                {"name": "Kecap manis", "amount": 2.5, "unit": "sdm"},
            ]),
            "instructions": "Potong ayam.\nBakar hingga matang.",
        }

    def test_anonymous_user_cannot_submit_recipe(self):
        response = self.client.post(self.url, self.payload)

        self.assertEqual(response.status_code, 401)
        self.assertEqual(Recipe.objects.count(), 0)

    def test_authenticated_submission_saves_recipe_and_steps_for_recipe_grid(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url, self.payload)
        page = self.client.get(reverse("recipe:home"))

        self.assertEqual(response.status_code, 201)
        recipe = Recipe.objects.get(pk=response.json()["recipe"]["id"])
        self.assertEqual(recipe.author, self.user)
        self.assertEqual(recipe.source_type, "local")
        self.assertTrue(recipe.is_published)
        self.assertEqual(recipe.servings, 4)
        self.assertEqual(
            recipe.ingredients,
            [
                {"name": "Daging ayam", "amount": 500, "unit": "gram"},
                {"name": "Kecap manis", "amount": 2.5, "unit": "sdm"},
            ],
        )
        self.assertEqual(recipe.instructions.splitlines(), ["Potong ayam.", "Bakar hingga matang."])
        self.assertIsNone(recipe.calories)
        self.assertEqual(recipe.nutrition_basis, "unknown")
        self.assertContains(page, "Sate Ayam Rumahan")

    def test_submission_id_makes_retries_idempotent_and_private_to_owner(self):
        self.client.force_login(self.user)
        first = self.client.post(self.url, self.payload)
        retry = self.client.post(self.url, self.payload)

        self.assertEqual(first.status_code, 201)
        self.assertEqual(retry.status_code, 200)
        self.assertTrue(retry.json()["duplicate"])
        self.assertEqual(Recipe.objects.count(), 1)

        other_user = get_user_model().objects.create_user(username="another-contributor")
        self.client.force_login(other_user)
        conflict = self.client.post(self.url, self.payload)
        self.assertEqual(conflict.status_code, 409)
        self.assertEqual(Recipe.objects.count(), 1)

    def test_invalid_recipe_is_rejected_without_creating_a_row(self):
        self.client.force_login(self.user)
        invalid = {
            **self.payload,
            "ingredients": json.dumps([{"name": "Garam", "amount": 0, "unit": "gram"}]),
        }

        response = self.client.post(self.url, invalid)

        self.assertEqual(response.status_code, 400)
        self.assertIn("ingredients", response.json()["errors"])
        self.assertEqual(Recipe.objects.count(), 0)

    def test_uploaded_image_is_validated_and_attached_to_the_recipe(self):
        image_buffer = BytesIO()
        Image.new("RGB", (2, 2), (50, 140, 100)).save(image_buffer, format="PNG")
        png_data = image_buffer.getvalue()
        self.client.force_login(self.user)
        with tempfile.TemporaryDirectory(dir=os.getcwd()) as media_dir:
            with override_settings(MEDIA_ROOT=media_dir):
                response = self.client.post(
                    self.url,
                    {**self.payload, "image": SimpleUploadedFile(
                        "sate.png", png_data, content_type="image/png"
                    )},
                )
                self.assertEqual(response.status_code, 201)
                recipe = Recipe.objects.get(pk=response.json()["recipe"]["id"])
                self.assertTrue(os.path.isfile(recipe.image.path))
                self.assertEqual(recipe.image.name, "recipes/sate.png")
                recipe.image.delete(save=False)

    def test_admin_form_uses_same_recipe_table_and_preserves_unit_fields(self):
        form = RecipeAdminForm(data={
            "title": "Sup Admin",
            "source_type": "local",
            "source_name": "Dapur Admin",
            "is_published": "on",
            "nutrition_basis": "unknown",
            "ingredients": json.dumps([
                {"name": "Kentang", "amount": 300, "unit": "gram"},
            ]),
            "instructions": "Kupas kentang.\nRebus sampai empuk.",
            "additional_nutrition": "{}",
        })

        self.assertTrue(form.is_valid(), form.errors)
        recipe = form.save()
        saved = Recipe.objects.get(pk=recipe.pk)
        self.assertEqual(saved.ingredients[0]["unit"], "gram")
        self.assertEqual(saved.instructions.splitlines(), ["Kupas kentang.", "Rebus sampai empuk."])


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
            title="Sup Sayur",
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
        first_request_id = str(uuid.uuid4())
        second_request_id = str(uuid.uuid4())

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
            data=json.dumps({"confirmed": True, "request_id": first_request_id}),
            content_type="application/json",
        )
        first_completed_at = first_response.json()["completed_at"]
        second_response = self.client.post(
            self.complete_url,
            data=json.dumps({"confirmed": True, "request_id": first_request_id}),
            content_type="application/json",
        )
        third_response = self.client.post(
            self.complete_url,
            data=json.dumps({"confirmed": True, "request_id": second_request_id}),
            content_type="application/json",
        )

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(second_response.status_code, 200)
        self.assertEqual(third_response.status_code, 200)
        self.assertTrue(second_response.json()["viewed"])
        self.assertTrue(second_response.json()["completed"])
        self.assertEqual(second_response.json()["completed_at"], first_completed_at)
        self.assertEqual(second_response.json()["cooking_count"], 1)
        self.assertEqual(third_response.json()["cooking_count"], 2)
        self.assertFalse(third_response.json()["tracker_recorded"])
        self.assertEqual(RecipeInteraction.objects.count(), 1)
        self.assertEqual(RecipeCookingEvent.objects.filter(user=self.user, recipe=self.recipe).count(), 2)

    def test_cooking_history_is_separate_for_each_user(self):
        other_user = get_user_model().objects.create_user(username="second-recipe-user")
        request_id = str(uuid.uuid4())

        self.client.force_login(self.user)
        first = self.client.post(
            self.complete_url,
            data=json.dumps({"confirmed": True, "request_id": request_id}),
            content_type="application/json",
        )
        self.client.force_login(other_user)
        second = self.client.post(
            self.complete_url,
            data=json.dumps({"confirmed": True, "request_id": str(uuid.uuid4())}),
            content_type="application/json",
        )

        self.assertEqual(first.json()["cooking_count"], 1)
        self.assertEqual(second.json()["cooking_count"], 1)
        self.assertEqual(RecipeCookingEvent.objects.filter(recipe=self.recipe).count(), 2)
        self.assertEqual(RecipeCookingEvent.objects.filter(user=self.user, recipe=self.recipe).count(), 1)
        self.assertEqual(RecipeCookingEvent.objects.filter(user=other_user, recipe=self.recipe).count(), 1)

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
