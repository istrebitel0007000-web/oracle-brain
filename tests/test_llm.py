"""tests/test_llm.py — LLM module tests (no real API calls)"""
import os, sys, importlib
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture(autouse=True)
def mock_groq_and_anthropic():
    with patch.dict("sys.modules", {"groq": MagicMock(), "anthropic": MagicMock()}):
        yield


def test_cache_key_deterministic():
    import oracle_brain.llm as llm; importlib.reload(llm)
    k1 = llm._cache_key("hello", "model-a")
    k2 = llm._cache_key("hello", "model-a")
    assert k1 == k2


def test_cache_key_differs_by_model():
    import oracle_brain.llm as llm; importlib.reload(llm)
    assert llm._cache_key("p", "model-a") != llm._cache_key("p", "model-b")


def test_cache_key_differs_by_prompt():
    import oracle_brain.llm as llm; importlib.reload(llm)
    assert llm._cache_key("a", "m") != llm._cache_key("b", "m")


def test_cache_key_differs_by_image_path():
    import oracle_brain.llm as llm; importlib.reload(llm)
    k1 = llm._cache_key("p", "m", image_path=None)
    k2 = llm._cache_key("p", "m", image_path="/img.jpg")
    assert k1 != k2


def test_set_and_get_cache():
    import oracle_brain.llm as llm; importlib.reload(llm)
    llm._set_cache("test-key", "test-response")
    assert llm._get_cached("test-key") == "test-response"


def test_cache_miss_returns_none():
    import oracle_brain.llm as llm; importlib.reload(llm)
    assert llm._get_cached("definitely-not-in-cache-xyz-999") is None


def test_clear_cache():
    import oracle_brain.llm as llm; importlib.reload(llm)
    llm._set_cache("k1", "v1")
    llm._set_cache("k2", "v2")
    cleared = llm.clear_cache()
    assert cleared >= 2
    assert llm._get_cached("k1") is None


def test_no_keys_raises_in_production(monkeypatch):
    """FIX #4: Must raise RuntimeError in production with no keys."""
    monkeypatch.setenv("FLASK_ENV", "production")
    for i in range(1, 11):
        monkeypatch.delenv(f"GROQ_KEY_{i}", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    import oracle_brain.llm as llm; importlib.reload(llm)
    with pytest.raises(RuntimeError, match="GROQ_KEY_1"):
        llm._load_groq_keys()


def test_no_keys_warns_in_development(monkeypatch):
    monkeypatch.setenv("FLASK_ENV", "development")
    for i in range(1, 11):
        monkeypatch.delenv(f"GROQ_KEY_{i}", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    import oracle_brain.llm as llm; importlib.reload(llm)
    assert llm._load_groq_keys() == ["MISSING_KEY"]


def test_multiple_keys_loaded(monkeypatch):
    monkeypatch.setenv("GROQ_KEY_1", "key-one")
    monkeypatch.setenv("GROQ_KEY_2", "key-two")
    for i in range(3, 11):
        monkeypatch.delenv(f"GROQ_KEY_{i}", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.setenv("FLASK_ENV", "development")
    import oracle_brain.llm as llm; importlib.reload(llm)
    keys = llm._load_groq_keys()
    assert "key-one" in keys and "key-two" in keys
    assert "MISSING_KEY" not in keys
