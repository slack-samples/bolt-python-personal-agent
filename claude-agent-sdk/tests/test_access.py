from agent.access import is_owner, owner_user_id, reply_user_token


def test_is_owner_matches_owner_user_id(monkeypatch):
    monkeypatch.setenv("OWNER_USER_ID", "U0WNER")
    assert is_owner("U0WNER") is True
    assert is_owner("U0THER") is False


def test_no_owner_when_env_unset(monkeypatch):
    monkeypatch.delenv("OWNER_USER_ID", raising=False)
    assert owner_user_id() is None
    assert is_owner("U0WNER") is False
    assert is_owner(None) is False


def test_no_owner_when_env_empty(monkeypatch):
    monkeypatch.setenv("OWNER_USER_ID", "")
    assert owner_user_id() is None


def test_reply_user_token_only_for_private_replies():
    assert reply_user_token("xoxp-1", True) == "xoxp-1"
    assert reply_user_token("xoxp-1", False) is None
    assert reply_user_token(None, True) is None
