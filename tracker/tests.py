
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import override_settings





from tracker.models import CookingLog, CookingStreak
from tracker.services import record_cook



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
            reverse("tracker:complete_cooking")
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



