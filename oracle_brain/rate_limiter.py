"""
oracle_brain/rate_limiter.py — Fixed rate limiter
BUG #3 FIXED: usage dict reads correct key per window
BUG #9 FIXED: config cached at startup, not re-read on every request
"""
from __future__ import annotations

import logging
import os
import threading
import time
from collections import defaultdict
from typing import Optional

log = logging.getLogger("oracle.ratelimit")

# ── Config: built ONCE at startup (FIX #9) ───────────────────────────────────

_RATE_CFG: Optional[dict] = None


def _build_rate_config() -> dict:
    return {
        "per_minute": int(os.getenv("RATE_PER_MINUTE", "20")),
        "per_hour":   int(os.getenv("RATE_PER_HOUR",   "200")),
        "per_day":    int(os.getenv("RATE_PER_DAY",     "1000")),
        "enabled":    os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true",
    }


def get_rate_config() -> dict:
    """Return cached rate config (built once, not on every request — FIX #9)."""
    global _RATE_CFG
    if _RATE_CFG is None:
        _RATE_CFG = _build_rate_config()
    return _RATE_CFG


# ── Sliding window counters ───────────────────────────────────────────────────

class _Window:
    """Thread-safe sliding window counter."""
    def __init__(self, limit: int, period_s: int) -> None:
        self.limit = limit
        self.period = period_s
        self._lock = threading.Lock()
        self._windows: dict[str, list[float]] = defaultdict(list)

    def check_and_increment(self, key: str) -> tuple[bool, int]:
        now = time.time()
        cutoff = now - self.period
        with self._lock:
            self._windows[key] = [t for t in self._windows[key] if t > cutoff]
            count = len(self._windows[key])
            if count >= self.limit:
                return False, count
            self._windows[key].append(now)
            return True, count + 1

    def get_count(self, key: str) -> int:
        now = time.time()
        cutoff = now - self.period
        with self._lock:
            return len([t for t in self._windows.get(key, []) if t > cutoff])

    def reset(self, key: str) -> None:
        with self._lock:
            self._windows.pop(key, None)


_window_minute: Optional[_Window] = None
_window_hour:   Optional[_Window] = None
_window_day:    Optional[_Window] = None
_init_lock = threading.Lock()


def _ensure_windows() -> None:
    global _window_minute, _window_hour, _window_day
    if _window_minute is not None:
        return
    with _init_lock:
        if _window_minute is not None:
            return
        cfg = get_rate_config()
        _window_minute = _Window(cfg["per_minute"], 60)
        _window_hour   = _Window(cfg["per_hour"],   3600)
        _window_day    = _Window(cfg["per_day"],     86400)


# ── Public API ────────────────────────────────────────────────────────────────

def check_rate_limit(user_key: str) -> tuple[bool, str, dict]:
    """
    Returns (allowed, reason_if_denied, usage_dict).
    BUG #3 FIX: each window reads its own correct counter.
    """
    cfg = get_rate_config()
    if not cfg["enabled"]:
        return True, "", _empty_usage(cfg)

    # Try Redis first
    from oracle_brain.db import get_redis
    redis = get_redis()
    if redis:
        return _redis_rate_check(redis, user_key, cfg)

    # In-memory fallback
    _ensure_windows()

    ok_min, _ = _window_minute.check_and_increment(user_key)   # type: ignore
    ok_hr,  _ = _window_hour.check_and_increment(user_key)     # type: ignore
    ok_day, _ = _window_day.check_and_increment(user_key)      # type: ignore

    # BUG #3 FIX: each field reads from its OWN window instance
    usage = {
        "per_minute": _window_minute.get_count(user_key),  # type: ignore
        "per_hour":   _window_hour.get_count(user_key),    # type: ignore
        "per_day":    _window_day.get_count(user_key),     # type: ignore
        "limits": {
            "per_minute": cfg["per_minute"],
            "per_hour":   cfg["per_hour"],
            "per_day":    cfg["per_day"],
        },
    }

    if not ok_min:
        return False, f"Rate limit: {cfg['per_minute']}/min exceeded.", usage
    if not ok_hr:
        return False, f"Rate limit: {cfg['per_hour']}/hour exceeded.", usage
    if not ok_day:
        return False, f"Rate limit: {cfg['per_day']}/day exceeded.", usage

    return True, "", usage


def _redis_rate_check(redis, user_key: str, cfg: dict) -> tuple[bool, str, dict]:
    key_min = f"rl:{user_key}:min"
    key_hr  = f"rl:{user_key}:hr"
    key_day = f"rl:{user_key}:day"

    allowed_min, cnt_min = redis.rate_check(key_min, cfg["per_minute"], 60)
    allowed_hr,  cnt_hr  = redis.rate_check(key_hr,  cfg["per_hour"],   3600)
    allowed_day, cnt_day = redis.rate_check(key_day, cfg["per_day"],    86400)

    usage = {
        "per_minute": cnt_min,
        "per_hour":   cnt_hr,
        "per_day":    cnt_day,
        "limits": {
            "per_minute": cfg["per_minute"],
            "per_hour":   cfg["per_hour"],
            "per_day":    cfg["per_day"],
        },
    }

    if not allowed_min:
        return False, f"Rate limit: {cfg['per_minute']}/min exceeded.", usage
    if not allowed_hr:
        return False, f"Rate limit: {cfg['per_hour']}/hour exceeded.", usage
    if not allowed_day:
        return False, f"Rate limit: {cfg['per_day']}/day exceeded.", usage

    return True, "", usage


def reset_user_limit(user_key: str) -> None:
    """Admin: reset all windows for a user."""
    _ensure_windows()
    if _window_minute: _window_minute.reset(user_key)
    if _window_hour:   _window_hour.reset(user_key)
    if _window_day:    _window_day.reset(user_key)
    log.info(f"Rate limit reset for {user_key}")


def _empty_usage(cfg: Optional[dict] = None) -> dict:
    if cfg is None:
        cfg = get_rate_config()
    return {
        "per_minute": 0, "per_hour": 0, "per_day": 0,
        "limits": {
            "per_minute": cfg["per_minute"],
            "per_hour":   cfg["per_hour"],
            "per_day":    cfg["per_day"],
        },
    }
