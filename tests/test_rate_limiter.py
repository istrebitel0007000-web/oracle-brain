"""tests/test_rate_limiter.py — Rate limiter (BUG #3 and #9 fix verification)"""
import os, sys, importlib
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture(autouse=True)
def mock_db():
    with patch("oracle_brain.rate_limiter.get_redis", return_value=None):
        yield


def _fresh(monkeypatch, rpm=10, rph=1000, rpd=10000, enabled=True):
    monkeypatch.setenv("RATE_PER_MINUTE", str(rpm))
    monkeypatch.setenv("RATE_PER_HOUR", str(rph))
    monkeypatch.setenv("RATE_PER_DAY", str(rpd))
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "true" if enabled else "false")
    import oracle_brain.rate_limiter as rl
    importlib.reload(rl)
    return rl


def test_config_cached_fix9(monkeypatch):
    """FIX #9: Config must be same object on repeated calls (cached)."""
    rl = _fresh(monkeypatch)
    assert rl.get_rate_config() is rl.get_rate_config()


def test_allows_within_limit(monkeypatch):
    rl = _fresh(monkeypatch, rpm=5)
    for _ in range(5):
        ok, reason, _ = rl.check_rate_limit("user1")
        assert ok and reason == ""


def test_blocks_after_per_minute_exceeded(monkeypatch):
    rl = _fresh(monkeypatch, rpm=3)
    for _ in range(3):
        ok, _, _ = rl.check_rate_limit("user2"); assert ok
    ok, reason, _ = rl.check_rate_limit("user2")
    assert not ok
    assert "min" in reason.lower()


def test_usage_keys_all_correct_fix3(monkeypatch):
    """FIX #3: per_minute, per_hour, per_day must each reflect their own window."""
    rl = _fresh(monkeypatch, rpm=100, rph=1000, rpd=10000)
    key = "user-fix3"
    for _ in range(5):
        rl.check_rate_limit(key)
    _, _, usage = rl.check_rate_limit(key)
    assert usage["per_minute"] > 0, "per_minute is 0 — BUG #3 not fixed"
    assert usage["per_hour"]   > 0, "per_hour is 0 — BUG #3 not fixed"
    assert usage["per_day"]    > 0, "per_day is 0 — BUG #3 not fixed"
    assert usage["limits"]["per_minute"] == 100
    assert usage["limits"]["per_hour"]   == 1000
    assert usage["limits"]["per_day"]    == 10000


def test_reset_restores_access(monkeypatch):
    rl = _fresh(monkeypatch, rpm=1)
    key = "user-reset"
    rl.check_rate_limit(key)
    ok, _, _ = rl.check_rate_limit(key); assert not ok
    rl.reset_user_limit(key)
    ok, _, _ = rl.check_rate_limit(key); assert ok


def test_user_isolation(monkeypatch):
    rl = _fresh(monkeypatch, rpm=1)
    rl.check_rate_limit("user-a")
    ok_b, _, _ = rl.check_rate_limit("user-b"); assert ok_b
    ok_a, _, _ = rl.check_rate_limit("user-a"); assert not ok_a


def test_disabled_always_allows(monkeypatch):
    rl = _fresh(monkeypatch, enabled=False)
    for _ in range(500):
        ok, _, _ = rl.check_rate_limit("any-user"); assert ok
