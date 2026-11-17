from logging import Logger

from slack_bolt.context.async_context import AsyncBoltContext
from slack_bolt.context.say.async_say import AsyncSay
from slack_bolt.context.say_stream.async_say_stream import AsyncSayStream
from slack_bolt.context.set_status.async_set_status import AsyncSetStatus
from slack_sdk.web.async_client import AsyncWebClient

from agent import AgentDeps, run_agent
from agent.agent import AGENT_TOOLS_SERVER, allowed_tool_name
from agent.reply_deps import build_reply_deps
from agent.tools import create_runbook
from listeners.views.feedback_builder import build_feedback_blocks
from thread_context import session_store

LEARNED_SUBTYPES = {None, "file_share", "thread_broadcast"}

RUNBOOK_WRITES = {allowed_tool_name(AGENT_TOOLS_SERVER, create_runbook.name)}


async def handle_message(
    client: AsyncWebClient,
    context: AsyncBoltContext,
    event: dict,
    logger: Logger,
    say: AsyncSay,
    say_stream: AsyncSayStream,
    set_status: AsyncSetStatus,
):
    """Handle messages sent to the agent via DM or in threads the bot is part of.

    The agent also learns from channel messages, adding anything they settle to runbooks.
    """
    if event.get("bot_id"):
        return

    is_dm = event.get("channel_type") == "im"

    if should_reply(context, event, is_dm):
        await reply_to_message(
            client, context, event, logger, say, say_stream, set_status, is_dm
        )
    elif should_learn(context, event, is_dm):
        await learn_from_message(client, context, event, logger)


def mentions_bot(context: AsyncBoltContext, event: dict) -> bool:
    return f"<@{context.bot_user_id}>" in event.get("text", "")


def should_learn(context: AsyncBoltContext, event: dict, is_dm: bool) -> bool:
    return (
        not is_dm
        and event.get("subtype") in LEARNED_SUBTYPES
        and not mentions_bot(context, event)
    )


def should_reply(context: AsyncBoltContext, event: dict, is_dm: bool) -> bool:
    if event.get("subtype") not in LEARNED_SUBTYPES:
        return False
    if is_dm:
        return True
    if mentions_bot(context, event):
        return False
    thread_ts = event.get("thread_ts")
    return thread_ts is not None and session_store.has_thread(
        context.channel_id, thread_ts
    )


async def learn_from_message(
    client: AsyncWebClient, context: AsyncBoltContext, event: dict, logger: Logger
):
    try:
        deps = AgentDeps(
            client=client,
            user_id=context.user_id,
            channel_id=context.channel_id,
            thread_ts=event.get("thread_ts") or event["ts"],
            message_ts=event["ts"],
            user_token=None,
            is_owner=False,
            is_private_reply=False,
            is_learning=True,
        )
        result = await run_agent(
            f"Learn from this channel message:\n\n{event.get('text', '')}",
            deps,
            persist_session=False,
        )
        if RUNBOOK_WRITES.intersection(result.tool_names):
            await client.chat_postEphemeral(
                channel=context.channel_id,
                user=context.user_id,
                thread_ts=event.get("thread_ts"),
                markdown_text=result.final_output,
            )
    except Exception:
        logger.exception("Failed to learn from message")


async def reply_to_message(
    client: AsyncWebClient,
    context: AsyncBoltContext,
    event: dict,
    logger: Logger,
    say: AsyncSay,
    say_stream: AsyncSayStream,
    set_status: AsyncSetStatus,
    is_dm: bool,
):
    try:
        channel_id = context.channel_id
        text = event.get("text", "")
        thread_ts = event.get("thread_ts") or event["ts"]

        user_id = context.user_id

        session_id = session_store.get_session(channel_id, thread_ts, user_id)

        await set_status(
            status="Thinking...",
            loading_messages=[
                "Teaching the hamsters to type faster…",
                "Untangling the internet cables…",
                "Consulting the office goldfish…",
                "Polishing up the response just for you…",
                "Convincing the AI to stop overthinking…",
            ],
        )

        deps = build_reply_deps(client, context, event, is_private_reply=is_dm)
        result = await run_agent(text, deps, session_id=session_id)

        streamer = await say_stream()
        await streamer.append(markdown_text=result.final_output)
        feedback_blocks = build_feedback_blocks()
        await streamer.stop(blocks=feedback_blocks)

        if result.session_id:
            session_store.set_session(channel_id, thread_ts, user_id, result.session_id)

    except Exception as e:
        logger.exception("Failed to handle message")
        await say(
            text=f":warning: Something went wrong! ({e})",
            thread_ts=event.get("thread_ts") or event.get("ts"),
        )
