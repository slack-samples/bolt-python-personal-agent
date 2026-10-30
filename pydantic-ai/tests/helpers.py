import asyncio
from unittest.mock import Mock

from slack_sdk.errors import SlackApiError

from agent.deps import AgentDeps


def slack_error(error: str, detail: str | None = None) -> SlackApiError:
    response = {"ok": False, "error": error}
    if detail:
        response["detail"] = detail
    return SlackApiError(message=error, response=response)


def invoke(tool, deps: AgentDeps, **args) -> str:
    return asyncio.run(tool(Mock(deps=deps), **args))
