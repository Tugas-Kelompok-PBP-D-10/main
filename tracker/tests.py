from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import override_settings
from tracker.models import CookingLog, CookingStreak, Badge, UserBadge, NutritionTarget
from tracker.services import record_cook
from django.contrib.auth.models import User
from django.db import IntegrityError
from tracker.integrations import (RecipeSnapshot,complete_recipe_cooking,)

import uuid, json

class TrackerTest(TestCase):

    def setUp(self):
        User = get_user_model()

        self.user = User.objects.create_user(
            username="testtracker",
            password="testpass123"
        )

    def test_record_cooking(self):
        record_cook(
            user=self.user,
            recipe_name="Nasi Goreng",
            protein_g=15,
            carbs_g=40,
            fat_g=10,
            calories=310
        )

       
        self.assertEqual(
            CookingLog.objects.filter(
                user=self.user
            ).count(),
            1
        )

    
        streak = CookingStreak.objects.get(
            user=self.user
        )

        self.assertEqual(
            streak.active_streak,
            1
        )


    @override_settings(
        ROOT_URLCONF="tracker.test_urls",
        LOGIN_URL="/accounts/login/"
    )
    def test_tracker_dashboard(self):
        self.client.force_login(self.user)

        response = self.client.get("/tracker/")

        self.assertEqual(response.status_code, 200)

        self.assertTemplateUsed(
            response,
            "tracker/tracker.html"
        )


    @override_settings(ROOT_URLCONF="tracker.test_urls")
    def test_complete_cooking(self):
        self.user.is_staff = True
        self.user.save(update_fields=["is_staff"])

        self.client.force_login(self.user)

       
            
        response = self.client.post(
            reverse("tracker:complete_cooking"),
            {
                "request_id": str(uuid.uuid4())
            }
        )

        self.assertEqual(response.status_code, 200)

        self.assertTrue(response.json()["success"])

       
        self.assertTrue(
            CookingLog.objects.filter(
                user=self.user,
                recipe_name="Test Cooking"
            ).exists()
        )


        streak = CookingStreak.objects.get(user=self.user)
        self.assertEqual(streak.active_streak, 1)

    
    def test_cooking_history_api(self):
        self.client.force_login(self.user)

        record_cook(
            user=self.user,
            recipe_name="Nasi Goreng",
            protein_g=15,
            carbs_g=40,
            fat_g=10,
            calories=310
        )

        response = self.client.get(
            "/tracker/api/history/"
        )

        self.assertEqual(response.status_code, 200)

        data = response.json()

        self.assertTrue(data["success"])
        self.assertEqual(len(data["history"]), 1)

        self.assertEqual(
            data["history"][0]["recipe_name"],
            "Nasi Goreng"
        )


    def test_duplicate_cooking_request(self):
        self.client.force_login(self.user)

        
        self.user.is_staff = True
        self.user.save(update_fields=["is_staff"])

        request_id = str(uuid.uuid4())
        url = reverse("tracker:complete_cooking")

        response1 = self.client.post(
            url, {"request_id": request_id}
        )
        response2 = self.client.post(
            url, {"request_id": request_id}
        )

        self.assertEqual(response1.status_code, 200)
        self.assertEqual(response2.status_code, 200)
        self.assertEqual(
            CookingLog.objects.filter(user=self.user).count(),
            1
        )

    
    def test_different_request_ids_allow_multiple_cooks(self):
   

        self.user.is_staff = True
        self.user.save(update_fields=["is_staff"])
        self.client.force_login(self.user)

        url = reverse("tracker:complete_cooking")

        response1 = self.client.post(
            url,
            {"request_id": str(uuid.uuid4())}
        )

        response2 = self.client.post(
            url,
            {"request_id": str(uuid.uuid4())}
        )

        self.assertEqual(response1.status_code, 200)
        self.assertEqual(response2.status_code, 200)

        self.assertEqual(
            CookingLog.objects.filter(user=self.user).count(),
            2
        )

        streak = CookingStreak.objects.get(user=self.user)

       
        self.assertEqual(streak.active_streak, 1)

    
    def test_request_id_cannot_be_reused_by_another_user(self):
   

        other_user = User.objects.create_user(
            username="other_tracker_user",
            password="testpass12345"
        )

        request_id = uuid.uuid4()

        record_cook(
            user=self.user,
            recipe_name="Resep A",
            request_id=request_id
        )

        with self.assertRaises(ValueError):
            record_cook(
                user=other_user,
                recipe_name="Resep B",
                request_id=request_id
            )

        self.assertEqual(
            CookingLog.objects.filter(
                request_id=request_id
            ).count(),
            1
        )

    
    def test_first_cook_badge_awarded(self):
       
        badge = Badge.objects.create(
            code="FIRST_COOK",
            name="First Cook",
            description="Berhasil memasak pertama kali!",
            kind=Badge.Kind.TOTAL,
            threshold=1,
        )
  
        record_cook(
            user=self.user,
            recipe_name="Nasi Goreng",
            protein_g=15,
            carbs_g=40,
            fat_g=10,
            calories=310,
        )

       
        self.assertTrue(
            UserBadge.objects.filter(
                user=self.user,
                badge=badge,
            ).exists()
        )

       
        self.assertEqual(
            UserBadge.objects.filter(
                user=self.user,
                badge=badge,
            ).count(),
            1
        )

