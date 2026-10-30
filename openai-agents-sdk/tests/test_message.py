import logging
from unittest.mock import AsyncMock, Mock, patch

import pytest
from agents import RunResult
from slack_bolt import BoltContext
from slack_sdk import WebClient

from listeners.events.message import handle_message
from thread_context.store import ConversationStore

test_logger = logging.getLogger(__name__)


@pytest.fixture(autouse=True)
def fresh_store():
    store = ConversationStore()
    with patch("listeners.events.message.conversation_store", store):
        yield store


def run_result(*tool_names):
    result = Mock(RunResult)
    result.final_output = "Added the steps to [Runbook: Deploys](https://example.com)."
    result.new_items = [Mock(raw_item=Mock(spec=["name"])) for _ in tool_names]
    for item, name in zip(result.new_items, tool_names):
        item.raw_item.name = name
    return result


class TestMessage:
    def setup_method(self):
        self.fake_client = Mock(WebClient)
        self.fake_context = Mock(BoltContext)
        self.fake_context.channel_id = "C123"
        self.fake_context.user_id = "U123"
        self.fake_context.user_token = "xoxp-123"
        self.fake_say = Mock()

    def handle(self, event):
        handle_message(
            client=self.fake_client,
            context=self.fake_context,
            event=event,
            logger=test_logger,
            say=self.fake_say,
            say_stream=Mock(),
            set_status=Mock(),
        )

    @patch("listeners.events.message.run_agent", new_callable=AsyncMock)
    def test_learns_with_bot_token_only(self, run_agent):
        run_agent.return_value = run_result("slack_update_canvas")

        self.handle(
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

    @patch("listeners.events.message.run_agent", new_callable=AsyncMock)
    def test_stays_quiet_when_no_runbook_changed(self, run_agent):
        run_agent.return_value = run_result("slack_search_public_and_private")

        self.handle(
            {
                "channel_type": "group",
                "text": "Lunch at noon?",
                "ts": "1700000000.000100",
            }
        )

        run_agent.assert_called_once()
        self.fake_client.chat_postEphemeral.assert_not_called()

    @patch("listeners.events.message.run_agent", new_callable=AsyncMock)
    def test_learns_from_broadcast_thread_replies(self, run_agent):
        run_agent.return_value = run_result()

        self.handle(
            {
                "channel_type": "channel",
                "subtype": "thread_broadcast",
                "text": "Fixed: restarting the worker cleared the queue",
                "thread_ts": "1700000000.000100",
                "ts": "1700000000.000200",
            }
        )

        run_agent.assert_called_once()

    @patch("listeners.events.message.run_agent", new_callable=AsyncMock)
    def test_logs_learning_errors(self, run_agent, caplog):
        run_agent.side_effect = Exception("test exception")

        self.handle(
            {
                "channel_type": "channel",
                "text": "Fixed it: rotate the signing secret",
                "ts": "1700000000.000100",
            }
        )

        assert "test exception" in caplog.text

    @patch("listeners.events.message.run_agent", new_callable=AsyncMock)
    def test_learns_with_the_bot_token_without_a_user_token(self, run_agent):
        self.fake_context.user_token = None
        run_agent.return_value = run_result("create_runbook")

        self.handle(
            {
                "channel_type": "channel",
                "text": "Fixed it: rotate the signing secret",
                "ts": "1700000000.000100",
            }
        )

        _, deps = run_agent.call_args.args
        assert deps.user_token is None
        self.fake_client.chat_postEphemeral.assert_called_once()

    @patch("listeners.events.message.run_agent", new_callable=AsyncMock)
    def test_does_not_learn_from_edits_or_bots(self, run_agent):
        self.handle(
            {
                "channel_type": "channel",
                "subtype": "message_changed",
                "ts": "1700000000.000100",
            }
        )
        self.handle(
            {
                "bot_id": "B123",
                "channel_type": "channel",
                "text": "Added the steps to the runbook.",
                "ts": "1700000000.000200",
            }
        )

        run_agent.assert_not_called()

    @patch("listeners.events.message.run_agent", new_callable=AsyncMock)
    def test_does_not_learn_from_dms(self, run_agent):
        run_agent.return_value = run_result()

        self.handle(
            {"channel_type": "im", "text": "Thanks!", "ts": "1700000000.000100"}
        )

        for call in run_agent.call_args_list:
            assert not str(call.args[0]).startswith("Learn from")

    @patch("listeners.events.message.run_agent", new_callable=AsyncMock)
    def test_dm_uses_requesters_token_privately(self, run_agent):
        run_agent.return_value = run_result()

        self.handle(
            {"channel_type": "im", "text": "What's new?", "ts": "1700000000.000100"}
        )

        _, deps = run_agent.call_args.args
        assert deps.user_token == "xoxp-123"
        assert deps.is_private_reply is True

    @patch("listeners.events.message.run_agent", new_callable=AsyncMock)
    def test_teammate_reply_in_engaged_thread_excludes_owner_history(
        self, run_agent, monkeypatch, fresh_store
    ):
        monkeypatch.setenv("OWNER_USER_ID", "U0WNER")
        fresh_store.set_history(
            "C123", "t1", "U0WNER", [{"role": "user", "content": "owner secret"}]
        )
        run_agent.return_value = run_result()

        self.handle(
            {
                "channel_type": "channel",
                "text": "Any update?",
                "thread_ts": "t1",
                "ts": "t2",
            }
        )

        assert run_agent.call_count == 2
        reply_input, deps = run_agent.call_args_list[1].args
        assert reply_input == "Any update?"
        assert deps.user_id == "U123"
        assert deps.user_token is None
        assert deps.is_owner is False
        assert deps.is_private_reply is False

    @patch("listeners.events.message.run_agent", new_callable=AsyncMock)
    def test_thread_reply_ignored_when_thread_not_engaged(self, run_agent):
        run_agent.return_value = run_result()

        self.handle(
            {
                "channel_type": "channel",
                "text": "Any update?",
                "thread_ts": "t1",
                "ts": "t2",
            }
        )

        run_agent.assert_called_once()
        assert run_agent.call_args.args[0].startswith("Learn from")
