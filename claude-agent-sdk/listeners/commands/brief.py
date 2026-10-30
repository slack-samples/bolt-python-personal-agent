from logging import Logger

from slack_bolt.context.ack.async_ack import AsyncAck
from slack_bolt.context.async_context import AsyncBoltContext
from slack_bolt.context.respond.async_respond import AsyncRespond
from slack_sdk.web.async_client import AsyncWebClient

from agent import AgentDeps, run_agent
from agent.access import is_owner, owner_user_id
from listeners.install_url import connect_message

BRIEF_PROMPT = "Brief me: what needs my attention today?"


async def handle_brief(
    ack: AsyncAck,
    command: dict,
    client: AsyncWebClient,
    context: AsyncBoltContext,
    respond: AsyncRespond,
    logger: Logger,
) -> None:
    """Handle /brief slash command (owner-only, requires MCP connection, read-only)."""
    await ack()

    try:
        user_id = command["user_id"]
        if not is_owner(user_id):
            owner = owner_user_id()
            if owner:
                await respond(text=f"`/brief` is only for <@{owner}>.")
            else:
                await respond(text="`/brief` is only for this agent's owner.")
            return

        if not context.user_token:
            await respond(text=connect_message())
            return

        await respond("Putting your brief together…")

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

        result = await run_agent(BRIEF_PROMPT, deps, persist_session=False)
        await respond(text=result.final_output)

    except Exception as e:
        logger.exception("Failed to handle /brief command")
        await respond(text=f":warning: Something went wrong! ({e})")
