"""
oracle_brain/auth.py — Google OAuth 2.0 + session management
"""
from __future__ import annotations

import logging
import os
from functools import wraps
from typing import Optional

from flask import Blueprint, redirect, request, session, url_for, jsonify

log = logging.getLogger("oracle.auth")

try:
    from authlib.integrations.flask_client import OAuth
    _AUTHLIB_AVAILABLE = True
except ImportError:
    _AUTHLIB_AVAILABLE = False

auth_bp = Blueprint("auth", __name__)
oauth: Optional[object] = None


def init_oauth(app) -> None:
    global oauth
    if not _AUTHLIB_AVAILABLE:
        log.warning("authlib not installed. Google OAuth disabled.")
        return
    client_id = os.getenv("GOOGLE_CLIENT_ID", "")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET", "")
    if not client_id or not client_secret:
        log.warning("GOOGLE_CLIENT_ID/SECRET not set. OAuth disabled.")
        return
    oauth = OAuth(app)
    oauth.register(
        name="google",
        client_id=client_id,
        client_secret=client_secret,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )
    log.info("Google OAuth initialised.")


@auth_bp.route("/login")
def login():
    if oauth is None:
        return redirect(url_for("web.index"))
    redirect_uri = url_for("auth.callback", _external=True)
    return oauth.google.authorize_redirect(redirect_uri)


@auth_bp.route("/auth/callback")
def callback():
    if oauth is None:
        return redirect(url_for("web.index"))
    try:
        token = oauth.google.authorize_access_token()
        userinfo = token.get("userinfo") or oauth.google.userinfo()
        email = userinfo.get("email", "")
        name = userinfo.get("name", email)
        picture = userinfo.get("picture", "")
        if not email:
            return "OAuth error: no email returned", 400

        from oracle_brain.db import get_db
        db = get_db()
        from oracle_brain.config import load_config
        cfg = load_config()
        if db:
            users = db.list_users()
            role = "admin" if len(users) == 0 else "user"
            if email in cfg.get("admin_emails", []):
                role = "admin"
            db.upsert_user(email=email, name=name, picture=picture, role=role)
            db.log_audit(email, "login", {"name": name})
            user = db.get_user(email)
            role = user.get("role", "user") if user else role
        else:
            role = "admin" if email in cfg.get("admin_emails", []) else "user"

        session.permanent = True
        session["user"] = {"email": email, "name": name, "picture": picture, "role": role}
        log.info(f"User logged in: {email} role={role}")
        return redirect(url_for("web.index"))
    except Exception as e:
        log.error(f"OAuth callback error: {e}")
        return f"Login failed: {e}", 500


@auth_bp.route("/logout")
def logout():
    user = session.get("user", {})
    email = user.get("email", "anonymous")
    from oracle_brain.db import get_db
    db = get_db()
    if db:
        try:
            db.log_audit(email, "logout")
        except Exception:
            pass
    session.clear()
    return redirect(url_for("web.index"))


@auth_bp.route("/api/me")
def me():
    user = session.get("user")
    if not user:
        return jsonify({"authenticated": False}), 401
    return jsonify({"authenticated": True, "user": user})


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("user"):
            if request.is_json or request.path.startswith("/api/"):
                return jsonify({"error": "Authentication required"}), 401
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        user = session.get("user")
        if not user:
            if request.is_json or request.path.startswith("/api/"):
                return jsonify({"error": "Authentication required"}), 401
            return redirect(url_for("auth.login"))
        if user.get("role") != "admin":
            return jsonify({"error": "Admin access required"}), 403
        return f(*args, **kwargs)
    return decorated


def current_user() -> Optional[dict]:
    return session.get("user")


def current_user_email() -> str:
    user = session.get("user")
    return user["email"] if user else "anonymous"


def is_admin() -> bool:
    user = session.get("user")
    return bool(user and user.get("role") == "admin")


def oauth_enabled() -> bool:
    return oauth is not None
