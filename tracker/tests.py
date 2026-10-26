
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import override_settings
from tracker.models import CookingLog, CookingStreak, Badge, UserBadge
from tracker.services import record_cook
from django.contrib.auth.models import User

from tracker.integrations import (
    RecipeSnapshot,
    complete_recipe_cooking,
)


import uuid



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


    def test_recipe_integration_records_cooking(self):
        recipe = RecipeSnapshot(
            name="Sup Ayam",
            protein_g=25,
            carbs_g=20,
            fat_g=8,
            calories=260,
        )

        complete_recipe_cooking(
            user=self.user,
            recipe=recipe,
            request_id=uuid.uuid4(),
        )

        log = CookingLog.objects.get(user=self.user)

        self.assertEqual(log.recipe_name, "Sup Ayam")
        self.assertEqual(log.protein_g, 25)
        self.assertEqual(log.carbs_g, 20)
        self.assertEqual(log.fat_g, 8)
        self.assertEqual(log.calories, 260)

        streak = CookingStreak.objects.get(user=self.user)

        self.assertEqual(streak.active_streak, 1)







