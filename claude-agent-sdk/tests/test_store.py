import time

from thread_context.store import SessionStore


def test_session_is_separate_per_user():
    store = SessionStore()

    store.set_session("C1", "t1", "U1", "session-1")

    assert store.get_session("C1", "t1", "U2") is None
    assert store.get_session("C1", "t1", "U1") == "session-1"


def test_has_thread_true_for_any_user():
    store = SessionStore()

    store.set_session("C1", "t1", "U1", "session-1")

    assert store.has_thread("C1", "t1") is True
    assert store.has_thread("C1", "t2") is False


def test_expired_session_is_gone():
    store = SessionStore(ttl_seconds=0)

    store.set_session("C1", "t1", "U1", "session-1")
    time.sleep(0.01)

    assert store.get_session("C1", "t1", "U1") is None
    assert store.has_thread("C1", "t1") is False


def test_oldest_sessions_are_dropped_over_the_limit():
    store = SessionStore(max_entries=1)

    store.set_session("C1", "t1", "U1", "session-1")
    time.sleep(0.01)
    store.set_session("C1", "t2", "U1", "session-2")

    assert store.get_session("C1", "t1", "U1") is None
    assert store.get_session("C1", "t2", "U1") == "session-2"
