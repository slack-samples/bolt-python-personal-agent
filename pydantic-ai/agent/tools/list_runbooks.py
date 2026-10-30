from pydantic_ai import RunContext
from slack_sdk.errors import SlackApiError

from agent.deps import AgentDeps
from agent.tools.channel_runbooks import channel_runbooks


async def list_runbooks(ctx: RunContext[AgentDeps]) -> str:
    """List the runbooks in this channel: canvases titled `Runbook: <topic>`.

    Call this before answering a request or writing a runbook, then read the
    one that covers the topic with `read_runbook`.

    Args:
        ctx: The run context with dependencies.
    """
    deps = ctx.deps
    try:
        runbooks = channel_runbooks(deps)
    except SlackApiError as e:
        return f"Could not list runbooks: {e.response['error']}"

    result = [
        f"- [{file['title']}]({file['permalink']}) (`{file['id']}`)"
        for file in runbooks
    ]
    if not result:
        return "No runbooks yet."
    return "\n".join(result)
