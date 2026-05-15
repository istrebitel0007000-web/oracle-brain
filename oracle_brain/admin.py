"""
oracle_brain/admin.py — Admin dashboard Blueprint
Routes: /admin/*  (admin_required)
"""
from __future__ import annotations

import logging
import sys
from datetime import datetime

from flask import Blueprint, jsonify, render_template_string, request

from oracle_brain.auth import admin_required, current_user
from oracle_brain.db import get_db, db_available
from oracle_brain.state import state
from oracle_brain.i18n import t, LANGUAGE_NAMES
from oracle_brain.config import PRICING_PER_1M

log = logging.getLogger("oracle.admin")
admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

_ADMIN_HTML = """
<!DOCTYPE html>
<html lang="{{ lang }}" dir="{{ dir }}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{ _t('admin') }} — Oracle Brain</title>
<style>
  :root {
    --bg: #0d1117; --surface: #161b22; --border: #30363d;
    --text: #e6edf3; --muted: #8b949e; --accent: #58a6ff;
    --green: #3fb950; --red: #f85149; --yellow: #d29922;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: var(--bg); color: var(--text); font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }
  .header { background: var(--surface); border-bottom: 1px solid var(--border); padding: 1rem 2rem; display: flex; align-items: center; justify-content: space-between; }
  .header h1 { font-size: 1.25rem; color: var(--accent); }
  .header a { color: var(--muted); text-decoration: none; font-size: 0.875rem; }
  .header a:hover { color: var(--text); }
  .container { max-width: 1200px; margin: 2rem auto; padding: 0 1.5rem; }
  .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 1rem; margin-bottom: 2rem; }
  .stat-card { background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 1.25rem; }
  .stat-card .label { font-size: 0.75rem; color: var(--muted); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.5rem; }
  .stat-card .value { font-size: 2rem; font-weight: 700; color: var(--text); }
  .stat-card .value.green { color: var(--green); }
  .stat-card .value.yellow { color: var(--yellow); }
  .section { background: var(--surface); border: 1px solid var(--border); border-radius: 8px; margin-bottom: 1.5rem; overflow: hidden; }
  .section-header { padding: 1rem 1.25rem; border-bottom: 1px solid var(--border); font-weight: 600; font-size: 0.9rem; color: var(--accent); }
  table { width: 100%; border-collapse: collapse; }
  th { padding: 0.75rem 1.25rem; text-align: left; font-size: 0.75rem; color: var(--muted); text-transform: uppercase; letter-spacing: 0.05em; border-bottom: 1px solid var(--border); }
  td { padding: 0.75rem 1.25rem; font-size: 0.875rem; border-bottom: 1px solid var(--border); }
  tr:last-child td { border-bottom: none; }
  tr:hover td { background: rgba(255,255,255,0.02); }
  .badge { display: inline-block; padding: 0.15rem 0.5rem; border-radius: 12px; font-size: 0.7rem; font-weight: 600; }
  .badge.admin { background: rgba(88,166,255,0.15); color: var(--accent); }
  .badge.user { background: rgba(63,185,80,0.15); color: var(--green); }
  .avatar { width: 28px; height: 28px; border-radius: 50%; vertical-align: middle; margin-right: 0.5rem; }
  .btn { padding: 0.4rem 0.9rem; border-radius: 6px; border: none; cursor: pointer; font-size: 0.8rem; font-weight: 600; }
  .btn-red { background: rgba(248,81,73,0.15); color: var(--red); border: 1px solid var(--red); }
  .btn-red:hover { background: rgba(248,81,73,0.3); }
  .no-db { text-align: center; padding: 3rem; color: var(--muted); }
  .refresh { font-size: 0.75rem; color: var(--muted); }
</style>
</head>
<body>
<div class="header">
  <h1>🔮 Oracle Brain — {{ _t('admin') }}</h1>
  <div style="display:flex;gap:1rem;align-items:center;">
    <span class="refresh">{{ user.get('email','') }}</span>
    <a href="/">← {{ _t('new_chat') }}</a>
    <a href="/logout">{{ _t('logout') }}</a>
  </div>
</div>
<div class="container">

  {% if not db_available %}
  <div class="no-db">
    <p>⚠️ PostgreSQL not configured. Stats shown from in-memory state only.</p>
    <p style="margin-top:0.5rem;font-size:0.8rem;">Set <code>DATABASE_URL</code> in Render environment variables for full admin features.</p>
  </div>
  {% endif %}

  <!-- Summary stats -->
  <div class="stats-grid">
    <div class="stat-card">
      <div class="label">{{ _t('total_users') }}</div>
      <div class="value green">{{ stats.total_users }}</div>
    </div>
    <div class="stat-card">
      <div class="label">{{ _t('total_requests') }}</div>
      <div class="value">{{ stats.total_requests }}</div>
    </div>
    <div class="stat-card">
      <div class="label">{{ _t('total_cost') }}</div>
      <div class="value yellow">${{ "%.4f"|format(stats.total_cost_usd) }}</div>
    </div>
    <div class="stat-card">
      <div class="label">{{ _t('active_users') }} (24h)</div>
      <div class="value">{{ stats.active_users_24h }}</div>
    </div>
    <div class="stat-card">
      <div class="label">Cache hits</div>
      <div class="value">{{ mem_stats.cache_hits }}</div>
    </div>
    <div class="stat-card">
      <div class="label">Anthropic calls</div>
      <div class="value">{{ mem_stats.anthropic_calls }}</div>
    </div>
    <div class="stat-card">
      <div class="label">Model fallbacks</div>
      <div class="value">{{ mem_stats.model_fallbacks }}</div>
    </div>
    <div class="stat-card">
      <div class="label">Quota errors</div>
      <div class="value">{{ mem_stats.quota_errors }}</div>
    </div>
  </div>

  <!-- Users table -->
  {% if users %}
  <div class="section">
    <div class="section-header">👥 Users</div>
    <table>
      <tr>
        <th>User</th><th>Role</th><th>Last seen</th>
        <th>Requests</th><th>Cost (USD)</th><th>Actions</th>
      </tr>
      {% for u in users %}
      <tr>
        <td>
          {% if u.picture %}<img src="{{ u.picture }}" class="avatar" referrerpolicy="no-referrer">{% endif %}
          {{ u.name or u.email }}<br>
          <small style="color:var(--muted)">{{ u.email }}</small>
        </td>
        <td><span class="badge {{ u.role }}">{{ u.role }}</span></td>
        <td><small>{{ u.last_seen.strftime('%Y-%m-%d %H:%M') if u.last_seen else '—' }}</small></td>
        <td>{{ u.total_requests or 0 }}</td>
        <td>${{ "%.4f"|format(u.total_cost or 0) }}</td>
        <td>
          <button class="btn btn-red" onclick="resetLimit('{{ u.email }}')">Reset limit</button>
        </td>
      </tr>
      {% endfor %}
    </table>
  </div>
  {% endif %}

  <!-- Cost by model -->
  {% if cost_by_user %}
  <div class="section">
    <div class="section-header">💰 Cost by User</div>
    <table>
      <tr><th>User</th><th>Tokens In</th><th>Tokens Out</th><th>Total Cost</th><th>Requests</th></tr>
      {% for row in cost_by_user %}
      <tr>
        <td>{{ row.user_email }}</td>
        <td>{{ "{:,}".format(row.total_tokens_in or 0) }}</td>
        <td>{{ "{:,}".format(row.total_tokens_out or 0) }}</td>
        <td>${{ "%.4f"|format(row.total_cost_usd or 0) }}</td>
        <td>{{ row.total_requests }}</td>
      </tr>
      {% endfor %}
    </table>
  </div>
  {% endif %}

  <!-- Audit log -->
  {% if audit %}
  <div class="section">
    <div class="section-header">📋 Recent Audit Log</div>
    <table>
      <tr><th>Time</th><th>User</th><th>Action</th><th>Detail</th></tr>
      {% for entry in audit %}
      <tr>
        <td><small>{{ entry.created_at.strftime('%Y-%m-%d %H:%M:%S') if entry.created_at else '—' }}</small></td>
        <td><small>{{ entry.user_email or '—' }}</small></td>
        <td>{{ entry.action }}</td>
        <td><small style="color:var(--muted)">{{ entry.detail or '' }}</small></td>
      </tr>
      {% endfor %}
    </table>
  </div>
  {% endif %}

</div>
<script>
async function resetLimit(email) {
  if (!confirm('Reset rate limit for ' + email + '?')) return;
  const r = await fetch('/admin/api/reset_limit', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({email})
  });
  const d = await r.json();
  alert(d.message || 'Done');
}
</script>
</body>
</html>
"""


