from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from rest_framework.authtoken.models import Token
from apps.costs.models.cost_record import CostRecord
from django.utils import timezone


class TestListCosts(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="costuser", password="pass")
        self.token, _ = Token.objects.get_or_create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")
        today = timezone.now().date()
        CostRecord.objects.create(
            user=self.user,
            date=today,
            model="deepseek-r1-distill-llama-70b",
            persona="tech_oracle",
            tokens_in=500,
            tokens_out=100,
            cost_usd=0.000450,
        )
        CostRecord.objects.create(
            user=self.user,
            date=today,
            model="llama-3.3-70b-versatile",
            persona="mentor",
            tokens_in=300,
            tokens_out=80,
            cost_usd=0.000250,
        )

    def test_list_costs_case_1(self):
        """
        Case: List all cost records for authenticated user
        Expected: Success — all user records returned
        """
        response = self.client.get("/api/v1/costs/list/")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(len(response.data), 2)

    def test_list_costs_case_2(self):
        """
        Case: List costs without authentication
        Expected: Failure — 401 Unauthorized
        """
        self.client.credentials()
        response = self.client.get("/api/v1/costs/list/")
        self.assertEqual(response.status_code, 401, response.data)


class TestCostSummary(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="summaryuser", password="pass")
        self.token, _ = Token.objects.get_or_create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")
        today = timezone.now().date()
        CostRecord.objects.create(
            user=self.user,
            date=today,
            model="deepseek-r1-distill-llama-70b",
            persona="tech_oracle",
            tokens_in=1000,
            tokens_out=200,
            cost_usd=0.001000,
        )
        CostRecord.objects.create(
            user=self.user,
            date=today,
            model="llama-3.3-70b-versatile",
            persona="mentor",
            tokens_in=500,
            tokens_out=100,
            cost_usd=0.000500,
        )

    def test_cost_summary_case_1(self):
        """
        Case: Get cost summary for authenticated user
        Expected: Success — totals aggregated correctly
        """
        response = self.client.get("/api/v1/costs/summary/")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["total_calls"], 2)
        self.assertEqual(response.data["total_tokens_in"], 1500)
        self.assertEqual(response.data["total_tokens_out"], 300)
        self.assertAlmostEqual(response.data["total_cost_usd"], 0.001500, places=5)

    def test_cost_summary_case_2(self):
        """
        Case: Get cost summary for user with no records
        Expected: Success — all zeros
        """
        empty_user = User.objects.create_user(username="emptyuser", password="pass")
        token, _ = Token.objects.get_or_create(user=empty_user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        response = self.client.get("/api/v1/costs/summary/")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["total_calls"], 0)
        self.assertEqual(response.data["total_cost_usd"], 0.0)
