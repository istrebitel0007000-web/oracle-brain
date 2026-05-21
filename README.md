# 🧠 Oracle Brain v5.5

> A powerful AI assistant API built with Django REST Framework, powered by Groq with multi-model fallback, RAG knowledge base, agent tools, personas, and full cost tracking.

---

## 🚀 Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.9+ |
| Framework | Django 4.2 + Django REST Framework 3.15 |
| Database | PostgreSQL |
| AI Provider | Groq API (multi-key rotation + fallback) |
| Auth | Token Authentication |
| Deployment | Render.com |

---

## 📁 Project Structure

```
oracle_brain/
├── config/                    # Django settings, URLs, WSGI
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── apps/
│   ├── core/                  # Base model, serializer, Groq client, logging
│   ├── chat/                  # Conversations, messages, branching, export
│   ├── personas/              # Built-in & custom AI personas
│   ├── notes/                 # User notes with pin support
│   ├── bookmarks/             # Save important messages
│   ├── rag/                   # RAG knowledge base (add/search chunks)
│   ├── costs/                 # Per-call cost tracking & summaries
│   ├── agent/                 # Agent tools (web fetch, calculator, etc.)
│   ├── auth/                  # Register, login, logout, change password
│   └── webhooks/              # Webhook token generation & receive
├── tests/
│   ├── auth/                  # Auth tests + fixtures
│   ├── chat/                  # Chat tests + fixtures
│   ├── notes/                 # Notes tests
│   ├── bookmarks/             # Bookmark tests
│   ├── rag/                   # RAG tests
│   ├── costs/                 # Cost tracking tests
│   ├── personas/              # Persona tests
│   ├── agent/                 # Agent tool tests
│   └── webhooks/              # Webhook tests
├── manage.py
├── requirements.txt
├── render.yaml                # One-click Render deployment
└── .env.template              # Environment variable template
```

---

## ⚡ API Endpoints

### Auth
| Method | URL | Description |
|---|---|---|
| POST | `/api/v1/auth/register/` | Register new user |
| POST | `/api/v1/auth/login/` | Login, get token |
| POST | `/api/v1/auth/logout/` | Logout |
| POST | `/api/v1/auth/change-password/` | Change password |

### Chat
| Method | URL | Description |
|---|---|---|
| GET | `/api/v1/chat/conversations/list/` | List all conversations |
| POST | `/api/v1/chat/conversations/create/` | Create conversation |
| DELETE | `/api/v1/chat/conversations/<id>/delete/` | Delete conversation |
| POST | `/api/v1/chat/conversations/<id>/messages/send/` | Send message |
| PATCH | `/api/v1/chat/messages/<id>/rate/` | Rate message (1-5) |
| POST | `/api/v1/chat/conversations/<id>/branch/` | Branch conversation |
| GET | `/api/v1/chat/conversations/<id>/export/` | Export (json/md/csv/txt) |

### Personas
| Method | URL | Description |
|---|---|---|
| GET | `/api/v1/personas/list/` | List all personas |
| POST | `/api/v1/personas/create/` | Create custom persona |
| PUT | `/api/v1/personas/<id>/update/` | Update persona |
| DELETE | `/api/v1/personas/<id>/delete/` | Delete persona |

### Notes
| Method | URL | Description |
|---|---|---|
| GET | `/api/v1/notes/list/` | List notes |
| POST | `/api/v1/notes/create/` | Create note |
| PUT | `/api/v1/notes/<id>/update/` | Update note |
| DELETE | `/api/v1/notes/<id>/delete/` | Delete note |
| PATCH | `/api/v1/notes/<id>/pin-toggle/` | Toggle pin |

### Bookmarks
| Method | URL | Description |
|---|---|---|
| GET | `/api/v1/bookmarks/list/` | List bookmarks |
| POST | `/api/v1/bookmarks/create/` | Create bookmark |
| PUT | `/api/v1/bookmarks/<id>/update/` | Update label |
| DELETE | `/api/v1/bookmarks/<id>/delete/` | Delete bookmark |

