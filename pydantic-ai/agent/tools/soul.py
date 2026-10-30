from pydantic_ai import RunContext

from agent.deps import AgentDeps
from agent.soul import SOUL_PATH, save_soul


async def update_soul(ctx: RunContext[AgentDeps], markdown: str) -> str:
    """Update the owner's soul file.

    Args:
        ctx: The run context with dependencies.
        markdown: The new soul content as markdown.
    """
    deps = ctx.deps

    if not deps.is_owner or not deps.is_private_reply:
        return "Only the owner can change the soul, in a direct message."

    if not markdown.strip():
        return "The soul can't be empty."

    save_soul(markdown, SOUL_PATH)
    return "Saved your soul."
