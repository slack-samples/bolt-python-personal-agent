from unittest.mock import Mock

from agent.deps import AgentDeps
from agent.tools.channel_runbooks import channel_runbooks


def test_channel_runbooks_calls_files_list_with_channel():
    client = Mock()
    client.files_list.return_value = {"files": []}
    deps = AgentDeps(
        client=client,
        user_id="U123",
        channel_id="C123",
        thread_ts="1234.56",
        message_ts="1234.56",
    )
    channel_runbooks(deps)
    client.files_list.assert_called_once_with(types="canvas", channel="C123")


def test_channel_runbooks_filters_by_title_and_channel():
    client = Mock()
    client.files_list.return_value = {
        "files": [
            {"title": "Runbook: Deploy", "channels": ["C123"], "groups": []},
            {"title": "Not a runbook", "channels": ["C123"], "groups": []},
            {"title": "Runbook: Other", "channels": ["C456"], "groups": []},
            {"title": "Runbook: Shared", "channels": [], "groups": ["C123"]},
        ]
    }
    deps = AgentDeps(
        client=client,
        user_id="U123",
        channel_id="C123",
        thread_ts="1234.56",
        message_ts="1234.56",
    )
    runbooks = channel_runbooks(deps)
    assert len(runbooks) == 2
    assert runbooks[0]["title"] == "Runbook: Deploy"
    assert runbooks[1]["title"] == "Runbook: Shared"
