import asyncio
import json

from agents.tool_context import ToolContext
from slack_sdk.errors import SlackApiError

from agent.deps import AgentDeps


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
