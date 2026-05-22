"""
Oracle Brain — Django Settings
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "change-me-in-production")
DEBUG = os.getenv("DEBUG", "False") == "True"
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "*").split(",")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "apps.core",
    "apps.chat",
    "apps.notes",
    "apps.bookmarks",
    "apps.personas",
    "apps.rag",
    "apps.agent",
    "apps.costs",
    "apps.webhooks",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# PostgreSQL — supports DATABASE_URL (Render) or individual env vars
_DATABASE_URL = os.getenv("DATABASE_URL")
if _DATABASE_URL:
    import dj_database_url
    DATABASES = {"default": dj_database_url.parse(_DATABASE_URL, conn_max_age=600)}
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("DB_NAME", "oracle_brain"),
            "USER": os.getenv("DB_USER", "postgres"),
            "PASSWORD": os.getenv("DB_PASSWORD", ""),
            "HOST": os.getenv("DB_HOST", "localhost"),
            "PORT": os.getenv("DB_PORT", "5432"),
        }
    }

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.TokenAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "100/hour",
        "user": "1000/hour",
    },
}

# Groq
GROQ_KEYS = [
    k for k in [
        os.getenv("GROQ_KEY_1", ""),
        os.getenv("GROQ_KEY_2", ""),
        os.getenv("GROQ_KEY_3", ""),
    ] if k and not k.startswith("YOUR_KEY")
]
GROQ_DEFAULT_MODEL = os.getenv("GROQ_MODEL", "deepseek-r1-distill-llama-70b")
GROQ_VISION_MODEL = os.getenv("GROQ_VISION_MODEL", "meta-llama/llama-4-scout-17b-16e-instruct")
GROQ_FALLBACK_MODELS = [
    "qwen-2.5-72b-instruct",
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "gemma2-9b-it",
]

# Oracle Brain
ORACLE_MAX_TOKENS = int(os.getenv("ORACLE_MAX_TOKENS", "4096"))
ORACLE_TEMPERATURE = float(os.getenv("ORACLE_TEMPERATURE", "0.7"))
ORACLE_MAX_HISTORY_TURNS = int(os.getenv("ORACLE_MAX_HISTORY_TURNS", "20"))
ORACLE_MAX_PROMPT_LEN = int(os.getenv("ORACLE_MAX_PROMPT_LEN", "8000"))
ORACLE_MAX_RETRIES = int(os.getenv("ORACLE_MAX_RETRIES", "5"))
ORACLE_DAILY_BUDGET_USD = float(os.getenv("ORACLE_DAILY_BUDGET_USD", "0.0"))
ORACLE_BACKUP_DIR = os.getenv("ORACLE_BACKUP_DIR", "backups")
ORACLE_BACKUP_KEEP = int(os.getenv("ORACLE_BACKUP_KEEP", "30"))
BACKUP_PASSWORD = os.getenv("BACKUP_PASSWORD", "")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1")
WEBHOOK_TOKEN = os.getenv("WEB_HOOK_TOKEN", "")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TG_RATE_MAX = int(os.getenv("TG_RATE_MAX", "10"))
TG_RATE_WINDOW = int(os.getenv("TG_RATE_WINDOW", "60"))

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {"format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "verbose"},
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "oracle.log",
            "maxBytes": 10485760,
            "backupCount": 5,
            "formatter": "verbose",
            "encoding": "utf-8",
        },
    },
    "root": {"handlers": ["console", "file"], "level": "INFO"},
}

# ORACLE_CONFIG dict — convenience alias used by groq_client and send_message
ORACLE_CONFIG = {
    "model": GROQ_DEFAULT_MODEL,
    "vision_model": GROQ_VISION_MODEL,
    "fallback_models": GROQ_FALLBACK_MODELS,
    "max_tokens": ORACLE_MAX_TOKENS,
    "temperature": ORACLE_TEMPERATURE,
    "max_retries": ORACLE_MAX_RETRIES,
    "request_delay": 0.3,
    "max_prompt_len": ORACLE_MAX_PROMPT_LEN,
    "max_history_turns": ORACLE_MAX_HISTORY_TURNS,
    "ollama_url": OLLAMA_URL,
    "ollama_model": OLLAMA_MODEL,
    "ollama_enabled": bool(OLLAMA_URL and OLLAMA_MODEL),
    "daily_budget_usd": ORACLE_DAILY_BUDGET_USD,
}

# GROQ_API_KEYS alias for groq_client
GROQ_API_KEYS = GROQ_KEYS
