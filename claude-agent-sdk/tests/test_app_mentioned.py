import logging
from unittest.mock import AsyncMock, Mock, patch

import pytest
from slack_bolt.context.async_context import AsyncBoltContext
from slack_sdk.web.async_client import AsyncWebClient

from agent.agent import AgentResult
from listeners.events.app_mentioned import handle_app_mentioned
from thread_context.store import SessionStore

test_logger = logging.getLogger(__name__)


@pytest.fixture(autouse=True)
def fresh_store():
    store = SessionStore()
    with patch("listeners.events.app_mentioned.session_store", store):
        yield store


def make_streamer():
    streamer = Mock()
    streamer.append = AsyncMock()
    streamer.stop = AsyncMock()
    return streamer


async def mention(context, event, say_stream=None):
    await handle_app_mentioned(
        client=Mock(AsyncWebClient),
        context=context,
        event=event,
        logger=test_logger,
        say=AsyncMock(),
        say_stream=say_stream or AsyncMock(return_value=make_streamer()),
        set_status=AsyncMock(),
    )


@pytest.mark.asyncio
@patch("listeners.events.app_mentioned.run_agent", new_callable=AsyncMock)
async def test_mention_runs_the_agent_without_a_user_token(run_agent):
    context = Mock(AsyncBoltContext)
    context.channel_id = "C123"
    context.user_id = "U123"
    context.user_token = None
    run_agent.return_value = AgentResult("Here's the runbook.", "session-1", [])
    streamer = make_streamer()

    await mention(
        context,
        {
            "text": "<@B123> is there a runbook for deploys?",
            "ts": "1700000000.000100",
        },
        say_stream=AsyncMock(return_value=streamer),
    )

    agent_input, deps = run_agent.call_args.args
    assert agent_input == "is there a runbook for deploys?"
    assert deps.user_token is None
    streamer.append.assert_awaited_once_with(markdown_text="Here's the runbook.")


@pytest.mark.asyncio
@patch("listeners.events.app_mentioned.run_agent", new_callable=AsyncMock)
async def test_owner_mention_in_channel_uses_no_token(run_agent, monkeypatch):
    monkeypatch.setenv("OWNER_USER_ID", "U123")
    context = Mock(AsyncBoltContext)
    context.channel_id = "C123"
    context.user_id = "U123"
    context.user_token = "xoxp-123"
    run_agent.return_value = AgentResult("Here's the runbook.", "session-1", [])

    await mention(context, {"text": "<@B123> summarize", "ts": "1700000000.000100"})

    _, deps = run_agent.call_args.args
    assert deps.is_owner is True
    assert deps.user_token is None
    assert deps.is_private_reply is False


@pytest.mark.asyncio
@patch("listeners.events.app_mentioned.run_agent", new_callable=AsyncMock)
async def test_mention_resumes_only_the_requesters_session(run_agent, fresh_store):
    fresh_store.set_session("C123", "t1", "U0WNER", "owner-session")
    context = Mock(AsyncBoltContext)
    context.channel_id = "C123"
    context.user_id = "U123"
    context.user_token = None
    run_agent.return_value = AgentResult("Here's the runbook.", "guest-session", [])

    await mention(
        context, {"text": "<@B123> any update?", "thread_ts": "t1", "ts": "t2"}
    )

    assert run_agent.call_args.kwargs["session_id"] is None
    assert fresh_store.get_session("C123", "t1", "U123") == "guest-session"
    assert fresh_store.get_session("C123", "t1", "U0WNER") == "owner-session"
