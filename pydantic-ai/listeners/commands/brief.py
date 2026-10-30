import asyncio
from logging import Logger

from slack_bolt import BoltContext
from slack_sdk import WebClient

from agent import AgentDeps, run_agent
from agent.access import is_owner, owner_user_id
from listeners.install_url import connect_message

BRIEF_PROMPT = "Brief me: what needs my attention today?"


def handle_brief(
    ack,
    command: dict,
    client: WebClient,
    context: BoltContext,
    respond,
    logger: Logger,
) -> None:
    """Handle /brief slash command (owner-only, requires MCP connection, read-only)."""
    ack()

    try:
        user_id = command["user_id"]
        if not is_owner(user_id):
            owner = owner_user_id()
            if owner:
                respond(text=f"`/brief` is only for <@{owner}>.")
            else:
                respond(text="`/brief` is only for this agent's owner.")
            return

        if not context.user_token:
            respond(text=connect_message())
            return

        respond("Putting your brief together…")

        deps = AgentDeps(
            client=client,
            user_id=user_id,
            channel_id=command["channel_id"],
            thread_ts="",
            message_ts="",
            user_token=context.user_token,
            is_owner=True,
            is_private_reply=True,
            is_brief=True,
        )

        result = asyncio.run(run_agent(BRIEF_PROMPT, deps))
        respond(text=result.final_output)

    except Exception as e:
        logger.exception("Failed to handle /brief command")
        respond(text=f":warning: Something went wrong! ({e})")
