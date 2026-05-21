from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from rest_framework.authtoken.models import Token
from apps.rag.models.rag_chunk import RagChunk


class TestAddRagChunk(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="raguser", password="pass")
        self.token, _ = Token.objects.get_or_create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")

    def test_add_rag_chunk_case_1(self):
        """
        Case: Add a valid text chunk to RAG
        Expected: Success — 201, chunk saved
        """
        data = {
            "text": "Django REST Framework is a powerful toolkit for building Web APIs.",
            "source": "docs.djangoproject.com",
        }
        response = self.client.post("/api/v1/rag/create/", data)
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["source"], "docs.djangoproject.com")
        self.assertIsNotNone(response.data["id"])

        chunk = RagChunk.objects.filter(id=response.data["id"]).first()
        self.assertIsNotNone(chunk)
        self.assertEqual(chunk.user_id, self.user.id)
        self.assertIn("django", chunk.tfidf_tokens)

    def test_add_rag_chunk_case_2(self):
        """
        Case: Add chunk with empty text
        Expected: Failure — 400 validation error
        """
        data = {"text": "", "source": "test"}
        response = self.client.post("/api/v1/rag/create/", data)
        self.assertEqual(response.status_code, 400, response.data)


class TestSearchRagChunks(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="searchrag", password="pass")
        self.token, _ = Token.objects.get_or_create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")
        RagChunk.objects.create(
            user=self.user,
            text="Python is great for data science and machine learning",
            source="test",
            tfidf_tokens=["python", "great", "data", "science", "machine", "learning"],
        )
        RagChunk.objects.create(
            user=self.user,
            text="Django is a web framework for Python",
            source="test",
            tfidf_tokens=["django", "web", "framework", "python"],
        )

    def test_search_rag_chunks_case_1(self):
        """
        Case: Search with relevant query
        Expected: Success — matching chunks returned
        """
        query_params = {"query": "python data science"}
        response = self.client.get("/api/v1/rag/search/", query_params)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertGreater(len(response.data), 0)
        self.assertIn("python", response.data[0]["text"].lower())

    def test_search_rag_chunks_case_2(self):
        """
        Case: Search with no matching query
        Expected: Success — empty list returned
        """
        query_params = {"query": "xyz quantum blockchain nft"}
        response = self.client.get("/api/v1/rag/search/", query_params)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(len(response.data), 0)
