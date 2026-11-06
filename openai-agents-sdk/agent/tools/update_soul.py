from agents import function_tool
from agents.run_context import RunContextWrapper

from agent.deps import AgentDeps
from agent.soul import SOUL_PATH, save_soul


@function_tool
async def update_soul(wrapper: RunContextWrapper[AgentDeps], markdown: str) -> str:
    """Update the owner's soul file.

    Args:
        markdown: The new soul content as markdown.
    """
    deps = wrapper.context

    if not deps.is_owner or not deps.is_private_reply:
        return "Only the owner can change the soul, in a direct message."

    if not markdown.strip():
        return "The soul can't be empty."

    save_soul(markdown, SOUL_PATH)
    return "Saved your soul."
