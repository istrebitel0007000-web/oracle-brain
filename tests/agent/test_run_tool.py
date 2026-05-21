from unittest.mock import patch, MagicMock
from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from rest_framework.authtoken.models import Token
from apps.agent.models.agent_tool_call import AgentToolCall


class TestRunTool(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="agentuser", password="pass")
        self.token, _ = Token.objects.get_or_create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")

    def test_run_tool_calculator_case_1(self):
        """
        Case: Run calculator tool with valid expression
        Expected: Success — correct result returned, call logged
        """
        data = {
            "tool_name": "calculator",
            "tool_input": {"expression": "2 ** 10"},
        }
        response = self.client.post("/api/v1/agent/tools/run/", data, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["tool_name"], "calculator")
        self.assertEqual(response.data["output"], "1024")

        call = AgentToolCall.objects.filter(
            user=self.user, tool_name="calculator"
        ).first()
        self.assertIsNotNone(call)
        self.assertTrue(call.success)

    def test_run_tool_calculator_case_2(self):
        """
        Case: Run calculator with invalid expression
        Expected: Error message returned, call logged as failed
        """
        data = {
            "tool_name": "calculator",
            "tool_input": {"expression": "import os; os.system('rm -rf /')"},
        }
        response = self.client.post("/api/v1/agent/tools/run/", data, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertIn("Tool Error", response.data["output"])

        call = AgentToolCall.objects.filter(
            user=self.user, tool_name="calculator"
        ).last()
        self.assertIsNotNone(call)
        self.assertFalse(call.success)

    def test_run_tool_case_3(self):
        """
        Case: Run unknown tool
        Expected: Error message — tool not found
        """
        data = {
            "tool_name": "nonexistent_tool",
            "tool_input": {},
        }
        response = self.client.post("/api/v1/agent/tools/run/", data, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertIn("Unknown tool", response.data["output"])

    @patch("urllib.request.urlopen")
    def test_run_tool_web_fetch_case_1(self, mock_urlopen):
        """
        Case: Run web_fetch with valid URL (external call mocked)
        Expected: Success — mocked content returned
        """
        from unittest.mock import MagicMock
        mock_response = MagicMock()
        mock_response.read.return_value = b"Mocked page content from example.com"
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        data = {
            "tool_name": "web_fetch",
            "tool_input": {"url": "https://example.com"},
        }
        response = self.client.post("/api/v1/agent/tools/run/", data, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertIn("Mocked page content", response.data["output"])


class TestListTools(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="listtoolsuser", password="pass")
        self.token, _ = Token.objects.get_or_create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")

    def test_list_tools_case_1(self):
        """
        Case: List all available agent tools
        Expected: Success — tools list returned with name and description
        """
        response = self.client.get("/api/v1/agent/tools/list/")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertGreater(len(response.data), 0)

        tool_names = [t["name"] for t in response.data]
        self.assertIn("calculator", tool_names)
        self.assertIn("web_fetch", tool_names)
        self.assertIn("get_time", tool_names)

    def test_list_tools_case_2(self):
        """
        Case: List tools without authentication
        Expected: Failure — 401 Unauthorized
        """
        self.client.credentials()
        response = self.client.get("/api/v1/agent/tools/list/")
        self.assertEqual(response.status_code, 401, response.data)
