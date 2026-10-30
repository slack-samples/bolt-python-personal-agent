import logging
from unittest.mock import AsyncMock, Mock, patch

import pytest

from agent.agent import AgentResult
from listeners.commands.brief import handle_brief
from listeners.install_url import connect_message

test_logger = logging.getLogger(__name__)


async def brief(command, context, respond, ack=None):
    await handle_brief(
        ack=ack or AsyncMock(),
        command=command,
        client=Mock(),
        context=context,
        respond=respond,
        logger=test_logger,
    )


@pytest.mark.asyncio
@patch("listeners.commands.brief.run_agent", new_callable=AsyncMock)
async def test_brief_refused_for_non_owner(run_agent, monkeypatch):
    monkeypatch.setenv("OWNER_USER_ID", "U456")
    ack = AsyncMock()
    respond = AsyncMock()

    await brief(
        {"user_id": "U123", "channel_id": "C123"},
        Mock(user_token=None),
        respond,
        ack=ack,
    )

    ack.assert_awaited_once()
    run_agent.assert_not_called()
    respond.assert_awaited_once()
    assert "<@U456>" in respond.call_args.kwargs["text"]


@pytest.mark.asyncio
@patch("listeners.commands.brief.run_agent", new_callable=AsyncMock)
async def test_brief_asks_owner_to_connect(run_agent, monkeypatch):
    monkeypatch.setenv("OWNER_USER_ID", "U123")
    monkeypatch.setenv("SLACK_CLIENT_ID", "123.456")
    monkeypatch.setenv("SLACK_REDIRECT_URI", "https://example.com")
    ack = AsyncMock()
    respond = AsyncMock()

    await brief(
        {"user_id": "U123", "channel_id": "C123"},
        Mock(user_token=None),
        respond,
        ack=ack,
    )

    ack.assert_awaited_once()
    run_agent.assert_not_called()
    respond.assert_awaited_once()
    assert "/slack/install" in respond.call_args.kwargs["text"]


@pytest.mark.asyncio
@patch("listeners.commands.brief.run_agent", new_callable=AsyncMock)
async def test_brief_runs_privately_for_connected_owner(run_agent, monkeypatch):
    monkeypatch.setenv("OWNER_USER_ID", "U123")
    ack = AsyncMock()
    respond = AsyncMock()
    run_agent.return_value = AgentResult("Here's what needs attention", "s1", [])

    await brief(
        {"user_id": "U123", "channel_id": "C123"},
        Mock(user_token="xoxp-1"),
        respond,
        ack=ack,
    )

    ack.assert_awaited_once()
    run_agent.assert_awaited_once()
    _, deps = run_agent.call_args.args
    assert deps.is_private_reply is True
    assert deps.user_token == "xoxp-1"
    assert deps.is_owner is True
    assert deps.is_brief is True
    assert deps.message_ts == ""
    assert respond.await_count == 2
    respond.assert_any_await("Putting your brief together…")
    respond.assert_awaited_with(text="Here's what needs attention")


@pytest.mark.asyncio
@patch("listeners.commands.brief.run_agent", new_callable=AsyncMock)
async def test_brief_acks_before_running(run_agent, monkeypatch):
    monkeypatch.setenv("OWNER_USER_ID", "U123")
    ack = AsyncMock()
    respond = AsyncMock()
    run_agent.side_effect = Exception("Agent error")

    await brief(
        {"user_id": "U123", "channel_id": "C123"},
        Mock(user_token="xoxp-1"),
        respond,
        ack=ack,
    )

    ack.assert_awaited_once()
    assert respond.await_count == 2
    respond.assert_any_await("Putting your brief together…")
    assert ":warning:" in respond.call_args.kwargs["text"]


@pytest.mark.asyncio
@patch("listeners.commands.brief.run_agent", new_callable=AsyncMock)
async def test_brief_points_to_readme_without_oauth(run_agent, monkeypatch):
    monkeypatch.setenv("OWNER_USER_ID", "U123")
    monkeypatch.delenv("SLACK_CLIENT_ID", raising=False)
    respond = AsyncMock()

    await brief(
        {"user_id": "U123", "channel_id": "C123"},
        Mock(user_token=None),
        respond,
    )

    run_agent.assert_not_called()
    assert respond.call_args.kwargs["text"] == connect_message()
    assert "README.md#slack-mcp-server" in respond.call_args.kwargs["text"]
