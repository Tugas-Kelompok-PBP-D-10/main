
import json

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

User = get_user_model()


class AuthenticationAPITests(TestCase):

    def setUp(self):
        # Aktifkan pemeriksaan CSRF saat testing
        self.client = Client(enforce_csrf_checks=True)
        self.base_url = "/api-authentication/v1/"

        self.username = "tester"
        self.password = "SandiTest!2026"

        self.user = User.objects.create_user(
            username=self.username,
            email="tester@example.com",
            password=self.password,
        )

        # Ambil cookie CSRF sebelum mengirim POST
        self.client.get(self.base_url + "csrf/")

    def post_json(self, endpoint, data, use_csrf=True):
        headers = {}

        if use_csrf:
            # Token dibaca ulang karena berubah setelah login
            headers["HTTP_X_CSRFTOKEN"] = (
                self.client.cookies["csrftoken"].value
            )

        return self.client.post(
            self.base_url + endpoint,
            data=json.dumps(data),
            content_type="application/json",
            **headers
        )

    def test_csrf(self):
        response = self.client.get(
            self.base_url + "csrf/"
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("csrf_token", response.json())
        self.assertIn("csrftoken", self.client.cookies)

    def test_register_success(self):
        response = self.post_json("register/", {
            "username": "userbaru",
            "email": "userbaru@example.com",
            "password1": "PasswordBaru!2026",
            "password2": "PasswordBaru!2026",
        })

        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.json()["success"])
        self.assertTrue(
            User.objects.filter(username="userbaru").exists()
        )

    def test_register_invalid(self):
        response = self.post_json("register/", {
            "username": "userbaru",
            "email": "userbaru@example.com",
            "password1": "PasswordBaru!2026",
            "password2": "PasswordSalah!2026",
        })

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()["success"])

    def test_register_duplicate_email(self):
        response = self.post_json("register/", {
            "username": "userbaru",
            "email": "tester@example.com",
            "password1": "PasswordBaru!2026",
            "password2": "PasswordBaru!2026",
        })

        self.assertEqual(response.status_code, 400)

    def test_login_profile_logout(self):
        # Login
        response = self.post_json("login/", {
            "username": self.username,
            "password": self.password,
        })

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

        # Ambil profil setelah login
        response = self.client.get(
            self.base_url + "profile/"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["username"],
            self.username
        )

        # Logout
        response = self.post_json("logout/", {})

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

        # Profil tidak boleh diakses setelah logout
        response = self.client.get(
            self.base_url + "profile/"
        )

        self.assertEqual(response.status_code, 403)

    def test_login_invalid(self):
        response = self.post_json("login/", {
            "username": self.username,
            "password": "passwordsalah",
        })

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()["success"])

    def test_profile_without_login(self):
        response = self.client.get(
            self.base_url + "profile/"
        )

        self.assertEqual(response.status_code, 403)

    def test_login_without_csrf(self):
        response = self.post_json(
            "login/",
            {
                "username": self.username,
                "password": self.password,
            },
            use_csrf=False
        )

        self.assertEqual(response.status_code, 403)
