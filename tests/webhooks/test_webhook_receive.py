from unittest.mock import patch
from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from rest_framework.authtoken.models import Token
from apps.webhooks.models.webhook_call import WebhookCall
import apps.webhooks.views.webhooks as webhooks_module


class TestWebhookReceive(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="webhookuser", password="pass")
        self.token, _ = Token.objects.get_or_create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")
        self.valid_token = webhooks_module.generate_webhook_token(user_id=self.user.id)

    @patch("apps.webhooks.views.webhooks.ask_groq")
    def test_webhook_receive_case_1(self, mock_ask_groq):
        """
        Case: Valid token and prompt sent to webhook
        Expected: Success — 200, AI response returned, call logged
        """
        mock_ask_groq.return_value = {
            "content": "The answer is 42.",
            "model": "deepseek-r1-distill-llama-70b",
            "tokens_in": 10,
            "tokens_out": 5,
            "cost": 0.0001,
        }

        data = {
            "token": self.valid_token,
            "prompt": "What is the answer to life?",
        }
        response = self.client.post("/api/v1/webhooks/receive/", data)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["response"], "The answer is 42.")

        call = WebhookCall.objects.filter(token=self.valid_token).first()
        self.assertIsNotNone(call)
        self.assertTrue(call.success)
        self.assertEqual(call.response, "The answer is 42.")

    def test_webhook_receive_case_2(self):
        """
        Case: Invalid/unknown token sent
        Expected: Failure — 401, call logged as failed
        """
        data = {
            "token": "invalid-token-xyz-000",
            "prompt": "Should not work",
        }
        response = self.client.post("/api/v1/webhooks/receive/", data)
        self.assertEqual(response.status_code, 401, response.data)

        call = WebhookCall.objects.filter(token="invalid-token-xyz-000").first()
        self.assertIsNotNone(call)
        self.assertFalse(call.success)


class TestGenerateWebhookToken(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="tokengen", password="pass")
        self.token, _ = Token.objects.get_or_create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")

    def test_generate_webhook_token_case_1(self):
        """
        Case: Generate new webhook token while authenticated
        Expected: Success — 201, token returned
        """
        response = self.client.post("/api/v1/webhooks/token/create/")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertIn("token", response.data)
        self.assertGreater(len(response.data["token"]), 20)

    def test_generate_webhook_token_case_2(self):
        """
        Case: Generate webhook token without authentication
        Expected: Failure — 401 Unauthorized
        """
        self.client.credentials()
        response = self.client.post("/api/v1/webhooks/token/create/")
        self.assertEqual(response.status_code, 401, response.data)
