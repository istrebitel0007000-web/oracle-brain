from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from rest_framework.authtoken.models import Token


class TestRegisterUser(APITestCase):
    def test_register_user_case_1(self):
        """
        Case: Register with valid credentials
        Expected: Success — user created, token returned
        """
        data = {
            "username": "newuser",
            "password": "securepass123",
            "email": "newuser@example.com",
        }
        response = self.client.post("/api/v1/auth/register/", data)
        self.assertEqual(response.status_code, 201, response.data)
        self.assertIn("token", response.data)
        self.assertIn("user_id", response.data)
        self.assertEqual(response.data["username"], "newuser")

        user = User.objects.filter(username="newuser").first()
        self.assertIsNotNone(user)
        self.assertEqual(user.email, "newuser@example.com")
        self.assertTrue(Token.objects.filter(user=user).exists())

    def test_register_user_case_2(self):
        """
        Case: Register with duplicate username
        Expected: Failure — 400 error
        """
        User.objects.create_user(username="duplicate", password="pass123")
        data = {
            "username": "duplicate",
            "password": "anotherpass",
        }
        response = self.client.post("/api/v1/auth/register/", data)
        self.assertEqual(response.status_code, 400, response.data)

    def test_register_user_case_3(self):
        """
        Case: Register with password too short (< 6 chars)
        Expected: Failure — 400 validation error
        """
        data = {
            "username": "shortpass",
            "password": "abc",
        }
        response = self.client.post("/api/v1/auth/register/", data)
        self.assertEqual(response.status_code, 400, response.data)
        self.assertIn("password", response.data)


class TestLoginUser(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="loginuser",
            password="correctpass",
        )

    def test_login_user_case_1(self):
        """
        Case: Login with correct credentials
        Expected: Success — token returned
        """
        data = {"username": "loginuser", "password": "correctpass"}
        response = self.client.post("/api/v1/auth/login/", data)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertIn("token", response.data)
        self.assertEqual(response.data["username"], "loginuser")

    def test_login_user_case_2(self):
        """
        Case: Login with wrong password
        Expected: Failure — 401 Unauthorized
        """
        data = {"username": "loginuser", "password": "wrongpass"}
        response = self.client.post("/api/v1/auth/login/", data)
        self.assertEqual(response.status_code, 401, response.data)
        self.assertNotIn("token", response.data)
