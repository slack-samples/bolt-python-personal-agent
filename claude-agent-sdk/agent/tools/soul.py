from claude_agent_sdk import tool

from agent.context import agent_deps_var
from agent.soul import SOUL_PATH, save_soul
from agent.tools.text_result import text_result


@tool(
    name="update_soul",
    description="Update the owner's soul file.",
    input_schema={
        "type": "object",
        "properties": {
            "markdown": {
                "type": "string",
                "description": "The new soul content as markdown.",
            },
        },
        "required": ["markdown"],
    },
)
async def update_soul(args: dict) -> dict:
    deps = agent_deps_var.get()

    if not deps.is_owner or not deps.is_private_reply:
        return text_result("Only the owner can change the soul, in a direct message.")

    markdown = args["markdown"]
    if not markdown.strip():
        return text_result("The soul can't be empty.")

    save_soul(markdown, SOUL_PATH)
    return text_result("Saved your soul.")