@admin_bp.route("/")
@admin_required
def dashboard():
    lang = request.cookies.get("lang", "en")
    dir_ = "rtl" if lang == "ar" else "ltr"
    user = current_user() or {}

    db = get_db()
    stats = {"total_users": 0, "total_requests": 0, "total_cost_usd": 0.0, "active_users_24h": 0}
    users: list[dict] = []
    cost_by_user: list[dict] = []
    audit: list[dict] = []

    if db:
        try:
            stats = db.get_admin_stats()
            users_raw = db.list_users()
            costs = db.get_cost_summary()
            cost_map = {r["user_email"]: r for r in costs}
            for u in users_raw:
                email = u["email"]
                cost_info = cost_map.get(email, {})
                u["total_requests"] = cost_info.get("total_requests", 0)
                u["total_cost"] = cost_info.get("total_cost_usd", 0.0)
            users = users_raw
            cost_by_user = costs
            audit = db.get_audit_log(limit=50)
        except Exception as e:
            log.error(f"Admin dashboard DB error: {e}")

    mem_stats = state.get_stats_snapshot()

    def _t(key: str, **kw) -> str:
        return t(key, lang, **kw)

    return render_template_string(
        _ADMIN_HTML,
        lang=lang, dir=dir_, user=user,
        stats=stats, mem_stats=mem_stats,
        users=users, cost_by_user=cost_by_user, audit=audit,
        db_available=db_available(),
        _t=_t,
    )


