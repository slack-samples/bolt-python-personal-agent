from claude_agent_sdk import tool
from slack_sdk.errors import SlackApiError

from agent.context import agent_deps_var
from agent.tools.channel_runbooks import channel_runbooks
from agent.tools.text_result import text_result

READ_RUNBOOK_DESCRIPTION = """\
Read a runbook's content as markdown.

Read a runbook before you answer from it.\
"""


@tool(
    name="read_runbook",
    description=READ_RUNBOOK_DESCRIPTION,
    input_schema={
        "type": "object",
        "properties": {
            "canvas_id": {
                "type": "string",
                "description": "The runbook's canvas ID from `list_runbooks`, such as `F0123ABCD`.",
            },
        },
        "required": ["canvas_id"],
    },
)
async def read_runbook(args: dict) -> dict:
    deps = agent_deps_var.get()
    canvas_id = args["canvas_id"]
    try:
        runbooks = await channel_runbooks(deps)
    except SlackApiError as e:
        return text_result(f"Could not read the runbook: {e.response['error']}")

    if canvas_id not in {f["id"] for f in runbooks}:
        return text_result("That runbook isn't available here.")

    try:
        response = await deps.client.api_call(
            "canvases.getContent", params={"canvas_id": canvas_id}
        )
    except SlackApiError as e:
        return text_result(f"Could not read the runbook: {e.response['error']}")
    return text_result(response.get("content", ""))
