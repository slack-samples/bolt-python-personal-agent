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
    is_thread_reply = event.get("thread_ts") is not None

    if not is_dm and event.get("subtype") in LEARNED_SUBTYPES:
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
            if RUNBOOK_WRITES.intersection(result.tool_names):
                client.chat_postEphemeral(
                    channel=context.channel_id,
                    user=context.user_id,
                    thread_ts=event.get("thread_ts"),
                    markdown_text=result.final_output,
                )
        except Exception:
            logger.exception("Failed to learn from message")

    if event.get("subtype"):
        return

    if is_dm:
        pass
    elif f"<@{context.bot_user_id}>" in event.get("text", ""):
        return
    elif is_thread_reply:
        if not conversation_store.has_thread(context.channel_id, event["thread_ts"]):
            return
    else:
        return

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

        deps = build_reply_deps(client, context, event, is_private_reply=is_dm)
        result = asyncio.run(run_agent(text, deps, message_history=history))

        streamer = say_stream()
        streamer.append(markdown_text=result.final_output)
        feedback_blocks = build_feedback_blocks()
        streamer.stop(blocks=feedback_blocks)

        conversation_store.set_history(channel_id, thread_ts, user_id, result.messages)

    except Exception as e:
        logger.exception("Failed to handle message")
        say(
            text=f":warning: Something went wrong! ({e})",
            thread_ts=event.get("thread_ts") or event.get("ts"),
        )
