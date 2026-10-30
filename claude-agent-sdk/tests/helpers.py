from claude_agent_sdk import SdkMcpTool
from slack_sdk.errors import SlackApiError

from agent.context import agent_deps_var
from agent.deps import AgentDeps


def slack_error(error: str, detail: str | None = None) -> SlackApiError:
    response = {"ok": False, "error": error}
    if detail:
        response["detail"] = detail
    return SlackApiError(message=error, response=response)


async def invoke(tool: SdkMcpTool, deps: AgentDeps, **args) -> str:
    agent_deps_var.set(deps)
    result = await tool.handler(args)
    return result["content"][0]["text"]
