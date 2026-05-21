from unittest.mock import patch, MagicMock
from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from rest_framework.authtoken.models import Token
from apps.chat.models.conversation import Conversation, Message


class TestSendMessage(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="msguser", password="pass")
        self.token, _ = Token.objects.get_or_create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")
        self.conversation = Conversation.objects.create(
            user=self.user,
            title="Test",
            persona="tech_oracle",
        )

    @patch("apps.chat.services.send_message.get_persona")
    @patch("apps.chat.services.send_message.ask_groq")
    def test_send_message_case_1(self, mock_ask_groq, mock_get_persona):
        """
        Case: Send a message with valid conversation and content
        Expected: Success — assistant message returned
        """
        mock_get_persona.return_value = None
        mock_ask_groq.return_value = {
            "content": "Hello! I am Oracle Brain.",
            "model": "deepseek-r1-distill-llama-70b",
            "tokens_in": 100,
            "tokens_out": 20,
            "cost": 0.0001,
        }

        data = {"content": "Hello Oracle!"}
        response = self.client.post(
            f"/api/v1/chat/conversations/{self.conversation.id}/messages/send/",
            data,
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["role"], "assistant")
        self.assertEqual(response.data["content"], "Hello! I am Oracle Brain.")
        self.assertEqual(response.data["model_used"], "deepseek-r1-distill-llama-70b")
        self.assertIsNotNone(response.data["id"])

        messages = Message.objects.filter(conversation=self.conversation)
        self.assertEqual(messages.count(), 2)
        self.assertEqual(messages.filter(role="user").first().content, "Hello Oracle!")

    @patch("apps.chat.services.send_message.ask_groq")
    def test_send_message_case_2(self, mock_ask_groq):
        """
        Case: Send empty content
        Expected: Failure — 400 validation error
        """
        data = {"content": ""}
        response = self.client.post(
            f"/api/v1/chat/conversations/{self.conversation.id}/messages/send/",
            data,
        )
        self.assertEqual(response.status_code, 400, response.data)
        mock_ask_groq.assert_not_called()

    @patch("apps.chat.services.send_message.get_persona")
    @patch("apps.chat.services.send_message.ask_groq")
    def test_send_message_case_3(self, mock_ask_groq, mock_get_persona):
        """
        Case: Send message to a conversation belonging to another user
        Expected: Failure — 404 Not Found
        """
        other_user = User.objects.create_user(username="other2", password="pass")
        other_conv = Conversation.objects.create(user=other_user, title="Other")
        mock_get_persona.return_value = None
        data = {"content": "Hack attempt"}
        response = self.client.post(
            f"/api/v1/chat/conversations/{other_conv.id}/messages/send/",
            data,
        )
        self.assertEqual(response.status_code, 404, response.data)
        mock_ask_groq.assert_not_called()
