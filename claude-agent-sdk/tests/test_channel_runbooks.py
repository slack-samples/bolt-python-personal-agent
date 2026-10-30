from unittest.mock import AsyncMock

import pytest

from agent.deps import AgentDeps
from agent.tools.channel_runbooks import channel_runbooks


def make_deps(client):
    return AgentDeps(
        client=client,
        user_id="U123",
        channel_id="C123",
        thread_ts="1234.56",
        message_ts="1234.56",
    )


@pytest.mark.asyncio
async def test_channel_runbooks_calls_files_list_with_channel():
    client = AsyncMock()
    client.files_list.return_value = {"files": []}
    await channel_runbooks(make_deps(client))
    client.files_list.assert_awaited_once_with(types="canvas", channel="C123")


@pytest.mark.asyncio
async def test_channel_runbooks_filters_by_title_and_channel():
    client = AsyncMock()
    client.files_list.return_value = {
        "files": [
            {"title": "Runbook: Deploy", "channels": ["C123"], "groups": []},
            {"title": "Not a runbook", "channels": ["C123"], "groups": []},
            {"title": "Runbook: Other", "channels": ["C456"], "groups": []},
            {"title": "Runbook: Shared", "channels": [], "groups": ["C123"]},
        ]
    }
    runbooks = await channel_runbooks(make_deps(client))
    assert len(runbooks) == 2
    assert runbooks[0]["title"] == "Runbook: Deploy"
    assert runbooks[1]["title"] == "Runbook: Shared"