### RAG Knowledge Base
| Method | URL | Description |
|---|---|---|
| GET | `/api/v1/rag/list/` | List chunks |
| POST | `/api/v1/rag/create/` | Add chunk (supports auto-split) |
| GET | `/api/v1/rag/search/` | Search by query |
| DELETE | `/api/v1/rag/<id>/delete/` | Delete chunk |

### Costs
| Method | URL | Description |
|---|---|---|
| GET | `/api/v1/costs/list/` | List cost records |
| GET | `/api/v1/costs/summary/` | Aggregated totals |

### Agent Tools
| Method | URL | Description |
|---|---|---|
| GET | `/api/v1/agent/tools/list/` | List available tools |
| POST | `/api/v1/agent/tools/run/` | Run a tool |

**Built-in tools:** `calculator`, `web_fetch`, `web_search`, `get_time`, `read_file`, `write_file`

### Webhooks
| Method | URL | Description |
|---|---|---|
| POST | `/api/v1/webhooks/token/create/` | Generate webhook token |
| POST | `/api/v1/webhooks/receive/` | Receive prompt via webhook |

---

## 🤖 Built-in Personas

| Key | Name | Temperature |
|---|---|---|
| `tech_oracle` | Tech Oracle | 0.3 |
| `socratic` | Socratic Guide | 0.8 |
| `creative_muse` | Creative Muse | 1.0 |
| `devil_advocate` | Devil's Advocate | 0.9 |
| `eli5` | ELI5 Explainer | 0.7 |
| `mentor` | Wise Mentor | 0.5 |
| `researcher` | Deep Researcher | 0.4 |
| `comedian` | Comedian | 1.0 |

---

## 🛠️ Local Setup

### 1. Clone and install
```bash
git clone https://github.com/istrebitel0007000-web/oracle-brain.git
cd oracle-brain
pip install -r requirements.txt
```

### 2. Configure environment
```bash
cp .env.template .env
# Edit .env and fill in your values
```

### 3. Set up PostgreSQL
```bash
createdb oracle_brain
```

### 4. Run migrations and seed
```bash
python manage.py migrate
python manage.py seed_personas
```

### 5. Run the server
```bash
python manage.py runserver
```

---

## 🧪 Running Tests

```bash
python manage.py test tests
```

All 44 tests pass across 9 apps — auth, chat, notes, bookmarks, rag, costs, personas, agent, webhooks.

---

## ☁️ Deploy to Render

This repo includes a `render.yaml` for one-click deployment.

1. Push to GitHub
2. Go to [render.com](https://render.com) → **New** → **Blueprint**
3. Connect your `oracle-brain` repo
4. Render auto-detects `render.yaml` and creates:
   - Web service (Django + Gunicorn)
   - PostgreSQL database (free tier)
5. Add your environment variables in Render dashboard:
   - `GROQ_KEY_1`, `GROQ_KEY_2`, `GROQ_KEY_3`
   - Any other vars from `.env.template`

---

## 🔐 Authentication

All endpoints (except register, login, and webhook receive) require a token:

```http
Authorization: Token your-token-here
```

Get your token by calling `/api/v1/auth/login/`.

---

## 🧰 Supported AI Models

| Model | Use |
|---|---|
| `deepseek-r1-distill-llama-70b` | Default — best reasoning |
| `qwen-2.5-72b-instruct` | Fallback 1 |
| `llama-3.3-70b-versatile` | Fallback 2 |
| `llama-3.1-8b-instant` | Fallback 3 — fastest |
| `gemma2-9b-it` | Fallback 4 |
| `meta-llama/llama-4-scout-17b-16e-instruct` | Vision tasks |

Oracle Brain automatically rotates through Groq API keys and falls back through models on rate limits or errors.

---

## 📐 Code Standards

This project follows 3 strict coding standards:

- **`docs/code_of_conduct`** — URL naming, app structure, serializer/service/view/model rules
- **`docs/tests_guide`** — test independence, fixtures, mocking external calls only
- **`docs/layers_guide`** — views handle HTTP only, serializers validate only, all logic in services

---

## 📄 License

MIT