@admin_bp.route("/api/stats")
@admin_required
def api_stats():
    db = get_db()
    db_stats = db.get_admin_stats() if db else {}
    mem_stats = state.get_stats_snapshot()
    return jsonify({"db": db_stats, "memory": mem_stats})


@admin_bp.route("/api/users")
@admin_required
def api_users():
    db = get_db()
    if not db:
        return jsonify({"users": [], "error": "Database not configured"})
    try:
        users = db.list_users()
        return jsonify({"users": users})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@admin_bp.route("/api/reset_limit", methods=["POST"])
@admin_required
def api_reset_limit():
    data = request.get_json() or {}
    email = data.get("email", "")
    if not email:
        return jsonify({"error": "email required"}), 400
    from oracle_brain.rate_limiter import reset_user_limit
    reset_user_limit(email)
    log.info(f"Admin reset rate limit for {email}")
    return jsonify({"message": f"Rate limit reset for {email}"})


@admin_bp.route("/api/cost_summary")
@admin_required
def api_cost_summary():
    db = get_db()
    if not db:
        return jsonify({"error": "Database not configured"})
    try:
        return jsonify(db.get_cost_summary())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@admin_bp.route("/api/audit")
@admin_required
def api_audit():
    limit = min(int(request.args.get("limit", 100)), 500)
    db = get_db()
    if not db:
        return jsonify({"error": "Database not configured"})
    try:
        return jsonify(db.get_audit_log(limit=limit))
    except Exception as e:
        return jsonify({"error": str(e)}), 500
