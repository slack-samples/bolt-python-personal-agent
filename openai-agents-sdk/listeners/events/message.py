import asyncio
from logging import Logger

from slack_bolt import BoltContext, Say, SayStream, SetStatus
from slack_sdk import WebClient

from agent import AgentDeps, run_agent
from listeners.events.reply_deps import build_reply_deps
from listeners.views.feedback_builder import build_feedback_blocks
from thread_context import conversation_store

LEARNED_SUBTYPES = {None, "file_share", "thread_broadcast"}

RUNBOOK_WRITES = {"create_runbook"}


def handle_message(
    client: WebClient,
    context: BoltContext,
    event: dict,
    logger: Logger,
    say: Say,
    say_stream: SayStream,
    set_status: SetStatus,
):
    """Handle messages sent to the agent via DM or in threads the bot is part of.

    The agent also learns from channel messages, adding anything they settle to runbooks.
    """
    if event.get("bot_id"):
        return

    is_dm = event.get("channel_type") == "im"

    try:
        if should_reply(context, event, is_dm):
            reply_to_message(
                client, context, event, logger, say, say_stream, set_status, is_dm
            )
    finally:
        if not is_dm and event.get("subtype") in LEARNED_SUBTYPES:
            learn_from_message(client, context, event, logger)


def should_reply(context: BoltContext, event: dict, is_dm: bool) -> bool:
    if event.get("subtype") not in LEARNED_SUBTYPES:
        return False
    if is_dm:
        return True
    if f"<@{context.bot_user_id}>" in event.get("text", ""):
        return False
    thread_ts = event.get("thread_ts")
    return thread_ts is not None and conversation_store.has_thread(
        context.channel_id, thread_ts
    )


def learn_from_message(
    client: WebClient, context: BoltContext, event: dict, logger: Logger
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
        )
        result = asyncio.run(
            run_agent(
                f"Learn from this channel message:\n\n{event.get('text', '')}", deps
            )
        )
        if any(
            getattr(item.raw_item, "name", None) in RUNBOOK_WRITES
            for item in result.new_items
        ):
            client.chat_postEphemeral(
                channel=context.channel_id,
                user=context.user_id,
                thread_ts=event.get("thread_ts"),
                markdown_text=result.final_output,
            )
    except Exception:
        logger.exception("Failed to learn from message")


def reply_to_message(
    client: WebClient,
    context: BoltContext,
    event: dict,
    logger: Logger,
    say: Say,
    say_stream: SayStream,
    set_status: SetStatus,
    is_dm: bool,
):
    try:
        channel_id = context.channel_id
        text = event.get("text", "")
        thread_ts = event.get("thread_ts") or event["ts"]

        user_id = context.user_id

        history = conversation_store.get_history(channel_id, thread_ts, user_id)

        set_status(
            status="Thinking...",
            loading_messages=[
                "Teaching the hamsters to type faster…",
                "Untangling the internet cables…",
                "Consulting the office goldfish…",
                "Polishing up the response just for you…",
                "Convincing the AI to stop overthinking…",
            ],
        )

        if history:
            input_items = history + [{"role": "user", "content": text}]
        else:
            input_items = text

        deps = build_reply_deps(client, context, event, is_private_reply=is_dm)
        result = asyncio.run(run_agent(input_items, deps))

        streamer = say_stream()
        streamer.append(markdown_text=result.final_output)
        feedback_blocks = build_feedback_blocks()
        streamer.stop(blocks=feedback_blocks)

        conversation_store.set_history(
            channel_id, thread_ts, user_id, result.to_input_list()
        )

    except Exception as e:
        logger.exception("Failed to handle message")
        say(
            text=f":warning: Something went wrong! ({e})",
            thread_ts=event.get("thread_ts") or event.get("ts"),
        )
