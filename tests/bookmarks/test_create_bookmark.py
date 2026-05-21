from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from rest_framework.authtoken.models import Token
from apps.bookmarks.models.bookmark import Bookmark


class TestCreateBookmark(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="bookmarkuser", password="pass")
        self.token, _ = Token.objects.get_or_create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")

    def test_create_bookmark_case_1(self):
        """
        Case: Create bookmark with valid label and content
        Expected: Success — 201, bookmark returned
        """
        data = {
            "label": "Useful Django tip",
            "content": "Use select_related() to avoid N+1 queries in Django ORM.",
        }
        response = self.client.post("/api/v1/bookmarks/create/", data)
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["label"], "Useful Django tip")
        self.assertIsNotNone(response.data["id"])

        bookmark = Bookmark.objects.filter(id=response.data["id"]).first()
        self.assertIsNotNone(bookmark)
        self.assertEqual(bookmark.user_id, self.user.id)
        self.assertEqual(bookmark.content, "Use select_related() to avoid N+1 queries in Django ORM.")

    def test_create_bookmark_case_2(self):
        """
        Case: Create bookmark with missing label
        Expected: Failure — 400 validation error
        """
        data = {"content": "Some content but no label"}
        response = self.client.post("/api/v1/bookmarks/create/", data)
        self.assertEqual(response.status_code, 400, response.data)
        self.assertIn("label", response.data)


class TestDeleteBookmark(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="delbookmark", password="pass")
        self.token, _ = Token.objects.get_or_create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")
        self.bookmark = Bookmark.objects.create(
            user=self.user,
            label="To Delete",
            content="Delete me",
        )

    def test_delete_bookmark_case_1(self):
        """
        Case: Delete owned bookmark
        Expected: Success — 204, bookmark gone
        """
        response = self.client.delete(f"/api/v1/bookmarks/{self.bookmark.id}/delete/")
        self.assertEqual(response.status_code, 204, response.data)
        self.assertFalse(Bookmark.objects.filter(id=self.bookmark.id).exists())

    def test_delete_bookmark_case_2(self):
        """
        Case: Delete bookmark owned by another user
        Expected: Failure — 404 Not Found
        """
        other = User.objects.create_user(username="otherb", password="pass")
        other_bookmark = Bookmark.objects.create(
            user=other, label="Other", content="Not yours"
        )
        response = self.client.delete(f"/api/v1/bookmarks/{other_bookmark.id}/delete/")
        self.assertEqual(response.status_code, 404, response.data)
        self.assertTrue(Bookmark.objects.filter(id=other_bookmark.id).exists())
