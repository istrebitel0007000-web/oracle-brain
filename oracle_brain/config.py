"""oracle_brain/config.py — Configuration management (atomic, schema-migrating)"""
from __future__ import annotations
import json, logging, os, threading
from pathlib import Path
from typing import Any

log = logging.getLogger("oracle.config")
CONFIG_FILE = "settings.json"
_config_lock = threading.RLock()

_DEPRECATED_MODELS = {
    "llama-3.1-70b-versatile", "llama-3.2-11b-vision-preview",
    "llama-3.2-90b-vision-preview", "mixtral-8x7b-32768",
}

DEFAULT_CONFIG: dict[str, Any] = {
    "model": "deepseek-r1-distill-llama-70b",
    "vision_model": "meta-llama/llama-4-scout-17b-16e-instruct",
    "fallback_models": [
        "qwen-2.5-72b-instruct", "llama-3.3-70b-versatile",
        "llama-3.1-8b-instant", "gemma2-9b-it",
    ],
    "anthropic_model": "claude-sonnet-4-20250514",
    "anthropic_fallback_enabled": True,
    "max_retries": 5, "request_delay": 0.3,
    "max_prompt_len": 8000, "max_tokens": 4096,
    "temperature": 0.7, "voice_enabled": False, "voice_rate": 175,
    "cache_enabled": True, "save_history": True,
    "history_file": "chat_history.json",
    "session_file": "session_restore.json",
    "log_file": "oracle.log", "telegram_token": "", "web_port": 5000,
    "active_persona": "tech_oracle", "scheduled_tasks": [],
    "optimize_prompts": True, "validate_responses": True,
    "max_history_turns": 20, "confidence_check": True,
    "latency_warn_ms": 5000, "offline_mode": False,
    "auto_translate": True, "mood_tracking": True,
    "suggest_followups": True, "auto_save_code": True,
    "code_output_dir": "oracle_code", "topic_tagging": True,
    "daily_digest": True, "digest_file": "daily_digest.json",
    "templates_file": "prompt_templates.json",
    "context_file": "user_context.txt", "user_context": "",
    "streaming": True, "notes_file": "oracle_notes.json",
    "bookmarks_file": "oracle_bookmarks.json",
    "response_length": "medium", "projects_file": "oracle_projects.json",
    "active_project": "", "smart_clarify": True,
    "rating_file": "oracle_ratings.json",
    "personas_file": "oracle_personas.json",
    "inject_datetime": True, "user_set_length": False,
    "rag_enabled": False, "rag_file": "oracle_rag.json",
    "rag_auto_ingest": False, "rag_min_answer_len": 80,
    "tg_pool_size": 8, "tg_rate_max": 10, "tg_rate_window": 60,
    "image_output_dir": "oracle_images",
    "ollama_enabled": False, "ollama_url": "http://localhost:11434",
    "ollama_model": "llama3.1", "audit_tools": True,
    "auto_update_check": True, "auto_backup": True,
    "backup_keep": 30, "backup_dir": "backups",
    "track_costs": True, "daily_budget_usd": 0.0,
    "redact_on_export": True, "encrypt_backups": False,
    "incognito": False, "csrf_protection": True,
    "allow_absolute_paths": False,
    "path_allowlist": ["oracle_code", "oracle_drafts", "backups", "uploads"],
    "safe_mode": True, "sqlite_enabled": False,
    "sqlite_file": "oracle.db", "webhook_token": "",
    "terminal_markdown": True, "sticky_lang": "",
    "multi_user": True, "user_data_dir": "user_data",
    "postgres_url": "", "redis_url": "",
    "upload_dir": "uploads", "max_upload_mb": 20,
    "allowed_upload_exts": [".txt",".py",".md",".pdf",".png",".jpg",".jpeg",".csv",".json"],
    "ui_language": "en", "admin_emails": [],
    "google_client_id": "", "google_client_secret": "",
    "secret_key": "",
}

PRICING_PER_1M: dict[str, dict[str, float]] = {
    "deepseek-r1-distill-llama-70b": {"in": 0.75, "out": 0.99},
    "qwen-2.5-72b-instruct": {"in": 0.59, "out": 0.79},
    "llama-3.3-70b-versatile": {"in": 0.59, "out": 0.79},
    "llama-3.1-8b-instant": {"in": 0.05, "out": 0.08},
    "gemma2-9b-it": {"in": 0.20, "out": 0.20},
    "meta-llama/llama-4-scout-17b-16e-instruct": {"in": 0.11, "out": 0.34},
    "claude-sonnet-4-20250514": {"in": 3.00, "out": 15.00},
    "claude-haiku-4-5-20251001": {"in": 0.80, "out": 4.00},
}


def atomic_write_json(path: str, data: Any, pretty: bool = True) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = str(p) + f".tmp.{os.getpid()}"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2 if pretty else None, ensure_ascii=False)
        os.replace(tmp, p)
    except Exception:
        Path(tmp).unlink(missing_ok=True)
        raise


def atomic_read_json(path: str, default: Any = None) -> Any:
    p = Path(path)
    if not p.exists():
        return default
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        log.warning(f"atomic_read_json: failed {path}: {e}")
        return default


def _migrate_models(cfg: dict) -> dict:
    if cfg.get("vision_model") in _DEPRECATED_MODELS:
        cfg["vision_model"] = DEFAULT_CONFIG["vision_model"]
    if cfg.get("model") in _DEPRECATED_MODELS:
        cfg["model"] = DEFAULT_CONFIG["model"]
    fb = cfg.get("fallback_models", [])
    if isinstance(fb, list):
        cfg["fallback_models"] = [m for m in fb if m not in _DEPRECATED_MODELS] \
            or list(DEFAULT_CONFIG["fallback_models"])
    return cfg


def load_config() -> dict:
    if Path(CONFIG_FILE).exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
            merged = {**DEFAULT_CONFIG, **saved}
            merged = _migrate_models(merged)
            try:
                atomic_write_json(CONFIG_FILE, merged)
            except Exception:
                pass
            return merged
        except Exception as e:
            log.warning(f"Failed to load {CONFIG_FILE}: {e}. Using defaults.")
    atomic_write_json(CONFIG_FILE, DEFAULT_CONFIG)
    return DEFAULT_CONFIG.copy()


def save_config(cfg: dict) -> None:
    with _config_lock:
        try:
            atomic_write_json(CONFIG_FILE, cfg)
        except Exception as e:
            log.error(f"save_config failed: {e}")
