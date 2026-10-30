from unittest.mock import Mock

import pytest
from slack_sdk import WebClient

from agent.deps import AgentDeps
from agent.soul import is_template, load_soul, save_soul
from agent.tools.soul import update_soul
from tests.helpers import invoke


@pytest.fixture
def soul_path(tmp_path, monkeypatch):
    path = tmp_path / "soul.md"
    import agent.tools.soul

    monkeypatch.setattr(agent.tools.soul, "SOUL_PATH", path)
    return path


@pytest.fixture
def deps():
    client = Mock(WebClient)
    return AgentDeps(
        client=client,
        user_id="U123",
        channel_id="C123",
        thread_ts="1700000000.000100",
        message_ts="1700000000.000100",
    )


def test_load_soul_falls_back_to_template_when_missing(tmp_path):
    nonexistent = tmp_path / "soul.md"
    result = load_soul(nonexistent)
    assert "## Goals" in result
    assert is_template(result)


def test_load_soul_falls_back_when_unreadable(tmp_path):
    directory_path = tmp_path / "soul.md"
    directory_path.mkdir()
    result = load_soul(directory_path)
    assert "## Goals" in result
    assert is_template(result)


def test_save_then_load_round_trips(tmp_path):
    path = tmp_path / "soul.md"
    content = "# Soul\n## Goals\nShip it"
    save_soul(content, path)
    result = load_soul(path)
    assert result == content
    assert not is_template(result)


def test_update_soul_refused_for_non_owner(soul_path, deps):
    deps.is_owner = False
    deps.is_private_reply = True
    result = invoke(update_soul, deps, markdown="# Soul\n## Goals\nTest")
    assert result == "Only the owner can change the soul, in a direct message."
    assert not soul_path.exists()


def test_update_soul_refused_in_channel(soul_path, deps):
    deps.is_owner = True
    deps.is_private_reply = False
    result = invoke(update_soul, deps, markdown="# Soul\n## Goals\nTest")
    assert result == "Only the owner can change the soul, in a direct message."
    assert not soul_path.exists()


def test_update_soul_rejects_empty_markdown(soul_path, deps):
    deps.is_owner = True
    deps.is_private_reply = True
    result = invoke(update_soul, deps, markdown="  ")
    assert result == "The soul can't be empty."
    assert not soul_path.exists()


def test_update_soul_writes_for_owner_in_dm(soul_path, deps):
    deps.is_owner = True
    deps.is_private_reply = True
    content = "# Soul\n## Goals\nShip it"
    result = invoke(update_soul, deps, markdown=content)
    assert result == "Saved your soul."
    assert soul_path.read_text() == content


def test_load_soul_falls_back_inline_when_template_unreadable(tmp_path, monkeypatch):
    import agent.soul

    monkeypatch.setattr(agent.soul, "TEMPLATE_PATH", tmp_path / "missing.md")
    result = load_soul(tmp_path / "soul.md")
    assert is_template(result)
    assert "## Goals" in result
