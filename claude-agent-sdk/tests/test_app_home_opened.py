import logging
from unittest.mock import AsyncMock, Mock, patch

import pytest
from slack_bolt.context.async_context import AsyncBoltContext
from slack_sdk.web.async_client import AsyncWebClient

from agent.soul import load_template
from listeners.events.app_home_opened import handle_app_home_opened

test_logger = logging.getLogger(__name__)


class TestAppHomeOpened:
    def setup_method(self):
        self.fake_client = Mock(AsyncWebClient)
        self.fake_client.views_publish = AsyncMock()
        self.fake_client.assistant_threads_setSuggestedPrompts = AsyncMock()
        self.fake_context = Mock(AsyncBoltContext)
        self.fake_context.user_token = None
        self.fake_context.user_id = "U123"

    @pytest.mark.asyncio
    async def test_publishes_home_view_when_tab_is_home(self):
        await handle_app_home_opened(
            client=self.fake_client,
            event={"tab": "home", "channel": "D123"},
            context=self.fake_context,
            logger=test_logger,
        )

        self.fake_client.views_publish.assert_called_once()
        kwargs = self.fake_client.views_publish.call_args.kwargs
        assert kwargs["user_id"] == "U123"
        assert kwargs["view"]["type"] == "home"
        self.fake_client.assistant_threads_setSuggestedPrompts.assert_not_called()

    @pytest.mark.asyncio
    async def test_sets_suggested_prompts_when_tab_is_messages(self):
        await handle_app_home_opened(
            client=self.fake_client,
            event={"tab": "messages", "channel": "D123"},
            context=self.fake_context,
            logger=test_logger,
        )

        self.fake_client.assistant_threads_setSuggestedPrompts.assert_called_once()
        kwargs = self.fake_client.assistant_threads_setSuggestedPrompts.call_args.kwargs
        assert kwargs["channel_id"] == "D123"
        assert isinstance(kwargs["prompts"], list)
        self.fake_client.views_publish.assert_not_called()

    @pytest.mark.asyncio
    async def test_views_publish_exception(self, caplog):
        self.fake_client.views_publish.side_effect = Exception("test exception")

        await handle_app_home_opened(
            client=self.fake_client,
            event={"tab": "home", "channel": "D123"},
            context=self.fake_context,
            logger=test_logger,
        )

        self.fake_client.views_publish.assert_called_once()
        assert "test exception" in caplog.text

    @pytest.mark.asyncio
    async def test_messages_tab_owner_prompts(self, monkeypatch):
        monkeypatch.setenv("OWNER_USER_ID", "U123")
        self.fake_context.user_id = "U123"

        await handle_app_home_opened(
            client=self.fake_client,
            event={"tab": "messages", "channel": "D123"},
            context=self.fake_context,
            logger=test_logger,
        )

        kwargs = self.fake_client.assistant_threads_setSuggestedPrompts.call_args.kwargs
        prompts = kwargs["prompts"]
        prompt_titles = [p["title"] for p in prompts]
        assert "Write a Runbook" in prompt_titles
        assert "Update my soul" in prompt_titles

    @pytest.mark.asyncio
    async def test_messages_tab_guest_prompts(self, monkeypatch):
        monkeypatch.setenv("OWNER_USER_ID", "UOWNER")
        self.fake_context.user_id = "UGUEST"

        await handle_app_home_opened(
            client=self.fake_client,
            event={"tab": "messages", "channel": "D123"},
            context=self.fake_context,
            logger=test_logger,
        )

        kwargs = self.fake_client.assistant_threads_setSuggestedPrompts.call_args.kwargs
        prompts = kwargs["prompts"]
        prompt_titles = [p["title"] for p in prompts]
        assert "Ask what they're working on" in prompt_titles
        assert "Update my soul" not in prompt_titles

    @pytest.mark.asyncio
    async def test_home_shows_soul_status_for_owner(self, monkeypatch):
        monkeypatch.setenv("OWNER_USER_ID", "U123")
        self.fake_context.user_id = "U123"

        with patch("listeners.events.app_home_opened.load_soul") as mock_load_soul:
            mock_load_soul.return_value = load_template()

            await handle_app_home_opened(
                client=self.fake_client,
                event={"tab": "home", "channel": "D123"},
                context=self.fake_context,
                logger=test_logger,
            )

            kwargs = self.fake_client.views_publish.call_args.kwargs
            view_text = str(kwargs["view"])
            assert "isn't set up" in view_text

    @pytest.mark.asyncio
    async def test_home_hides_soul_status_for_guest(self, monkeypatch):
        monkeypatch.setenv("OWNER_USER_ID", "UOWNER")
        self.fake_context.user_id = "UGUEST"

        await handle_app_home_opened(
            client=self.fake_client,
            event={"tab": "home", "channel": "D123"},
            context=self.fake_context,
            logger=test_logger,
        )

        kwargs = self.fake_client.views_publish.call_args.kwargs
        view_text = str(kwargs["view"])
        assert "soul" not in view_text.lower()
