import logging
from unittest.mock import AsyncMock, Mock, patch

import pytest
from slack_bolt.context.async_context import AsyncBoltContext
from slack_sdk.web.async_client import AsyncWebClient

from agent.agent import AgentResult
from listeners.events.message import handle_message
from thread_context.store import SessionStore

test_logger = logging.getLogger(__name__)

LEARNED = "Added the steps to [Runbook: Deploys](https://example.com)."


@pytest.fixture(autouse=True)
def fresh_store():
    store = SessionStore()
    with patch("listeners.events.message.session_store", store):
        yield store


def run_result(*tool_names):
    return AgentResult(LEARNED, "session-1", list(tool_names))


def make_streamer():
    streamer = Mock()
    streamer.append = AsyncMock()
    streamer.stop = AsyncMock()
    return streamer


class TestMessage:
    def setup_method(self):
        self.fake_client = Mock(AsyncWebClient)
        self.fake_client.chat_postEphemeral = AsyncMock()
        self.fake_context = Mock(AsyncBoltContext)
        self.fake_context.channel_id = "C123"
        self.fake_context.user_id = "U123"
        self.fake_context.user_token = "xoxp-123"
        self.fake_say = AsyncMock()

    async def handle(self, event):
        await handle_message(
            client=self.fake_client,
            context=self.fake_context,
            event=event,
            logger=test_logger,
            say=self.fake_say,
            say_stream=AsyncMock(return_value=make_streamer()),
            set_status=AsyncMock(),
        )

    @pytest.mark.asyncio
    @patch("listeners.events.message.run_agent", new_callable=AsyncMock)
    async def test_learns_with_bot_token_only(self, run_agent):
        run_agent.return_value = run_result("mcp__agent-tools__create_runbook")

        await self.handle(
            {
                "channel_type": "channel",
                "text": "Fixed it: rotate the signing secret, then redeploy",
                "thread_ts": "1700000000.000100",
                "ts": "1700000000.000200",
            }
        )

        learn_input, deps = run_agent.call_args.args
        assert learn_input.startswith("Learn from this channel message")
        assert "rotate the signing secret" in learn_input
        assert deps.user_id == "U123"
        assert deps.user_token is None
        assert deps.is_owner is False
        assert deps.is_private_reply is False
        kwargs = self.fake_client.chat_postEphemeral.call_args.kwargs
        assert kwargs["user"] == "U123"
        assert kwargs["thread_ts"] == "1700000000.000100"
        assert "Runbook: Deploys" in kwargs["markdown_text"]

    @pytest.mark.asyncio
    @patch("listeners.events.message.run_agent", new_callable=AsyncMock)
    async def test_learning_never_resumes_or_stores_a_session(
        self, run_agent, fresh_store
    ):
        fresh_store.set_session("C123", "t1", "U123", "reply-session")
        run_agent.return_value = run_result("mcp__agent-tools__create_runbook")

        await self.handle(
            {
                "channel_type": "channel",
                "subtype": "thread_broadcast",
                "text": "Fixed it",
                "thread_ts": "t1",
                "ts": "t2",
            }
        )

        run_agent.assert_awaited_once()
        assert "session_id" not in run_agent.call_args.kwargs
        assert run_agent.call_args.kwargs["persist_session"] is False
        assert fresh_store.get_session("C123", "t1", "U123") == "reply-session"

    @pytest.mark.asyncio
    @patch("listeners.events.message.run_agent", new_callable=AsyncMock)
    async def test_stays_quiet_when_no_runbook_changed(self, run_agent):
        run_agent.return_value = run_result("mcp__agent-tools__list_runbooks")

        await self.handle(
            {
                "channel_type": "group",
                "text": "Lunch at noon?",
                "ts": "1700000000.000100",
            }
        )

        run_agent.assert_called_once()
        self.fake_client.chat_postEphemeral.assert_not_called()

    @pytest.mark.asyncio
    @patch("listeners.events.message.run_agent", new_callable=AsyncMock)
    async def test_learns_from_broadcast_thread_replies(self, run_agent):
        run_agent.return_value = run_result()

        await self.handle(
            {
                "channel_type": "channel",
                "subtype": "thread_broadcast",
                "text": "Fixed: restarting the worker cleared the queue",
                "thread_ts": "1700000000.000100",
                "ts": "1700000000.000200",
            }
        )

        run_agent.assert_called_once()

    @pytest.mark.asyncio
    @patch("listeners.events.message.run_agent", new_callable=AsyncMock)
    async def test_logs_learning_errors(self, run_agent, caplog):
        run_agent.side_effect = Exception("test exception")

        await self.handle(
            {
                "channel_type": "channel",
                "text": "Fixed it: rotate the signing secret",
                "ts": "1700000000.000100",
            }
        )

        assert "test exception" in caplog.text

    @pytest.mark.asyncio
    @patch("listeners.events.message.run_agent", new_callable=AsyncMock)
    async def test_learns_with_the_bot_token_without_a_user_token(self, run_agent):
        self.fake_context.user_token = None
        run_agent.return_value = run_result("mcp__agent-tools__create_runbook")

        await self.handle(
            {
                "channel_type": "channel",
                "text": "Fixed it: rotate the signing secret",
                "ts": "1700000000.000100",
            }
        )

        _, deps = run_agent.call_args.args
        assert deps.user_token is None
        self.fake_client.chat_postEphemeral.assert_called_once()

    @pytest.mark.asyncio
    @patch("listeners.events.message.run_agent", new_callable=AsyncMock)
    async def test_does_not_learn_from_edits_or_bots(self, run_agent):
        await self.handle(
            {
                "channel_type": "channel",
                "subtype": "message_changed",
                "ts": "1700000000.000100",
            }
        )
        await self.handle(
            {
                "bot_id": "B123",
                "channel_type": "channel",
                "text": "Added the steps to the runbook.",
                "ts": "1700000000.000200",
            }
        )

        run_agent.assert_not_called()

    @pytest.mark.asyncio
    @patch("listeners.events.message.run_agent", new_callable=AsyncMock)
    async def test_does_not_learn_from_dms(self, run_agent):
        run_agent.return_value = run_result()

        await self.handle(
            {"channel_type": "im", "text": "Thanks!", "ts": "1700000000.000100"}
        )

        for call in run_agent.call_args_list:
            assert not str(call.args[0]).startswith("Learn from")

    @pytest.mark.asyncio
    @patch("listeners.events.message.run_agent", new_callable=AsyncMock)
    async def test_dm_uses_requesters_token_privately(self, run_agent, fresh_store):
        run_agent.return_value = run_result()

        await self.handle(
            {"channel_type": "im", "text": "What's new?", "ts": "1700000000.000100"}
        )

        _, deps = run_agent.call_args.args
        assert deps.user_token == "xoxp-123"
        assert deps.is_private_reply is True
        assert (
            fresh_store.get_session("C123", "1700000000.000100", "U123") == "session-1"
        )

    @pytest.mark.asyncio
    @patch("listeners.events.message.run_agent", new_callable=AsyncMock)
    async def test_teammate_reply_in_engaged_thread_excludes_owner_history(
        self, run_agent, monkeypatch, fresh_store
    ):
        monkeypatch.setenv("OWNER_USER_ID", "U0WNER")
        fresh_store.set_session("C123", "t1", "U0WNER", "owner-session")
        run_agent.return_value = run_result()

        await self.handle(
            {
                "channel_type": "channel",
                "text": "Any update?",
                "thread_ts": "t1",
                "ts": "t2",
            }
        )

        assert run_agent.call_count == 2
        reply_call = run_agent.call_args_list[1]
        reply_input, deps = reply_call.args
        assert reply_input == "Any update?"
        assert reply_call.kwargs["session_id"] is None
        assert deps.user_id == "U123"
        assert deps.user_token is None
        assert deps.is_owner is False
        assert deps.is_private_reply is False

    @pytest.mark.asyncio
    @patch("listeners.events.message.run_agent", new_callable=AsyncMock)
    async def test_thread_reply_ignored_when_thread_not_engaged(self, run_agent):
        run_agent.return_value = run_result()

        await self.handle(
            {
                "channel_type": "channel",
                "text": "Any update?",
                "thread_ts": "t1",
                "ts": "t2",
            }
        )

        run_agent.assert_called_once()
        assert run_agent.call_args.args[0].startswith("Learn from")

    @pytest.mark.asyncio
    @patch("listeners.events.message.run_agent", new_callable=AsyncMock)
    async def test_owner_reply_in_engaged_thread_uses_no_token(
        self, run_agent, monkeypatch, fresh_store
    ):
        monkeypatch.setenv("OWNER_USER_ID", "U123")
        fresh_store.set_session("C123", "t1", "U123", "owner-session")
        run_agent.return_value = run_result()

        await self.handle(
            {
                "channel_type": "channel",
                "text": "Any update?",
                "thread_ts": "t1",
                "ts": "t2",
            }
        )

        assert run_agent.call_count == 2
        reply_call = run_agent.call_args_list[1]
        _, deps = reply_call.args
        assert reply_call.kwargs["session_id"] == "owner-session"
        assert deps.is_owner is True
        assert deps.user_token is None
        assert deps.is_private_reply is False
        assert deps.is_brief is False

    @pytest.mark.asyncio
    @patch("listeners.events.message.run_agent", new_callable=AsyncMock)
    async def test_owner_dm_brief_me_is_a_normal_dm(self, run_agent, monkeypatch):
        monkeypatch.setenv("OWNER_USER_ID", "U123")
        run_agent.return_value = run_result()

        await self.handle(
            {"channel_type": "im", "text": "Brief me", "ts": "1700000000.000100"}
        )

        _, deps = run_agent.call_args.args
        assert deps.is_brief is False
        assert deps.is_owner is True
        assert deps.is_private_reply is True
