import time

from pydantic_ai.messages import ModelRequest, UserPromptPart

from thread_context.store import ConversationStore


def test_history_is_separate_per_user():
    store = ConversationStore()
    messages = [ModelRequest(parts=[UserPromptPart(content="hello")])]

    store.set_history("C1", "t1", "U1", messages)

    assert store.get_history("C1", "t1", "U2") is None
    assert store.get_history("C1", "t1", "U1") == messages


def test_has_thread_true_for_any_user():
    store = ConversationStore()
    messages = [ModelRequest(parts=[UserPromptPart(content="hello")])]

    store.set_history("C1", "t1", "U1", messages)

    assert store.has_thread("C1", "t1") is True
    assert store.has_thread("C1", "t2") is False


def test_expired_history_is_gone():
    store = ConversationStore(ttl_seconds=0)
    messages = [ModelRequest(parts=[UserPromptPart(content="hello")])]

    store.set_history("C1", "t1", "U1", messages)
    time.sleep(0.01)

    assert store.get_history("C1", "t1", "U1") is None
    assert store.has_thread("C1", "t1") is False


def test_max_conversations_drops_the_oldest():
    store = ConversationStore(max_conversations=1)

    store.set_history("C1", "t1", "U1", [])
    time.sleep(0.01)
    store.set_history("C1", "t2", "U1", [])

    assert store.get_history("C1", "t1", "U1") is None
    assert store.get_history("C1", "t2", "U1") == []
