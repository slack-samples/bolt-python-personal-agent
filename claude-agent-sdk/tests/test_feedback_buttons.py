import logging
from unittest.mock import AsyncMock, Mock

import pytest
from slack_bolt.context.async_context import AsyncBoltContext
from slack_sdk.web.async_client import AsyncWebClient

from listeners.actions.feedback_buttons import handle_feedback_button

test_logger = logging.getLogger(__name__)


def make_context():
    context = Mock(AsyncBoltContext)
    context.channel_id = "C123"
    context.user_id = "U123"
    return context


async def press(message, value="good-feedback"):
    client = Mock(AsyncWebClient)
    client.chat_postEphemeral = AsyncMock()
    ack = AsyncMock()
    await handle_feedback_button(
        ack=ack,
        body={"message": message, "actions": [{"value": value}]},
        client=client,
        context=make_context(),
        logger=test_logger,
    )
    ack.assert_awaited_once()
    return client.chat_postEphemeral.call_args.kwargs


@pytest.mark.asyncio
async def test_feedback_replies_in_the_message_thread():
    kwargs = await press({"ts": "t2", "thread_ts": "t1"})
    assert kwargs["channel"] == "C123"
    assert kwargs["user"] == "U123"
    assert kwargs["thread_ts"] == "t1"
    assert "Glad that was helpful" in kwargs["text"]


@pytest.mark.asyncio
async def test_feedback_falls_back_to_the_message_ts_without_a_thread():
    kwargs = await press({"ts": "t1"}, value="bad-feedback")
    assert kwargs["thread_ts"] == "t1"
    assert "Sorry that wasn't helpful" in kwargs["text"]
