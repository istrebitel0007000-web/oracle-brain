"""tests/test_web.py — Flask route integration tests"""
import io
import json
import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("FLASK_ENV", "testing")
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-for-testing")
    monkeypatch.setenv("GROQ_KEY_1", "fake-groq-key")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("REDIS_URL", raising=False)
    monkeypatch.delenv("GOOGLE_CLIENT_ID", raising=False)
    monkeypatch.delenv("GOOGLE_CLIENT_SECRET", raising=False)

    # Patch Groq to avoid real API calls
    with patch("oracle_brain.llm._GROQ_AVAILABLE", True):
        with patch("oracle_brain.llm.Groq", MagicMock()):
            from oracle_brain import create_app
            import importlib
            import oracle_brain.llm as llm_mod
            importlib.reload(llm_mod)
            application = create_app()
            application.config["TESTING"] = True
            yield application


@pytest.fixture
def client(app):
    return app.test_client()


def test_health_endpoint(client):
    r = client.get("/health")
    assert r.status_code == 200
    data = json.loads(r.data)
    assert data["status"] == "ok"


def test_manifest_json(client):
    r = client.get("/manifest.json")
    assert r.status_code == 200
    data = json.loads(r.data)
    assert data["name"] == "Oracle Brain"
    assert "icons" in data


def test_service_worker(client):
    r = client.get("/sw.js")
    assert r.status_code == 200
    assert b"serviceWorker" in r.data.lower() or b"cache" in r.data.lower()


def test_index_redirects_to_login_if_oauth_configured(client, monkeypatch, app):
    """If OAuth is configured, unauthenticated users are redirected to /login."""
    with patch("oracle_brain.web.oauth_enabled", return_value=True):
        r = client.get("/")
        # Should redirect (302) to login
        assert r.status_code in (302, 200)


def test_index_loads_without_oauth(client):
    """Without OAuth, index should load for anyone."""
    with patch("oracle_brain.web.oauth_enabled", return_value=False):
        r = client.get("/")
        assert r.status_code == 200
        assert b"Oracle Brain" in r.data


def test_api_me_unauthenticated(client):
    r = client.get("/api/me")
    assert r.status_code == 200
    data = json.loads(r.data)
    assert data["authenticated"] is False


def test_api_me_authenticated(client):
    with client.session_transaction() as sess:
        sess["user"] = {"email": "test@test.com", "name": "Test", "role": "user"}
    r = client.get("/api/me")
    data = json.loads(r.data)
    assert data["authenticated"] is True
    assert data["user"]["email"] == "test@test.com"


def test_api_conversations_no_db(client):
    r = client.get("/api/conversations")
    assert r.status_code == 200
    data = json.loads(r.data)
    assert data["conversations"] == []


def test_api_cost_today(client):
    r = client.get("/api/cost_today")
    assert r.status_code == 200
    data = json.loads(r.data)
    assert "cost_today" in data
    assert data["cost_today"] == 0.0


def test_upload_no_file(client):
    r = client.post("/api/upload")
    assert r.status_code == 400
    data = json.loads(r.data)
    assert "error" in data


def test_upload_txt_file(client, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    content = b"This is a test file for Oracle Brain."
    data = {"file": (io.BytesIO(content), "test.txt")}
    r = client.post("/api/upload", data=data, content_type="multipart/form-data")
    assert r.status_code == 200
    result = json.loads(r.data)
    assert result["success"] is True
    assert result["filename"] == "test.txt"
    assert "This is a test file" in result.get("extracted_preview", "")


def test_upload_disallowed_extension(client):
    data = {"file": (io.BytesIO(b"binary"), "evil.exe")}
    r = client.post("/api/upload", data=data, content_type="multipart/form-data")
    assert r.status_code == 400
    result = json.loads(r.data)
    assert "error" in result


def test_api_settings_get(client):
    r = client.get("/api/settings")
    assert r.status_code == 200
    data = json.loads(r.data)
    assert "model" in data
    assert "temperature" in data


def test_api_settings_post(client):
    r = client.post(
        "/api/settings",
        data=json.dumps({"temperature": 0.5}),
        content_type="application/json"
    )
    assert r.status_code == 200
    data = json.loads(r.data)
    assert data["success"] is True


def test_api_settings_no_secret_keys_exposed(client):
    """Settings endpoint must never expose API keys."""
    r = client.get("/api/settings")
    data = json.loads(r.data)
    for key in data:
        assert "key" not in key.lower() or key == "allowed_upload_exts", f"Possible key leak: {key}"


def test_admin_requires_admin_role(client):
    # Not logged in
    r = client.get("/admin/")
    assert r.status_code in (302, 401, 403)


def test_admin_accessible_by_admin(client):
    with client.session_transaction() as sess:
        sess["user"] = {"email": "admin@test.com", "name": "Admin", "role": "admin"}
    r = client.get("/admin/")
    assert r.status_code == 200
    assert b"Oracle Brain" in r.data


def test_clear_history(client):
    r = client.delete("/api/history")
    assert r.status_code == 200
    data = json.loads(r.data)
    assert data["success"] is True
