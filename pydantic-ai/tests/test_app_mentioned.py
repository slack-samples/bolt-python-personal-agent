import logging
from unittest.mock import AsyncMock, Mock, patch

import pytest
from pydantic_ai.messages import ModelRequest, UserPromptPart
from slack_bolt import BoltContext
from slack_sdk import WebClient

from agent.agent import AgentResult
from listeners.events.app_mentioned import handle_app_mentioned
from thread_context.store import ConversationStore

test_logger = logging.getLogger(__name__)


@pytest.fixture(autouse=True)
def fresh_store():
    store = ConversationStore()
    with patch("listeners.events.app_mentioned.conversation_store", store):
        yield store


@patch("listeners.events.app_mentioned.run_agent", new_callable=AsyncMock)
def test_mention_runs_the_agent_without_a_user_token(run_agent):
    context = Mock(BoltContext)
    context.channel_id = "C123"
    context.user_id = "U123"
    context.user_token = None
    run_agent.return_value = AgentResult("Here's the runbook.", [], [])
    say_stream = Mock()

    handle_app_mentioned(
        client=Mock(WebClient),
        context=context,
        event={
            "text": "<@B123> is there a runbook for deploys?",
            "ts": "1700000000.000100",
        },
        logger=test_logger,
        say=Mock(),
        say_stream=say_stream,
        set_status=Mock(),
    )

    agent_input, deps = run_agent.call_args.args
    assert agent_input == "is there a runbook for deploys?"
    assert run_agent.call_args.kwargs["message_history"] is None
    assert deps.user_token is None
    say_stream.return_value.append.assert_called_once_with(
        markdown_text="Here's the runbook."
    )


@patch("listeners.events.app_mentioned.run_agent", new_callable=AsyncMock)
def test_owner_mention_in_channel_uses_no_token(run_agent, monkeypatch):
    monkeypatch.setenv("OWNER_USER_ID", "U123")
    context = Mock(BoltContext)
    context.channel_id = "C123"
    context.user_id = "U123"
    context.user_token = "xoxp-123"
    run_agent.return_value = AgentResult("Here's the runbook.", [], [])

    handle_app_mentioned(
        client=Mock(WebClient),
        context=context,
        event={"text": "<@B123> summarize", "ts": "1700000000.000100"},
        logger=test_logger,
        say=Mock(),
        say_stream=Mock(),
        set_status=Mock(),
    )

    _, deps = run_agent.call_args.args
    assert deps.is_owner is True
    assert deps.user_token is None
    assert deps.is_private_reply is False


def mention_context(user_id):
    context = Mock(BoltContext)
    context.channel_id = "C123"
    context.user_id = user_id
    context.user_token = None
    return context


def mention(context, text="<@B123> any update?"):
    handle_app_mentioned(
        client=Mock(WebClient),
        context=context,
        event={"text": text, "thread_ts": "t1", "ts": "t2"},
        logger=test_logger,
        say=Mock(),
        say_stream=Mock(),
        set_status=Mock(),
    )


@patch("listeners.events.app_mentioned.run_agent", new_callable=AsyncMock)
def test_mention_resumes_only_the_requesters_history(run_agent, fresh_store):
    owner_history = [ModelRequest(parts=[UserPromptPart(content="owner secret")])]
    fresh_store.set_history("C123", "t1", "U0WNER", owner_history)
    guest_messages = [ModelRequest(parts=[UserPromptPart(content="any update?")])]
    run_agent.return_value = AgentResult("Not yet.", guest_messages, [])

    mention(mention_context("U0GUEST"))

    assert run_agent.call_args.kwargs["message_history"] is None
    assert fresh_store.get_history("C123", "t1", "U0GUEST") == guest_messages
    assert fresh_store.get_history("C123", "t1", "U0WNER") == owner_history

    mention(mention_context("U0GUEST"), text="<@B123> and now?")

    assert run_agent.call_args.kwargs["message_history"] == guest_messages


@patch("listeners.events.app_mentioned.run_agent", new_callable=AsyncMock)
def test_mention_from_a_bot_is_ignored(run_agent):
    say = Mock()
    say_stream = Mock()

    handle_app_mentioned(
        client=Mock(WebClient),
        context=Mock(BoltContext),
        event={
            "bot_id": "B456",
            "text": "<@B123> can you check this?",
            "ts": "1700000000.000100",
        },
        logger=test_logger,
        say=say,
        say_stream=say_stream,
        set_status=Mock(),
    )

    run_agent.assert_not_called()
    say.assert_not_called()
    say_stream.assert_not_called()
