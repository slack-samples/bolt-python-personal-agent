import logging
from unittest.mock import AsyncMock, Mock, patch

import pytest
from pydantic_ai.messages import ModelRequest, UserPromptPart
from slack_bolt import BoltContext
from slack_sdk import WebClient

from agent.agent import AgentResult
from listeners.events.message import handle_message
from thread_context.store import ConversationStore

test_logger = logging.getLogger(__name__)


@pytest.fixture(autouse=True)
def fresh_store():
    store = ConversationStore()
    with patch("listeners.events.message.conversation_store", store):
        yield store


def run_result(*tool_names):
    return AgentResult(
        "Added the steps to [Runbook: Deploys](https://example.com).",
        [],
        list(tool_names),
    )


class TestMessage:
    def setup_method(self):
        self.fake_client = Mock(WebClient)
        self.fake_context = Mock(BoltContext)
        self.fake_context.channel_id = "C123"
        self.fake_context.user_id = "U123"
        self.fake_context.user_token = "xoxp-123"
        self.fake_context.bot_user_id = "UBOT"
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
        run_agent.return_value = run_result("create_runbook")

        self.handle(
            {
                "channel_type": "channel",
                "text": "Fixed it: rotate the signing secret, then redeploy",
                "thread_ts": "1700000000.000100",
                "ts": "1700000000.000200",
            }
        )

        learn_input, deps = run_agent.call_args.args
        assert run_agent.call_args.kwargs == {}
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
            "C123",
            "t1",
            "U0WNER",
            [ModelRequest(parts=[UserPromptPart(content="owner secret")])],
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
        reply_call = run_agent.call_args_list[0]
        reply_input, deps = reply_call.args
        assert reply_input == "Any update?"
        assert reply_call.kwargs["message_history"] is None
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

    @patch("listeners.events.message.run_agent", new_callable=AsyncMock)
    def test_owner_reply_in_engaged_thread_uses_no_token(
        self, run_agent, monkeypatch, fresh_store
    ):
        monkeypatch.setenv("OWNER_USER_ID", "U123")
        fresh_store.set_history("C123", "t1", "U123", [])
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
        _, deps = run_agent.call_args_list[0].args
        assert deps.is_owner is True
        assert deps.user_token is None
        assert deps.is_private_reply is False
        assert deps.is_brief is False

    @patch("listeners.events.message.run_agent", new_callable=AsyncMock)
    def test_owner_dm_brief_me_is_a_normal_dm(self, run_agent, monkeypatch):
        monkeypatch.setenv("OWNER_USER_ID", "U123")
        run_agent.return_value = run_result()

        self.handle(
            {"channel_type": "im", "text": "Brief me", "ts": "1700000000.000100"}
        )

        _, deps = run_agent.call_args.args
        assert deps.is_brief is False
        assert deps.is_owner is True
        assert deps.is_private_reply is True

    @patch("listeners.events.message.run_agent", new_callable=AsyncMock)
    def test_stays_quiet_when_mcp_canvas_tools_are_called(self, run_agent):
        run_agent.return_value = run_result(
            "slack_update_canvas", "slack_create_canvas"
        )

        self.handle(
            {"channel_type": "channel", "text": "Fixed it", "ts": "1700000000.000100"}
        )

        self.fake_client.chat_postEphemeral.assert_not_called()

    @patch("listeners.events.message.run_agent", new_callable=AsyncMock)
    def test_dm_stores_and_resumes_the_requesters_history(self, run_agent, fresh_store):
        messages = [ModelRequest(parts=[UserPromptPart(content="What's new?")])]
        run_agent.return_value = AgentResult("Nothing yet.", messages, [])

        self.handle({"channel_type": "im", "text": "What's new?", "ts": "t1"})

        assert fresh_store.get_history("C123", "t1", "U123") == messages

        self.handle(
            {"channel_type": "im", "text": "And now?", "thread_ts": "t1", "ts": "t2"}
        )

        assert run_agent.call_args.kwargs["message_history"] == messages

    @patch("listeners.events.message.run_agent", new_callable=AsyncMock)
    def test_mention_in_engaged_thread_is_left_to_app_mention(
        self, run_agent, fresh_store
    ):
        fresh_store.set_history("C123", "t1", "U123", [])
        run_agent.return_value = run_result()
        say_stream = Mock()

        handle_message(
            client=self.fake_client,
            context=self.fake_context,
            event={
                "channel_type": "channel",
                "text": "<@UBOT> any update?",
                "thread_ts": "t1",
                "ts": "t2",
            },
            logger=test_logger,
            say=self.fake_say,
            say_stream=say_stream,
            set_status=Mock(),
        )

        run_agent.assert_called_once()
        assert run_agent.call_args.args[0].startswith("Learn from")
        say_stream.assert_not_called()

    @patch("listeners.events.message.run_agent", new_callable=AsyncMock)
    def test_dm_that_mentions_the_agent_still_gets_a_reply(self, run_agent):
        run_agent.return_value = run_result()

        self.handle({"channel_type": "im", "text": "<@UBOT> what's new?", "ts": "t1"})

        run_agent.assert_called_once()
        assert run_agent.call_args.args[0] == "<@UBOT> what's new?"

    def handle_in_engaged_thread(self, fresh_store, say_stream):
        fresh_store.set_history("C123", "t1", "U123", [])
        handle_message(
            client=self.fake_client,
            context=self.fake_context,
            event={
                "channel_type": "channel",
                "text": "Any update?",
                "thread_ts": "t1",
                "ts": "t2",
            },
            logger=test_logger,
            say=self.fake_say,
            say_stream=say_stream,
            set_status=Mock(),
        )

    @patch("listeners.events.message.run_agent", new_callable=AsyncMock)
    def test_replies_before_learning(self, run_agent, fresh_store):
        say_stream = Mock()
        replied_before_learning = []

        async def respond(agent_input, deps, **kwargs):
            if str(agent_input).startswith("Learn from"):
                replied_before_learning.append(
                    say_stream.return_value.append.call_count == 1
                )
            return run_result()

        run_agent.side_effect = respond

        self.handle_in_engaged_thread(fresh_store, say_stream)

        assert run_agent.call_count == 2
        assert run_agent.call_args_list[0].args[0] == "Any update?"
        assert replied_before_learning == [True]

    @patch("listeners.events.message.run_agent", new_callable=AsyncMock)
    def test_learns_when_the_reply_fails(self, run_agent, fresh_store):
        run_agent.side_effect = [
            Exception("reply failed"),
            run_result("create_runbook"),
        ]

        self.handle_in_engaged_thread(fresh_store, Mock())

        assert "reply failed" in self.fake_say.call_args.kwargs["text"]
        self.fake_client.chat_postEphemeral.assert_called_once()

    @patch("listeners.events.message.run_agent", new_callable=AsyncMock)
    def test_learns_when_the_error_reply_fails(self, run_agent, fresh_store):
        run_agent.side_effect = [
            Exception("reply failed"),
            run_result("create_runbook"),
        ]
        self.fake_say.side_effect = Exception("say failed")

        with pytest.raises(Exception, match="say failed"):
            self.handle_in_engaged_thread(fresh_store, Mock())

        self.fake_client.chat_postEphemeral.assert_called_once()

    @patch("listeners.events.message.run_agent", new_callable=AsyncMock)
    def test_reply_survives_a_learning_failure(self, run_agent, fresh_store, caplog):
        run_agent.side_effect = [run_result(), Exception("learning failed")]
        say_stream = Mock()

        self.handle_in_engaged_thread(fresh_store, say_stream)

        say_stream.return_value.append.assert_called_once()
        assert "learning failed" in caplog.text
        self.fake_say.assert_not_called()
