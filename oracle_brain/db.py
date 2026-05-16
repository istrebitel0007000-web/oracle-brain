"""
oracle_brain/db.py — PostgreSQL + Redis persistence layer
Falls back gracefully to JSON files if DB is not configured.
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any, Optional

log = logging.getLogger("oracle.db")

try:
    import psycopg2
    import psycopg2.extras
    _PG_AVAILABLE = True
except ImportError:
    _PG_AVAILABLE = False

try:
    import redis as redis_lib
    _REDIS_AVAILABLE = True
except ImportError:
    _REDIS_AVAILABLE = False


class PostgresDB:
    def __init__(self, url: str) -> None:
        self._url = url
        self._conn: Any = None
        self._connect()
        self._bootstrap()

    def _connect(self) -> None:
        if not _PG_AVAILABLE:
            raise RuntimeError("psycopg2 is not installed.")
        self._conn = psycopg2.connect(self._url)
        self._conn.autocommit = False

    def _cursor(self):
        try:
            self._conn.isolation_level
        except Exception:
            self._connect()
        return self._conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    def _bootstrap(self) -> None:
        ddl = """
        CREATE TABLE IF NOT EXISTS users (
            id          SERIAL PRIMARY KEY,
            email       TEXT UNIQUE NOT NULL,
            name        TEXT,
            picture     TEXT,
            role        TEXT DEFAULT 'user',
            created_at  TIMESTAMPTZ DEFAULT NOW(),
            last_seen   TIMESTAMPTZ DEFAULT NOW()
        );
        CREATE TABLE IF NOT EXISTS user_state (
            user_email  TEXT PRIMARY KEY REFERENCES users(email) ON DELETE CASCADE,
            state_json  JSONB NOT NULL DEFAULT '{}',
            updated_at  TIMESTAMPTZ DEFAULT NOW()
        );
        CREATE TABLE IF NOT EXISTS conversations (
            id          SERIAL PRIMARY KEY,
            user_email  TEXT REFERENCES users(email) ON DELETE CASCADE,
            title       TEXT,
            messages    JSONB NOT NULL DEFAULT '[]',
            created_at  TIMESTAMPTZ DEFAULT NOW(),
            updated_at  TIMESTAMPTZ DEFAULT NOW()
        );
        CREATE TABLE IF NOT EXISTS uploads (
            id          SERIAL PRIMARY KEY,
            user_email  TEXT REFERENCES users(email) ON DELETE CASCADE,
            filename    TEXT NOT NULL,
            filepath    TEXT NOT NULL,
            filetype    TEXT,
            size_bytes  INTEGER,
            extracted   TEXT,
            created_at  TIMESTAMPTZ DEFAULT NOW()
        );
        CREATE TABLE IF NOT EXISTS audit_log (
            id          SERIAL PRIMARY KEY,
            user_email  TEXT,
            action      TEXT NOT NULL,
            detail      JSONB,
            created_at  TIMESTAMPTZ DEFAULT NOW()
        );
        CREATE TABLE IF NOT EXISTS costs (
            id          SERIAL PRIMARY KEY,
            user_email  TEXT,
            model       TEXT,
            tokens_in   INTEGER DEFAULT 0,
            tokens_out  INTEGER DEFAULT 0,
            cost_usd    FLOAT DEFAULT 0,
            created_at  TIMESTAMPTZ DEFAULT NOW()
        );
        """
        with self._cursor() as cur:
            cur.execute(ddl)
        self._conn.commit()

    def upsert_user(self, email: str, name: str = "", picture: str = "", role: str = "user") -> dict:
        sql = """
        INSERT INTO users (email, name, picture, role, last_seen)
        VALUES (%s, %s, %s, %s, NOW())
        ON CONFLICT (email) DO UPDATE
            SET name = EXCLUDED.name, picture = EXCLUDED.picture, last_seen = NOW()
        RETURNING *
        """
        with self._cursor() as cur:
            cur.execute(sql, (email, name, picture, role))
            row = dict(cur.fetchone())
        self._conn.commit()
        return row

    def get_user(self, email: str) -> Optional[dict]:
        with self._cursor() as cur:
            cur.execute("SELECT * FROM users WHERE email = %s", (email,))
            row = cur.fetchone()
        return dict(row) if row else None

    def list_users(self) -> list[dict]:
        with self._cursor() as cur:
            cur.execute("SELECT * FROM users ORDER BY last_seen DESC")
            return [dict(r) for r in cur.fetchall()]

    def set_user_role(self, email: str, role: str) -> None:
        with self._cursor() as cur:
            cur.execute("UPDATE users SET role = %s WHERE email = %s", (role, email))
        self._conn.commit()

    def save_user_state(self, email: str, state_dict: dict) -> None:
        sql = """
        INSERT INTO user_state (user_email, state_json, updated_at)
        VALUES (%s, %s, NOW())
        ON CONFLICT (user_email) DO UPDATE
            SET state_json = EXCLUDED.state_json, updated_at = NOW()
        """
        with self._cursor() as cur:
            cur.execute(sql, (email, json.dumps(state_dict)))
        self._conn.commit()

    def load_user_state(self, email: str) -> Optional[dict]:
        with self._cursor() as cur:
            cur.execute("SELECT state_json FROM user_state WHERE user_email = %s", (email,))
            row = cur.fetchone()
        return dict(row["state_json"]) if row else None

    def save_conversation(self, email: str, messages: list, title: str = "", conv_id: Optional[int] = None) -> int:
        if conv_id:
            sql = "UPDATE conversations SET messages = %s, title = %s, updated_at = NOW() WHERE id = %s AND user_email = %s"
            with self._cursor() as cur:
                cur.execute(sql, (json.dumps(messages), title, conv_id, email))
            self._conn.commit()
            return conv_id
        sql = "INSERT INTO conversations (user_email, title, messages) VALUES (%s, %s, %s) RETURNING id"
        with self._cursor() as cur:
            cur.execute(sql, (email, title, json.dumps(messages)))
            new_id = cur.fetchone()["id"]
        self._conn.commit()
        return new_id

    def list_conversations(self, email: str) -> list[dict]:
        with self._cursor() as cur:
            cur.execute(
                "SELECT id, title, created_at, updated_at FROM conversations WHERE user_email = %s ORDER BY updated_at DESC",
                (email,)
            )
            return [dict(r) for r in cur.fetchall()]

    def get_conversation(self, conv_id: int, email: str) -> Optional[dict]:
        with self._cursor() as cur:
            cur.execute("SELECT * FROM conversations WHERE id = %s AND user_email = %s", (conv_id, email))
            row = cur.fetchone()
        return dict(row) if row else None

    def delete_conversation(self, conv_id: int, email: str) -> None:
        with self._cursor() as cur:
            cur.execute("DELETE FROM conversations WHERE id = %s AND user_email = %s", (conv_id, email))
        self._conn.commit()

    def save_upload(self, email: str, filename: str, filepath: str,
                    filetype: str, size_bytes: int, extracted: str = "") -> int:
        sql = "INSERT INTO uploads (user_email, filename, filepath, filetype, size_bytes, extracted) VALUES (%s,%s,%s,%s,%s,%s) RETURNING id"
        with self._cursor() as cur:
            cur.execute(sql, (email, filename, filepath, filetype, size_bytes, extracted))
            new_id = cur.fetchone()["id"]
        self._conn.commit()
        return new_id

    def list_uploads(self, email: str) -> list[dict]:
        with self._cursor() as cur:
            cur.execute(
                "SELECT id, filename, filetype, size_bytes, created_at FROM uploads WHERE user_email = %s ORDER BY created_at DESC",
                (email,)
            )
            return [dict(r) for r in cur.fetchall()]

    def log_cost(self, email: str, model: str, tokens_in: int, tokens_out: int, cost_usd: float) -> None:
        sql = "INSERT INTO costs (user_email, model, tokens_in, tokens_out, cost_usd) VALUES (%s,%s,%s,%s,%s)"
        with self._cursor() as cur:
            cur.execute(sql, (email, model, tokens_in, tokens_out, cost_usd))
        self._conn.commit()

    def get_cost_summary(self) -> list[dict]:
        sql = """
        SELECT user_email,
               SUM(tokens_in) AS total_tokens_in,
               SUM(tokens_out) AS total_tokens_out,
               SUM(cost_usd) AS total_cost_usd,
               COUNT(*) AS total_requests
        FROM costs GROUP BY user_email ORDER BY total_cost_usd DESC
        """
        with self._cursor() as cur:
            cur.execute(sql)
            return [dict(r) for r in cur.fetchall()]

    def get_cost_today(self, email: str) -> float:
        sql = "SELECT COALESCE(SUM(cost_usd),0) AS today FROM costs WHERE user_email=%s AND created_at::date=CURRENT_DATE"
        with self._cursor() as cur:
            cur.execute(sql, (email,))
            row = cur.fetchone()
        return float(row["today"]) if row else 0.0

    def log_audit(self, email: str, action: str, detail: Optional[dict] = None) -> None:
        sql = "INSERT INTO audit_log (user_email, action, detail) VALUES (%s,%s,%s)"
        with self._cursor() as cur:
            cur.execute(sql, (email, action, json.dumps(detail or {})))
        self._conn.commit()

    def get_audit_log(self, limit: int = 100) -> list[dict]:
        with self._cursor() as cur:
            cur.execute("SELECT * FROM audit_log ORDER BY created_at DESC LIMIT %s", (limit,))
            return [dict(r) for r in cur.fetchall()]

    def get_admin_stats(self) -> dict:
        with self._cursor() as cur:
            cur.execute("SELECT COUNT(*) AS cnt FROM users")
            total_users = cur.fetchone()["cnt"]
            cur.execute("SELECT COUNT(*) AS cnt FROM costs")
            total_requests = cur.fetchone()["cnt"]
            cur.execute("SELECT COALESCE(SUM(cost_usd),0) AS total FROM costs")
            total_cost = float(cur.fetchone()["total"])
            cur.execute("SELECT COUNT(DISTINCT user_email) AS cnt FROM costs WHERE created_at > NOW() - INTERVAL '24 hours'")
            active_24h = cur.fetchone()["cnt"]
        return {
            "total_users": total_users,
            "total_requests": total_requests,
            "total_cost_usd": round(total_cost, 4),
            "active_users_24h": active_24h,
        }


class RedisCache:
    def __init__(self, url: str, default_ttl: int = 3600) -> None:
        if not _REDIS_AVAILABLE:
            raise RuntimeError("redis not installed.")
        self._client = redis_lib.from_url(url, decode_responses=True)
        self._default_ttl = default_ttl
        self._client.ping()

    def get(self, key: str) -> Optional[str]:
        try:
            return self._client.get(key)
        except Exception as e:
            log.warning(f"Redis get error: {e}")
            return None

    def set(self, key: str, value: str, ttl: Optional[int] = None) -> None:
        try:
            self._client.set(key, value, ex=ttl or self._default_ttl)
        except Exception as e:
            log.warning(f"Redis set error: {e}")

    def delete(self, key: str) -> None:
        try:
            self._client.delete(key)
        except Exception as e:
            log.warning(f"Redis delete error: {e}")

    def get_json(self, key: str) -> Optional[Any]:
        raw = self.get(key)
        return json.loads(raw) if raw else None

    def set_json(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        self.set(key, json.dumps(value, ensure_ascii=False), ttl)

    def incr(self, key: str, ttl: Optional[int] = None) -> int:
        try:
            val = self._client.incr(key)
            if ttl and val == 1:
                self._client.expire(key, ttl)
            return val
        except Exception as e:
            log.warning(f"Redis incr error: {e}")
            return 0

    def rate_check(self, key: str, limit: int, window: int) -> tuple[bool, int]:
        count = self.incr(key, window)
        return count <= limit, count


_pg: Optional[PostgresDB] = None
_redis: Optional[RedisCache] = None


def init_db(postgres_url: str = "", redis_url: str = "") -> None:
    global _pg, _redis
    pg_url = postgres_url or os.getenv("DATABASE_URL", "")
    r_url = redis_url or os.getenv("REDIS_URL", "")
    if pg_url and _PG_AVAILABLE:
        try:
            _pg = PostgresDB(pg_url)
            log.info("PostgreSQL connected.")
        except Exception as e:
            log.error(f"PostgreSQL init failed: {e}")
    if r_url and _REDIS_AVAILABLE:
        try:
            _redis = RedisCache(r_url)
            log.info("Redis connected.")
        except Exception as e:
            log.error(f"Redis init failed: {e}")


def get_db() -> Optional[PostgresDB]:
    return _pg


def get_redis() -> Optional[RedisCache]:
    return _redis


def db_available() -> bool:
    return _pg is not None


def redis_available() -> bool:
    return _redis is not None
