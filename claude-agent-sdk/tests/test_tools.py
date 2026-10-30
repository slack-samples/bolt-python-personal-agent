import random
from unittest.mock import AsyncMock, Mock

import pytest
from slack_sdk.web.async_client import AsyncWebClient

from agent.deps import AgentDeps
from agent.tools import (
    add_emoji_reaction,
    create_runbook,
    list_runbooks,
    read_runbook,
)
from tests.helpers import invoke, slack_error


class TestTools:
    def setup_method(self):
        self.client = Mock(AsyncWebClient)
        self.client.api_call = AsyncMock()
        self.client.canvases_create = AsyncMock()
        self.client.files_list = AsyncMock()
        self.client.files_info = AsyncMock(
            return_value={
                "file": {
                    "title": "Runbook: Deploys",
                    "permalink": "https://example.slack.com/docs/T1/F123",
                }
            }
        )
        self.deps = AgentDeps(
            client=self.client,
            user_id="U123",
            channel_id="C123",
            thread_ts="1700000000.000100",
            message_ts="1700000000.000100",
        )

    @pytest.mark.asyncio
    async def test_list_runbooks_lists_only_runbooks(self):
        self.client.files_list.return_value = {
            "files": [
                {
                    "id": "F123",
                    "title": "Runbook: Deploys",
                    "permalink": "https://example.com/F123",
                    "channels": ["C123"],
                },
                {
                    "id": "F456",
                    "title": "Lunch orders",
                    "permalink": "https://example.com/F456",
                    "channels": ["C123"],
                },
            ]
        }

        result = await invoke(list_runbooks, self.deps)

        assert self.client.files_list.call_args.kwargs["types"] == "canvas"
        assert "[Runbook: Deploys](https://example.com/F123) (`F123`)" in result
        assert "Lunch orders" not in result

    @pytest.mark.asyncio
    async def test_list_runbooks_without_any(self):
        self.client.files_list.return_value = {"files": []}

        assert await invoke(list_runbooks, self.deps) == "No runbooks yet."

    @pytest.mark.asyncio
    async def test_read_runbook_returns_its_markdown(self):
        self.client.files_list.return_value = {
            "files": [
                {
                    "id": "F123",
                    "title": "Runbook: Test",
                    "permalink": "https://example.com/F123",
                    "channels": ["C123"],
                }
            ]
        }
        self.client.api_call.return_value = {"content": "# Steps\n1. Rotate the secret"}

        result = await invoke(read_runbook, self.deps, canvas_id="F123")

        self.client.api_call.assert_awaited_once_with(
            "canvases.getContent", params={"canvas_id": "F123"}
        )
        assert result == "# Steps\n1. Rotate the secret"

    @pytest.mark.asyncio
    async def test_read_runbook_reports_errors(self):
        self.client.files_list.return_value = {
            "files": [
                {
                    "id": "F404",
                    "title": "Runbook: Test",
                    "permalink": "https://example.com/F404",
                    "channels": ["C123"],
                }
            ]
        }
        self.client.api_call.side_effect = slack_error("canvas_not_found")

        result = await invoke(read_runbook, self.deps, canvas_id="F404")

        assert "canvas_not_found" in result

    @pytest.mark.asyncio
    async def test_create_runbook_adds_a_channel_tab(self):
        self.client.canvases_create.return_value = {"canvas_id": "F123"}

        result = await invoke(
            create_runbook, self.deps, topic="Deploys", markdown="# Steps\n1. Redeploy"
        )

        kwargs = self.client.canvases_create.call_args.kwargs
        assert kwargs["title"] == "Runbook: Deploys"
        assert kwargs["channel_id"] == "C123"
        assert kwargs["document_content"] == {
            "type": "markdown",
            "markdown": "# Steps\n1. Redeploy",
        }
        self.client.files_info.assert_awaited_once_with(file="F123")
        assert (
            result
            == "Created [Runbook: Deploys](https://example.slack.com/docs/T1/F123)."
        )

    @pytest.mark.asyncio
    async def test_create_runbook_asks_to_fix_rejected_markdown(self):
        self.client.canvases_create.side_effect = slack_error(
            "canvas_creation_failed", "Unsupported nested list"
        )

        result = await invoke(
            create_runbook, self.deps, topic="Deploys", markdown="1. - x"
        )

        assert "Unsupported nested list" in result
        assert "call create_runbook again" in result

    @pytest.mark.asyncio
    async def test_lists_only_runbooks_shared_in_the_current_channel(self):
        self.client.files_list.return_value = {
            "files": [
                {
                    "id": "F_HERE",
                    "title": "Runbook: Here",
                    "permalink": "https://example.com/F_HERE",
                    "channels": ["C123"],
                },
                {
                    "id": "F_HERE_PRIVATE",
                    "title": "Runbook: Here too",
                    "permalink": "https://example.com/F_HERE_PRIVATE",
                    "groups": ["C123"],
                },
                {
                    "id": "F_OTHER",
                    "title": "Runbook: Other public channel",
                    "permalink": "https://example.com/F_OTHER",
                    "channels": ["C_PUB"],
                },
                {
                    "id": "F_PRIV",
                    "title": "Runbook: Private",
                    "permalink": "https://example.com/F_PRIV",
                    "groups": ["G_PRIV"],
                },
            ]
        }

        result = await invoke(list_runbooks, self.deps)

        assert "F_HERE" in result
        assert "F_HERE_PRIVATE" in result
        assert "F_OTHER" not in result
        assert "F_PRIV" not in result
        self.client.conversations_info.assert_not_called()
        self.client.users_conversations.assert_not_called()

    @pytest.mark.asyncio
    async def test_read_runbook_refuses_runbook_from_another_channel(self):
        self.client.files_list.return_value = {
            "files": [
                {
                    "id": "F_OTHER",
                    "title": "Runbook: Other",
                    "permalink": "https://example.com/F_OTHER",
                    "channels": ["C_PUB"],
                }
            ]
        }

        result = await invoke(read_runbook, self.deps, canvas_id="F_OTHER")

        assert result == "That runbook isn't available here."
        self.client.api_call.assert_not_called()

    @pytest.mark.asyncio
    async def test_null_channels_and_groups_are_not_shared(self):
        self.client.files_list.return_value = {
            "files": [
                {
                    "id": "F_NULL",
                    "title": "Runbook: Null",
                    "permalink": "https://example.com/F_NULL",
                    "channels": None,
                    "groups": None,
                }
            ]
        }

        assert await invoke(list_runbooks, self.deps) == "No runbooks yet."


@pytest.mark.asyncio
async def test_emoji_reaction_reacts_to_the_current_message(monkeypatch):
    monkeypatch.setattr(random, "random", lambda: 0.5)
    client = Mock(AsyncWebClient)
    client.reactions_add = AsyncMock()
    deps = AgentDeps(
        client=client,
        user_id="U123",
        channel_id="C123",
        thread_ts="1700000000.000100",
        message_ts="1700000000.000200",
    )

    result = await invoke(add_emoji_reaction, deps, emoji_name="tada")

    client.reactions_add.assert_awaited_once_with(
        channel="C123", timestamp="1700000000.000200", name="tada"
    )
    assert result == "Reacted with :tada:"
