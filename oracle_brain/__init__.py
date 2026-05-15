"""
oracle_brain/__init__.py — Flask application factory
"""
from __future__ import annotations

import datetime
import logging
import os
import secrets
import sys
from pathlib import Path

from flask import Flask

log = logging.getLogger("oracle")


def create_app(config_override: dict | None = None) -> Flask:
    """Create and configure the Flask application."""
    app = Flask(__name__, static_folder=None)

    # Secret key — MUST be set via env for sessions to survive Render redeploys
    app.secret_key = os.getenv("SECRET_KEY") or secrets.token_hex(32)
    if not os.getenv("SECRET_KEY"):
        log.warning("SECRET_KEY not set — sessions will not survive restarts.")

    app.config.update({
        "SESSION_COOKIE_HTTPONLY": True,
        "SESSION_COOKIE_SAMESITE": "Lax",
        "SESSION_COOKIE_SECURE": os.getenv("FLASK_ENV") == "production",
        "PERMANENT_SESSION_LIFETIME": datetime.timedelta(days=30),
        "MAX_CONTENT_LENGTH": 50 * 1024 * 1024,
    })

    from oracle_brain.config import load_config
    cfg = load_config()
    if config_override:
        cfg.update(config_override)
    app.oracle_config = cfg  # type: ignore[attr-defined]

    log_level = logging.DEBUG if os.getenv("FLASK_DEBUG") else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(cfg.get("log_file", "oracle.log"), encoding="utf-8"),
        ],
    )

    from oracle_brain.db import init_db
    init_db(postgres_url=cfg.get("postgres_url", ""), redis_url=cfg.get("redis_url", ""))

    from oracle_brain.llm import init_llm
    init_llm()

    from oracle_brain.auth import auth_bp, init_oauth
    init_oauth(app)
    app.register_blueprint(auth_bp)

    from oracle_brain.admin import admin_bp
    app.register_blueprint(admin_bp)

    from oracle_brain.web import web_bp
    app.register_blueprint(web_bp)

    for d in [
        cfg.get("upload_dir", "uploads"),
        cfg.get("backup_dir", "backups"),
        cfg.get("code_output_dir", "oracle_code"),
        cfg.get("user_data_dir", "user_data"),
        cfg.get("image_output_dir", "oracle_images"),
    ]:
        Path(d).mkdir(parents=True, exist_ok=True)

    log.info("Oracle Brain app created.")
    return app
