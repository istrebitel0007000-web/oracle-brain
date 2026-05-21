from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from rest_framework.authtoken.models import Token
from apps.notes.models.note import Note


class TestCreateNote(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="noteuser", password="pass")
        self.token, _ = Token.objects.get_or_create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")

    def test_create_note_case_1(self):
        """
        Case: Create note with valid text
        Expected: Success — 201, note returned
        """
        data = {"text": "Remember to review the PR tomorrow"}
        response = self.client.post("/api/v1/notes/create/", data)
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["text"], "Remember to review the PR tomorrow")
        self.assertFalse(response.data["is_pinned"])

        note = Note.objects.filter(id=response.data["id"]).first()
        self.assertIsNotNone(note)
        self.assertEqual(note.user_id, self.user.id)

    def test_create_note_case_2(self):
        """
        Case: Create note with empty text
        Expected: Failure — 400 validation error
        """
        data = {"text": ""}
        response = self.client.post("/api/v1/notes/create/", data)
        self.assertEqual(response.status_code, 400, response.data)


class TestPinNote(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="pinnoteuser", password="pass")
        self.token, _ = Token.objects.get_or_create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")
        self.note = Note.objects.create(user=self.user, text="Pin me")

    def test_pin_note_case_1(self):
        """
        Case: Pin an unpinned note
        Expected: Success — is_pinned becomes True
        """
        response = self.client.patch(f"/api/v1/notes/{self.note.id}/pin-toggle/")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertTrue(response.data["is_pinned"])

        self.note.refresh_from_db()
        self.assertTrue(self.note.is_pinned)

    def test_pin_note_case_2(self):
        """
        Case: Toggle pin on already-pinned note
        Expected: Success — is_pinned becomes False
        """
        self.note.is_pinned = True
        self.note.save()
        response = self.client.patch(f"/api/v1/notes/{self.note.id}/pin-toggle/")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertFalse(response.data["is_pinned"])
