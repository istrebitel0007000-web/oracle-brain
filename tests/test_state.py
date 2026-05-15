"""tests/test_state.py — State module tests"""
import sys, threading
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


def test_state_singleton():
    from oracle_brain.state import state, OracleState
    assert isinstance(state, OracleState)


def test_history_append_and_get():
    from oracle_brain.state import OracleState
    s = OracleState()
    s.append_history({"role": "user", "content": "Hello"})
    s.append_history({"role": "assistant", "content": "Hi"})
    h = s.get_history()
    assert len(h) == 2 and h[0]["role"] == "user"


def test_history_clear():
    from oracle_brain.state import OracleState
    s = OracleState()
    s.append_history({"role": "user", "content": "test"})
    s.clear_history()
    assert s.get_history() == []


def test_trim_history():
    from oracle_brain.state import OracleState
    s = OracleState()
    for i in range(50):
        s.append_history({"role": "user", "content": f"msg {i}"})
        s.append_history({"role": "assistant", "content": f"reply {i}"})
    s.trim_history(max_turns=10)
    assert len(s.get_history()) == 20


def test_latency_bounded_to_50():
    from oracle_brain.state import OracleState
    s = OracleState()
    for i in range(200):
        s.add_latency(float(i))
    assert len(s.latency_samples) == 50, "FIX #7: latency deque must be bounded to 50"


def test_inc_stat():
    from oracle_brain.state import OracleState
    s = OracleState()
    s.inc_stat("total_requests")
    s.inc_stat("total_requests", 4)
    assert s.get_stats_snapshot()["total_requests"] == 5


def test_notes_and_bookmarks_tracked():
    from oracle_brain.state import OracleState
    s = OracleState()
    s.add_note({"content": "n1"})
    s.add_note({"content": "n2"})
    s.add_bookmark({"message": "bm1"})
    assert len(s.get_notes()) == 2
    assert len(s.get_bookmarks()) == 1
    snap = s.get_stats_snapshot()
    assert snap["notes_saved"] == 2
    assert snap["bookmarks_saved"] == 1


def test_per_user_state_isolated():
    from oracle_brain.state import OracleState
    s = OracleState()
    u1 = s.get_user_state("alice@test.com")
    u2 = s.get_user_state("bob@test.com")
    u1.append_history({"role": "user", "content": "Alice"})
    assert len(u1.get_history()) == 1
    assert len(u2.get_history()) == 0


def test_per_user_state_same_ref():
    from oracle_brain.state import OracleState
    s = OracleState()
    u1a = s.get_user_state("alice@test.com")
    u1b = s.get_user_state("alice@test.com")
    assert u1a is u1b


def test_thread_safety():
    from oracle_brain.state import OracleState
    s = OracleState()
    errors = []
    def writer():
        try:
            for i in range(100):
                s.append_history({"role": "user", "content": f"msg {i}"})
                s.inc_stat("total_requests")
        except Exception as e:
            errors.append(e)
    threads = [threading.Thread(target=writer) for _ in range(10)]
    for t in threads: t.start()
    for t in threads: t.join()
    assert errors == [], f"Thread safety errors: {errors}"
    assert len(s.get_history()) == 1000


def test_user_state_serialization():
    from oracle_brain.state import OracleUserState
    u = OracleUserState("test@test.com")
    u.append_history({"role": "user", "content": "hello"})
    u.active_persona = "pirate"
    u.tokens_in = 500
    d = u.to_dict()
    assert d["user_id"] == "test@test.com"
    assert d["active_persona"] == "pirate"
    assert d["tokens_in"] == 500
    assert len(d["history"]) == 1
    u2 = OracleUserState("test@test.com")
    u2.from_dict(d)
    assert u2.active_persona == "pirate"
    assert len(u2.get_history()) == 1
