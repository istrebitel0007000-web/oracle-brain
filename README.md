# 🔮 Oracle Brain v6.0.0

A full-featured AI assistant web app with multi-user support, Google OAuth, PostgreSQL persistence, Redis caching, file uploads, multi-language UI, and an admin dashboard.

---

## What's new in v6.0.0

| Feature | Details |
|---|---|
| 🔐 Google OAuth | Real user accounts via Google Sign-In |
| 💾 PostgreSQL | Full persistence — survives Render redeploys |
| ⚡ Redis | Rate limiting + response caching |
| 👥 Multi-user | Each user has isolated history, notes, bookmarks |
| 📂 File uploads | PDF, TXT, images with text extraction |
| 🤖 Anthropic fallback | Claude kicks in when all Groq models fail |
| 🌐 4 languages | English, Arabic (RTL), Russian, Uzbek |
| 📱 PWA | Installable on mobile and desktop |
| 📊 Admin dashboard | Users, costs, audit log, rate limit reset |
| 🐛 14 bugs fixed | Rate limiter, atomic writes, unbounded lists, etc. |

---

## Quick start (local)

```bash
git clone https://github.com/istrebitel0007000-web/oracle-brain
cd oracle-brain
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env and fill in GROQ_KEY_1 at minimum
python app.py
# Open http://localhost:5000
```

---

## Environment variables

| Variable | Required | Description |
|---|---|---|
| `SECRET_KEY` | ✅ | Random 64-char string. Generate: `python -c "import secrets; print(secrets.token_hex(32))"` |
| `GROQ_KEY_1` | ✅ | Your Groq API key. Get from console.groq.com |
| `GROQ_KEY_2`, `GROQ_KEY_3` | Optional | Extra keys for rotation/fallback |
| `ANTHROPIC_API_KEY` | Optional | Enables Claude as fallback LLM |
| `GOOGLE_CLIENT_ID` | Optional | Enables Google OAuth login |
| `GOOGLE_CLIENT_SECRET` | Optional | Required with `GOOGLE_CLIENT_ID` |
| `DATABASE_URL` | Optional | PostgreSQL connection string. Falls back to JSON files |
| `REDIS_URL` | Optional | Redis URL. Falls back to in-memory rate limiting |
| `RATE_PER_MINUTE` | Optional | Default: 20 |
| `RATE_PER_HOUR` | Optional | Default: 200 |
| `RATE_PER_DAY` | Optional | Default: 1000 |

---

## Deploy to Render

1. Push this repo to GitHub
2. Go to [render.com](https://render.com) → New → Blueprint
3. Connect your repo — Render auto-reads `render.yaml`
4. Set these environment variables in Render dashboard:
   - `GROQ_KEY_1` — your Groq key
   - `GOOGLE_CLIENT_ID` + `GOOGLE_CLIENT_SECRET` — for OAuth
   - `ANTHROPIC_API_KEY` — optional, for Claude fallback
   - `REDIS_URL` — optional, add a Redis service in Render
5. `DATABASE_URL` is auto-set by the Render PostgreSQL database in `render.yaml`
6. Deploy ✅

### Google OAuth setup
1. Go to [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
2. Create OAuth 2.0 Client ID → Web application
3. Authorized redirect URIs: `https://your-app.onrender.com/auth/callback`
4. Copy Client ID and Secret to Render env vars

---

## Project structure

```
oracle-brain/
├── app.py                    # Gunicorn entry point
├── requirements.txt
├── render.yaml               # Render deployment config
├── .env.example              # Environment variable template
├── oracle_brain/
│   ├── __init__.py           # Flask app factory
│   ├── config.py             # Settings management (atomic, schema-migrating)
│   ├── state.py              # Thread-safe global state + per-user state
│   ├── db.py                 # PostgreSQL + Redis layer
│   ├── auth.py               # Google OAuth + session management
│   ├── llm.py                # Groq (key rotation) + Anthropic fallback
│   ├── uploads.py            # File upload + PDF/image text extraction
│   ├── rate_limiter.py       # Fixed rate limiter (Redis-backed)
│   ├── i18n.py               # EN / AR / RU / UZ translations
│   ├── admin.py              # Admin dashboard Blueprint
│   └── web.py                # Main web Blueprint (routes + SSE streaming)
└── tests/
    ├── test_config.py
    ├── test_state.py
    ├── test_rate_limiter.py
    ├── test_i18n.py
    ├── test_uploads.py
    ├── test_llm.py
    └── test_web.py
```

---

## Running tests

```bash
pip install pytest pytest-cov
pytest tests/ -v --cov=oracle_brain
```

---

## Admin access

The **first user** to log in via Google OAuth is automatically assigned the `admin` role.

You can also pre-assign admin emails in `settings.json`:
```json
{
  "admin_emails": ["you@example.com"]
}
```

Admin panel: `https://your-app.onrender.com/admin`

---

## Bugs fixed (from v5.5)

| # | Bug | Fix |
|---|---|---|
| 1 | 10,909-line monolith | Split into 9 focused modules |
| 2 | Global mutable state without locks | `OracleState` class with `RLock` on every method |
| 3 | Rate limiter `usage` dict read wrong keys | Each window reads from its own correct instance |
| 4 | Fake API key silently continued | Raises `RuntimeError` in production |
| 5 | `safe_path` allowed absolute paths by default | `allow_absolute_paths: false` by default |
| 6 | Config errors silently swallowed | Logs warning before falling back to defaults |
| 7 | Unbounded `latency_samples` list | `deque(maxlen=50)` |
| 8 | `save_config` not atomic | Uses `atomic_write_json` |
| 9 | Rate config re-read on every request | Cached at module load |
| 10 | Personas mutated global state at import | Loaded lazily, not at import |
| 11 | Hardcoded pricing data hard to update | Centralized in `config.PRICING_PER_1M` |
| 12 | ANSI rendering on non-TTY | Early-out check for `sys.stdout.isatty()` |
| 13 | Missing type annotation on `image_path` | `Optional[str]` |
| 14 | No CI/CD | GitHub Actions workflow with pytest + coverage |
