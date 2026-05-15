"""tests/test_config.py — Config module tests"""
import json, os, sys, tempfile
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


def test_default_config_has_required_keys():
    from oracle_brain.config import DEFAULT_CONFIG
    for key in ["model","fallback_models","max_tokens","temperature",
                "anthropic_model","anthropic_fallback_enabled","allow_absolute_paths",
                "multi_user","postgres_url","redis_url","upload_dir",
                "max_upload_mb","ui_language","admin_emails"]:
        assert key in DEFAULT_CONFIG, f"Missing: {key}"


def test_allow_absolute_paths_defaults_false():
    from oracle_brain.config import DEFAULT_CONFIG
    assert DEFAULT_CONFIG["allow_absolute_paths"] is False


def test_atomic_write_read(tmp_path):
    from oracle_brain.config import atomic_write_json, atomic_read_json
    p = str(tmp_path / "test.json")
    atomic_write_json(p, {"hello": "world", "num": 42})
    assert atomic_read_json(p) == {"hello": "world", "num": 42}


def test_atomic_read_missing_returns_default(tmp_path):
    from oracle_brain.config import atomic_read_json
    result = atomic_read_json(str(tmp_path / "nope.json"), default={"x": 1})
    assert result == {"x": 1}


def test_load_config_creates_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from oracle_brain.config import load_config, CONFIG_FILE
    cfg = load_config()
    assert "model" in cfg
    assert Path(CONFIG_FILE).exists()


def test_migrate_deprecated_model():
    from oracle_brain.config import _migrate_models, DEFAULT_CONFIG
    original_model = "mixtral-8x7b-32768"
    cfg = {
        "model": original_model,
        "vision_model": "llama-3.2-90b-vision-preview",
        "fallback_models": ["mixtral-8x7b-32768", "llama-3.1-8b-instant"],
    }
    result = _migrate_models(cfg)
    # Model must NOT be the deprecated one anymore
    assert result["model"] != original_model
    assert result["model"] == DEFAULT_CONFIG["model"]
    assert "mixtral-8x7b-32768" not in result["fallback_models"]
    assert "llama-3.1-8b-instant" in result["fallback_models"]


def test_migrate_good_model_unchanged():
    from oracle_brain.config import _migrate_models
    cfg = {
        "model": "deepseek-r1-distill-llama-70b",
        "vision_model": "meta-llama/llama-4-scout-17b-16e-instruct",
        "fallback_models": ["llama-3.1-8b-instant"],
    }
    result = _migrate_models(cfg)
    assert result["model"] == "deepseek-r1-distill-llama-70b"
    assert result["vision_model"] == "meta-llama/llama-4-scout-17b-16e-instruct"


def test_save_config_roundtrip(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from oracle_brain.config import load_config, save_config
    cfg = load_config()
    cfg["temperature"] = 0.99
    save_config(cfg)
    loaded = load_config()
    assert loaded["temperature"] == 0.99


def test_pricing_structure():
    from oracle_brain.config import PRICING_PER_1M
    assert "deepseek-r1-distill-llama-70b" in PRICING_PER_1M
    assert "claude-sonnet-4-20250514" in PRICING_PER_1M
    for model, prices in PRICING_PER_1M.items():
        assert "in" in prices and "out" in prices, f"Bad pricing for {model}"
        assert prices["in"] >= 0 and prices["out"] >= 0


def test_config_merge_preserves_user_values(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from oracle_brain.config import load_config, save_config, CONFIG_FILE, atomic_write_json
    # Write a partial config
    atomic_write_json(CONFIG_FILE, {"temperature": 0.1, "model": "deepseek-r1-distill-llama-70b"})
    cfg = load_config()
    assert cfg["temperature"] == 0.1
    # All defaults still present
    assert "max_tokens" in cfg and "anthropic_model" in cfg
