from agents import function_tool
from agents.run_context import RunContextWrapper
from slack_sdk.errors import SlackApiError

from agent.deps import AgentDeps
from agent.tools.channel_runbooks import channel_runbooks


@function_tool
async def read_runbook(wrapper: RunContextWrapper[AgentDeps], canvas_id: str) -> str:
    """Read a runbook's content as markdown.

    Read a runbook before you answer from it.

    Args:
        canvas_id: The runbook's canvas ID from `list_runbooks`, such as `F0123ABCD`.
    """
    deps = wrapper.context
    try:
        runbooks = channel_runbooks(deps)
    except SlackApiError as e:
        return f"Could not read the runbook: {e.response['error']}"

    if canvas_id not in {f["id"] for f in runbooks}:
        return "That runbook isn't available here."

    try:
        response = deps.client.api_call(
            "canvases.getContent", params={"canvas_id": canvas_id}
        )
    except SlackApiError as e:
        return f"Could not read the runbook: {e.response['error']}"
    return response.get("content", "")
