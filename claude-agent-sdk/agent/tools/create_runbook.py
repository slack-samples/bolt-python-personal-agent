from claude_agent_sdk import tool
from slack_sdk.errors import SlackApiError

from agent.context import agent_deps_var
from agent.tools.text_result import text_result

CREATE_RUNBOOK_DESCRIPTION = """\
Create a runbook as a tab in the current channel so the whole team can read and edit it.

Only create a runbook when `list_runbooks` shows none that covers the topic.\
"""


@tool(
    name="create_runbook",
    description=CREATE_RUNBOOK_DESCRIPTION,
    input_schema={
        "type": "object",
        "properties": {
            "topic": {
                "type": "string",
                "description": "What the runbook covers, such as `Rotating the signing secret`. It's titled `Runbook: <topic>`.",
            },
            "markdown": {
                "type": "string",
                "description": "The runbook as markdown, with short sections for when to use it, the steps, and who to ask.",
            },
        },
        "required": ["topic", "markdown"],
    },
)
async def create_runbook(args: dict) -> dict:
    deps = agent_deps_var.get()
    try:
        created = await deps.client.canvases_create(
            title=f"Runbook: {args['topic']}",
            document_content={"type": "markdown", "markdown": args["markdown"]},
            channel_id=deps.channel_id,
        )
        file = (await deps.client.files_info(file=created["canvas_id"]))["file"]
    except SlackApiError as e:
        detail = e.response.get("detail")
        if detail:
            return text_result(
                f"Could not create the runbook: {e.response['error']} ({detail}). "
                "Fix the markdown and call create_runbook again."
            )
        return text_result(f"Could not create the runbook: {e.response['error']}")
    return text_result(f"Created [{file['title']}]({file['permalink']}).")
