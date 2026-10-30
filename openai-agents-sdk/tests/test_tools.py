import asyncio
import json
from unittest.mock import Mock

from agents.tool_context import ToolContext
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from agent.deps import AgentDeps
from agent.tools import create_runbook, list_runbooks, read_runbook


def slack_error(error: str, detail: str | None = None) -> SlackApiError:
    response = {"ok": False, "error": error}
    if detail:
        response["detail"] = detail
    return SlackApiError(message=error, response=response)


def invoke(tool, deps: AgentDeps, **args) -> str:
    ctx = ToolContext(
        context=deps,
        tool_name=tool.name,
        tool_call_id="call_1",
        tool_arguments=json.dumps(args),
    )
    return asyncio.run(tool.on_invoke_tool(ctx, json.dumps(args)))


class TestTools:
    def setup_method(self):
        self.client = Mock(WebClient)
        self.client.files_info.return_value = {
            "file": {
                "title": "Runbook: Deploys",
                "permalink": "https://example.slack.com/docs/T1/F123",
            }
        }
        self.deps = AgentDeps(
            client=self.client,
            user_id="U123",
            channel_id="C123",
            thread_ts="1700000000.000100",
            message_ts="1700000000.000100",
        )

    def test_list_runbooks_lists_only_runbooks(self):
        self.client.files_list.return_value = {
            "files": [
                {
                    "id": "F123",
                    "title": "Runbook: Deploys",
                    "permalink": "https://example.com/F123",
                    "channels": ["C_PUB"],
                },
                {
                    "id": "F456",
                    "title": "Lunch orders",
                    "permalink": "https://example.com/F456",
                    "channels": ["C_PUB"],
                },
            ]
        }

        result = invoke(list_runbooks, self.deps)

        assert self.client.files_list.call_args.kwargs["types"] == "canvas"
        assert "[Runbook: Deploys](https://example.com/F123) (`F123`)" in result
        assert "Lunch orders" not in result

    def test_list_runbooks_without_any(self):
        self.client.files_list.return_value = {"files": []}

        assert invoke(list_runbooks, self.deps) == "No runbooks yet."

    def test_read_runbook_returns_its_markdown(self):
        self.client.files_list.return_value = {
            "files": [
                {
                    "id": "F123",
                    "title": "Runbook: Test",
                    "permalink": "https://example.com/F123",
                    "channels": ["C_PUB"],
                }
            ]
        }
        self.client.api_call.return_value = {"content": "# Steps\n1. Rotate the secret"}

        result = invoke(read_runbook, self.deps, canvas_id="F123")

        self.client.api_call.assert_called_once_with(
            "canvases.getContent", params={"canvas_id": "F123"}
        )
        assert result == "# Steps\n1. Rotate the secret"

    def test_read_runbook_reports_errors(self):
        self.client.files_list.return_value = {
            "files": [
                {
                    "id": "F404",
                    "title": "Runbook: Test",
                    "permalink": "https://example.com/F404",
                    "channels": ["C_PUB"],
                }
            ]
        }
        self.client.api_call.side_effect = slack_error("canvas_not_found")

        result = invoke(read_runbook, self.deps, canvas_id="F404")

        assert "canvas_not_found" in result

    def test_create_runbook_adds_a_channel_tab(self):
        self.client.canvases_create.return_value = {"canvas_id": "F123"}

        result = invoke(
            create_runbook, self.deps, topic="Deploys", markdown="# Steps\n1. Redeploy"
        )

        kwargs = self.client.canvases_create.call_args.kwargs
        assert kwargs["title"] == "Runbook: Deploys"
        assert kwargs["channel_id"] == "C123"
        assert kwargs["document_content"] == {
            "type": "markdown",
            "markdown": "# Steps\n1. Redeploy",
        }
        self.client.files_info.assert_called_once_with(file="F123")
        assert (
            result
            == "Created [Runbook: Deploys](https://example.slack.com/docs/T1/F123)."
        )

    def test_create_runbook_asks_to_fix_rejected_markdown(self):
        self.client.canvases_create.side_effect = slack_error(
            "canvas_creation_failed", "Unsupported nested list"
        )

        result = invoke(create_runbook, self.deps, topic="Deploys", markdown="1. - x")

        assert "Unsupported nested list" in result
        assert "call create_runbook again" in result

    def test_channel_reply_lists_public_and_current_channel_runbooks(self):
        self.client.files_list.return_value = {
            "files": [
                {
                    "id": "F_PUB",
                    "title": "Runbook: Public",
                    "permalink": "https://example.com/F_PUB",
                    "channels": ["C_PUB"],
                },
                {
                    "id": "F_PRIV",
                    "title": "Runbook: Private",
                    "permalink": "https://example.com/F_PRIV",
                    "groups": ["G_PRIV"],
                },
                {
                    "id": "F_HERE",
                    "title": "Runbook: Here",
                    "permalink": "https://example.com/F_HERE",
                    "groups": ["C123"],
                },
            ]
        }
        self.deps.is_private_reply = False

        result = invoke(list_runbooks, self.deps)

        assert "F_PUB" in result
        assert "F_HERE" in result
        assert "F_PRIV" not in result
        assert (
            not hasattr(self.client, "users_conversations")
            or not self.client.users_conversations.called
        )

    def test_private_reply_includes_requesters_private_channels(self):
        self.client.files_list.return_value = {
            "files": [
                {
                    "id": "F_PRIV",
                    "title": "Runbook: Private",
                    "permalink": "https://example.com/F_PRIV",
                    "groups": ["G_PRIV"],
                },
            ]
        }
        self.client.users_conversations.return_value = {
            "channels": [{"id": "G_PRIV"}],
            "response_metadata": {},
        }
        self.deps.is_private_reply = True

        result = invoke(list_runbooks, self.deps)

        assert "F_PRIV" in result
        self.client.users_conversations.assert_called_once()

    def test_private_reply_excludes_private_channels_requester_is_not_in(self):
        self.client.files_list.return_value = {
            "files": [
                {
                    "id": "F_PRIV",
                    "title": "Runbook: Private",
                    "permalink": "https://example.com/F_PRIV",
                    "groups": ["G_PRIV"],
                },
            ]
        }
        self.client.users_conversations.return_value = {
            "channels": [],
            "response_metadata": {},
        }
        self.deps.is_private_reply = True

        result = invoke(list_runbooks, self.deps)

        assert "F_PRIV" not in result

    def test_read_runbook_refuses_runbook_not_visible(self):
        self.client.files_list.return_value = {
            "files": [
                {
                    "id": "F_PRIV",
                    "title": "Runbook: Private",
                    "permalink": "https://example.com/F_PRIV",
                    "groups": ["G_PRIV"],
                },
            ]
        }
        self.deps.is_private_reply = False

        result = invoke(read_runbook, self.deps, canvas_id="F_PRIV")

        assert result == "That runbook isn't available here."
        assert not self.client.api_call.called
