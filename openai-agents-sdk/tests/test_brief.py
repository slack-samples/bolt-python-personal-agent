import logging
from unittest.mock import AsyncMock, Mock, patch

from listeners.commands.brief import handle_brief

test_logger = logging.getLogger(__name__)


@patch("listeners.commands.brief.run_agent", new_callable=AsyncMock)
def test_brief_refused_for_non_owner(run_agent, monkeypatch):
    monkeypatch.setenv("OWNER_USER_ID", "U456")
    ack = Mock()
    command = {"user_id": "U123", "channel_id": "C123"}
    respond = Mock()

    handle_brief(
        ack=ack,
        command=command,
        client=Mock(),
        context=Mock(user_token=None),
        respond=respond,
        logger=test_logger,
    )

    ack.assert_called_once()
    run_agent.assert_not_called()
    respond.assert_called_once()
    assert "<@U456>" in respond.call_args.kwargs["text"]


@patch("listeners.commands.brief.run_agent", new_callable=AsyncMock)
def test_brief_asks_owner_to_connect(run_agent, monkeypatch):
    monkeypatch.setenv("OWNER_USER_ID", "U123")
    monkeypatch.setenv("SLACK_CLIENT_ID", "123.456")
    monkeypatch.setenv("SLACK_REDIRECT_URI", "https://example.com")
    ack = Mock()
    command = {"user_id": "U123", "channel_id": "C123"}
    context = Mock(user_token=None)
    respond = Mock()

    handle_brief(
        ack=ack,
        command=command,
        client=Mock(),
        context=context,
        respond=respond,
        logger=test_logger,
    )

    ack.assert_called_once()
    run_agent.assert_not_called()
    respond.assert_called_once()
    assert "/slack/install" in respond.call_args.kwargs["text"]


@patch("listeners.commands.brief.run_agent", new_callable=AsyncMock)
def test_brief_runs_privately_for_connected_owner(run_agent, monkeypatch):
    monkeypatch.setenv("OWNER_USER_ID", "U123")
    ack = Mock()
    command = {"user_id": "U123", "channel_id": "C123"}
    context = Mock(user_token="xoxp-1")
    respond = Mock()
    run_agent.return_value = Mock(final_output="Here's what needs attention")

    handle_brief(
        ack=ack,
        command=command,
        client=Mock(),
        context=context,
        respond=respond,
        logger=test_logger,
    )

    ack.assert_called_once()
    run_agent.assert_called_once()
    _, deps = run_agent.call_args.args
    assert deps.is_private_reply is True
    assert deps.user_token == "xoxp-1"
    assert deps.is_owner is True
    respond.assert_called_once_with(text="Here's what needs attention")


@patch("listeners.commands.brief.run_agent", new_callable=AsyncMock)
def test_brief_acks_before_running(run_agent, monkeypatch):
    monkeypatch.setenv("OWNER_USER_ID", "U123")
    ack = Mock()
    command = {"user_id": "U123", "channel_id": "C123"}
    context = Mock(user_token="xoxp-1")
    respond = Mock()
    run_agent.side_effect = Exception("Agent error")

    handle_brief(
        ack=ack,
        command=command,
        client=Mock(),
        context=context,
        respond=respond,
        logger=test_logger,
    )

    ack.assert_called_once()
    respond.assert_called_once()
    assert ":warning:" in respond.call_args.kwargs["text"]