class NutritionTargetTest(TestCase):

    def setUp(self):
        User = get_user_model()

        self.user = User.objects.create_user(
            username="nutrition_test_user",
            password="testpassword123"
        )

    def test_create_nutrition_target(self):
        target = NutritionTarget.objects.create(
            user=self.user,
            protein_g=120,
            carbs_g=150,
            fat_g=70
        )

        self.assertEqual(target.protein_g, 120)
        self.assertEqual(target.carbs_g, 150)
        self.assertEqual(target.fat_g, 70)

    def test_update_nutrition_target(self):
        NutritionTarget.objects.create(
            user=self.user,
            protein_g=120,
            carbs_g=150,
            fat_g=70
        )

        target, created = NutritionTarget.objects.update_or_create(
            user=self.user,
            defaults={
                "protein_g": 140,
                "carbs_g": 180,
                "fat_g": 65
            }
        )

        self.assertFalse(created)
        self.assertEqual(target.protein_g, 140)
        self.assertEqual(target.carbs_g, 180)
        self.assertEqual(target.fat_g, 65)

    def test_one_target_per_user(self):
        NutritionTarget.objects.create(
            user=self.user,
            protein_g=120,
            carbs_g=150,
            fat_g=70
        )

        with self.assertRaises(IntegrityError):
            NutritionTarget.objects.create(
                user=self.user,
                protein_g=100,
                carbs_g=130,
                fat_g=50
            )

class NutritionTargetAPITest(TestCase):

    def setUp(self):
        User = get_user_model()

        self.user = User.objects.create_user(
            username="target_api_user",
            password="testpassword123"
        )

        self.other_user = User.objects.create_user(
            username="other_target_user",
            password="testpassword123"
        )

        self.url = reverse("tracker:nutrition_target_api")
        self.client.force_login(self.user)

    def test_get_target_when_not_set(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["has_target"])
        self.assertIsNone(response.json()["target"])

    def test_save_nutrition_target(self):
        response = self.client.post(
            self.url,
            data=json.dumps({
                "protein_g": 120,
                "carbs_g": 150,
                "fat_g": 70,
            }),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

        target = NutritionTarget.objects.get(user=self.user)

        self.assertEqual(target.protein_g, 120)
        self.assertEqual(target.carbs_g, 150)
        self.assertEqual(target.fat_g, 70)

    def test_update_existing_target(self):
        NutritionTarget.objects.create(
            user=self.user,
            protein_g=120,
            carbs_g=150,
            fat_g=70,
        )

        response = self.client.post(
            self.url,
            data=json.dumps({
                "protein_g": 140,
                "carbs_g": 180,
                "fat_g": 65,
            }),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            NutritionTarget.objects.filter(user=self.user).count(),
            1
        )

        target = NutritionTarget.objects.get(user=self.user)
        self.assertEqual(target.protein_g, 140)

    def test_reject_invalid_target(self):
        response = self.client.post(
            self.url,
            data=json.dumps({
                "protein_g": 0,
                "carbs_g": 150,
                "fat_g": 70,
            }),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(
            NutritionTarget.objects.filter(user=self.user).exists()
        )

    def test_users_have_separate_targets(self):
        NutritionTarget.objects.create(
            user=self.other_user,
            protein_g=200,
            carbs_g=250,
            fat_g=90,
        )

        self.client.post(
            self.url,
            data=json.dumps({
                "protein_g": 120,
                "carbs_g": 150,
                "fat_g": 70,
            }),
            content_type="application/json",
        )

        other_target = NutritionTarget.objects.get(
            user=self.other_user
        )

        self.assertEqual(other_target.protein_g, 200)
        self.assertEqual(other_target.carbs_g, 250)

    def test_login_required(self):
        self.client.logout()

        response = self.client.post(
            self.url,
            data=json.dumps({
                "protein_g": 120,
                "carbs_g": 150,
                "fat_g": 70,
            }),
            content_type="application/json",
        )

        self.assertNotEqual(response.status_code, 200)
        self.assertFalse(NutritionTarget.objects.exists())
