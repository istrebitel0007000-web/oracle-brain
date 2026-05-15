"""oracle_brain/state.py — Thread-safe shared + per-user state"""
from __future__ import annotations
import threading
from collections import deque
from typing import Any


class OracleUserState:
    """Isolated per-user state (history, notes, bookmarks, settings)."""
    def __init__(self, user_id: str) -> None:
        self.user_id = user_id
        self._lock = threading.RLock()
        self.history: list[dict] = []
        self.notes: list[dict] = []
        self.bookmarks: list[dict] = []
        self.rag_chunks: list[dict] = []
        self.active_persona: str = "tech_oracle"
        self.response_length: str = "medium"
        self.active_project: str = ""
        self.sticky_lang: str = ""
        self.tokens_in: int = 0
        self.tokens_out: int = 0
        self.total_requests: int = 0
        self.role: str = "user"  # "user" | "admin"

    def append_history(self, entry: dict) -> None:
        with self._lock:
            self.history.append(entry)

    def get_history(self) -> list[dict]:
        with self._lock:
            return list(self.history)

    def clear_history(self) -> None:
        with self._lock:
            self.history.clear()

    def trim_history(self, max_turns: int) -> None:
        with self._lock:
            if len(self.history) > max_turns * 2:
                self.history = self.history[-(max_turns * 2):]

    def to_dict(self) -> dict:
        with self._lock:
            return {
                "user_id": self.user_id, "history": list(self.history),
                "notes": list(self.notes), "bookmarks": list(self.bookmarks),
                "active_persona": self.active_persona,
                "response_length": self.response_length,
                "active_project": self.active_project,
                "sticky_lang": self.sticky_lang,
                "tokens_in": self.tokens_in, "tokens_out": self.tokens_out,
                "total_requests": self.total_requests, "role": self.role,
            }

    def from_dict(self, data: dict) -> None:
        with self._lock:
            self.history = data.get("history", [])
            self.notes = data.get("notes", [])
            self.bookmarks = data.get("bookmarks", [])
            self.active_persona = data.get("active_persona", "tech_oracle")
            self.response_length = data.get("response_length", "medium")
            self.active_project = data.get("active_project", "")
            self.sticky_lang = data.get("sticky_lang", "")
            self.tokens_in = data.get("tokens_in", 0)
            self.tokens_out = data.get("tokens_out", 0)
            self.total_requests = data.get("total_requests", 0)
            self.role = data.get("role", "user")


class OracleState:
    """Global singleton — all shared runtime state with proper locking."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self.history: list[dict] = []
        self.notes: list[dict] = []
        self.bookmarks: list[dict] = []
        self.rag_chunks: list[dict] = []
        self.ratings: list[dict] = []
        self.projects: dict[str, Any] = {}
        self.audit_log: list[dict] = []
        self.costs: list[dict] = []
        self.macros: dict[str, str] = {}
        self.aliases: dict[str, str] = {}
        self.drafts: dict[str, str] = {}
        # FIX #7: bounded deque instead of unbounded list
        self.latency_samples: deque[float] = deque(maxlen=50)
        self.stats: dict[str, Any] = {
            "total_requests": 0, "cache_hits": 0, "quota_errors": 0,
            "server_errors": 0, "key_usage": {}, "model_fallbacks": 0,
            "optimized_prompts": 0, "invalid_responses": 0,
            "duplicate_hits": 0, "history_summaries": 0,
            "offline_hits": 0, "translations": 0, "mood_adjustments": 0,
            "code_files_saved": 0, "topics_tagged": 0, "templates_used": 0,
            "steps_run": 0, "notes_saved": 0, "bookmarks_saved": 0,
            "batch_questions": 0, "ratings_given": 0, "clarify_triggered": 0,
            "followups_asked": 0, "projects_switched": 0,
            "tokens_in": 0, "tokens_out": 0, "anthropic_calls": 0,
        }
        self._user_states: dict[str, OracleUserState] = {}

    # ── History ──────────────────────────────────────────────────────────────
    def append_history(self, entry: dict) -> None:
        with self._lock: self.history.append(entry)

    def get_history(self) -> list[dict]:
        with self._lock: return list(self.history)

    def clear_history(self) -> None:
        with self._lock: self.history.clear()

    def trim_history(self, max_turns: int) -> None:
        with self._lock:
            if len(self.history) > max_turns * 2:
                self.history = self.history[-(max_turns * 2):]

    # ── Notes ─────────────────────────────────────────────────────────────────
    def add_note(self, note: dict) -> None:
        with self._lock:
            self.notes.append(note)
            self.stats["notes_saved"] += 1

    def get_notes(self) -> list[dict]:
        with self._lock: return list(self.notes)

    # ── Bookmarks ─────────────────────────────────────────────────────────────
    def add_bookmark(self, bm: dict) -> None:
        with self._lock:
            self.bookmarks.append(bm)
            self.stats["bookmarks_saved"] += 1

    def get_bookmarks(self) -> list[dict]:
        with self._lock: return list(self.bookmarks)

    # ── RAG ───────────────────────────────────────────────────────────────────
    def add_rag_chunk(self, chunk: dict) -> None:
        with self._lock: self.rag_chunks.append(chunk)

    def get_rag_chunks(self) -> list[dict]:
        with self._lock: return list(self.rag_chunks)

    # ── Stats ─────────────────────────────────────────────────────────────────
    def inc_stat(self, key: str, amount: int = 1) -> None:
        with self._lock: self.stats[key] = self.stats.get(key, 0) + amount

    def add_latency(self, ms: float) -> None:
        with self._lock: self.latency_samples.append(ms)

    def avg_latency(self) -> float:
        with self._lock:
            samples = list(self.latency_samples)
            return sum(samples) / len(samples) if samples else 0.0

    def get_stats_snapshot(self) -> dict:
        with self._lock: return dict(self.stats)

    # ── Per-user ──────────────────────────────────────────────────────────────
    def get_user_state(self, user_id: str) -> OracleUserState:
        with self._lock:
            if user_id not in self._user_states:
                self._user_states[user_id] = OracleUserState(user_id)
            return self._user_states[user_id]

    def list_users(self) -> list[str]:
        with self._lock: return list(self._user_states.keys())

    def get_all_user_states(self) -> list[OracleUserState]:
        with self._lock: return list(self._user_states.values())


# Global singleton
state = OracleState()
