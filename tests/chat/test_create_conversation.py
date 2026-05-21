from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from rest_framework.authtoken.models import Token
from apps.chat.models.conversation import Conversation


class TestCreateConversation(APITestCase):
    fixtures = [
        "tests/chat/fixtures/test_create_conversation/user.json",
    ]

    def setUp(self):
        self.user = User.objects.get(pk=1)
        self.token, _ = Token.objects.get_or_create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")

    def test_create_conversation_case_1(self):
        """
        Case: Create conversation with valid data
        Expected: Success — 201, conversation returned
        """
        data = {
            "title": "My Test Chat",
            "model": "deepseek-r1-distill-llama-70b",
            "persona": "tech_oracle",
        }
        response = self.client.post("/api/v1/chat/conversations/create/", data)
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["title"], "My Test Chat")
        self.assertEqual(response.data["persona"], "tech_oracle")
        self.assertIsNotNone(response.data["id"])

        conversation = Conversation.objects.filter(id=response.data["id"]).first()
        self.assertIsNotNone(conversation)
        self.assertEqual(conversation.user_id, self.user.id)

    def test_create_conversation_case_2(self):
        """
        Case: Create conversation without auth token
        Expected: Failure — 401 Unauthorized
        """
        self.client.credentials()
        data = {"title": "Unauthorized Chat"}
        response = self.client.post("/api/v1/chat/conversations/create/", data)
        self.assertEqual(response.status_code, 401, response.data)

    def test_create_conversation_case_3(self):
        """
        Case: Create conversation with defaults (no body)
        Expected: Success — defaults applied
        """
        response = self.client.post("/api/v1/chat/conversations/create/", {})
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["title"], "New Conversation")
        self.assertEqual(response.data["persona"], "tech_oracle")
        self.assertEqual(response.data["temperature"], 0.7)


class TestDeleteConversation(APITestCase):
    fixtures = [
        "tests/chat/fixtures/test_create_conversation/user.json",
    ]

    def setUp(self):
        self.user = User.objects.get(pk=1)
        self.token, _ = Token.objects.get_or_create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")
        self.conversation = Conversation.objects.create(
            user=self.user,
            title="To Delete",
        )

    def test_delete_conversation_case_1(self):
        """
        Case: Delete owned conversation
        Expected: Success — 204, conversation gone
        """
        response = self.client.delete(
            f"/api/v1/chat/conversations/{self.conversation.id}/delete/"
        )
        self.assertEqual(response.status_code, 204, response.data)
        self.assertFalse(
            Conversation.objects.filter(id=self.conversation.id).exists()
        )

    def test_delete_conversation_case_2(self):
        """
        Case: Delete conversation belonging to another user
        Expected: Failure — 404 Not Found
        """
        other_user = User.objects.create_user(username="other", password="pass")
        other_conv = Conversation.objects.create(user=other_user, title="Other's Chat")
        response = self.client.delete(
            f"/api/v1/chat/conversations/{other_conv.id}/delete/"
        )
        self.assertEqual(response.status_code, 404, response.data)
        self.assertTrue(Conversation.objects.filter(id=other_conv.id).exists())
