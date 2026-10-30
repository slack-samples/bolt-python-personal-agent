from claude_agent_sdk import tool
from slack_sdk.errors import SlackApiError

from agent.context import agent_deps_var
from agent.tools.channel_runbooks import channel_runbooks
from agent.tools.text_result import text_result

LIST_RUNBOOKS_DESCRIPTION = """\
List the runbooks in this channel: canvases titled `Runbook: <topic>`.

Call this before answering a request or writing a runbook, then read the
one that covers the topic with `read_runbook`.\
"""


@tool(
    name="list_runbooks",
    description=LIST_RUNBOOKS_DESCRIPTION,
    input_schema={"type": "object", "properties": {}},
)
async def list_runbooks(args: dict) -> dict:
    deps = agent_deps_var.get()
    try:
        runbooks = await channel_runbooks(deps)
    except SlackApiError as e:
        return text_result(f"Could not list runbooks: {e.response['error']}")

    result = [
        f"- [{file['title']}]({file['permalink']}) (`{file['id']}`)"
        for file in runbooks
    ]
    if not result:
        return text_result("No runbooks yet.")
    return text_result("\n".join(result))
