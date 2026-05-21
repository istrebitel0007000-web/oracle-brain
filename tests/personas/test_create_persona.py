from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from rest_framework.authtoken.models import Token
from apps.personas.models.persona import Persona


class TestCreatePersona(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="personauser", password="pass")
        self.token, _ = Token.objects.get_or_create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")

    def test_create_persona_case_1(self):
        """
        Case: Create custom persona with valid data
        Expected: Success — 201, persona returned with custom type
        """
        data = {
            "key": "pirate",
            "name": "Pirate Oracle",
            "instruction": "Answer everything like a pirate. ARRR!",
            "temperature": 0.9,
            "length": "short",
        }
        response = self.client.post("/api/v1/personas/create/", data)
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["key"], "pirate")
        self.assertEqual(response.data["name"], "Pirate Oracle")
        self.assertEqual(response.data["persona_type"], "custom")
        self.assertIsNotNone(response.data["id"])

        persona = Persona.objects.filter(key="pirate").first()
        self.assertIsNotNone(persona)
        self.assertEqual(persona.persona_type, Persona.PersonaType.CUSTOM)

    def test_create_persona_case_2(self):
        """
        Case: Create persona with duplicate key
        Expected: Failure — 400 error
        """
        Persona.objects.create(
            key="duplicate-key",
            name="Existing",
            instruction="Already here",
        )
        data = {
            "key": "duplicate-key",
            "name": "New Duplicate",
            "instruction": "This should fail",
        }
        response = self.client.post("/api/v1/personas/create/", data)
        self.assertEqual(response.status_code, 400, response.data)

    def test_create_persona_case_3(self):
        """
        Case: Create persona with missing required fields
        Expected: Failure — 400 validation error
        """
        data = {"key": "no-instruction"}
        response = self.client.post("/api/v1/personas/create/", data)
        self.assertEqual(response.status_code, 400, response.data)
        self.assertIn("instruction", response.data)


class TestListPersonas(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="listpersonas", password="pass")
        self.token, _ = Token.objects.get_or_create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")
        Persona.objects.create(
            key="test-persona-1",
            name="Test One",
            instruction="Test instruction",
            persona_type=Persona.PersonaType.CUSTOM,
        )
        Persona.objects.create(
            key="test-persona-2",
            name="Test Two",
            instruction="Test instruction 2",
            persona_type=Persona.PersonaType.BUILTIN,
        )

    def test_list_personas_case_1(self):
        """
        Case: List all personas (builtin + custom)
        Expected: Success — both returned
        """
        response = self.client.get("/api/v1/personas/list/")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertGreaterEqual(len(response.data), 2)

    def test_list_personas_case_2(self):
        """
        Case: List personas without auth
        Expected: Failure — 401 Unauthorized
        """
        self.client.credentials()
        response = self.client.get("/api/v1/personas/list/")
        self.assertEqual(response.status_code, 401, response.data)
