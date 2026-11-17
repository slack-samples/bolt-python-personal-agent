import asyncio
from logging import Logger

from slack_bolt import BoltContext, Say, SayStream, SetStatus
from slack_sdk import WebClient

from agent import run_agent
from agent.reply_deps import build_reply_deps
from listeners.views.feedback_builder import build_feedback_blocks
from thread_context import conversation_store


def handle_app_mentioned(
    client: WebClient,
    context: BoltContext,
    event: dict,
    logger: Logger,
    say: Say,
    say_stream: SayStream,
    set_status: SetStatus,
):
    """Handle @mentions in channels."""
    if event.get("bot_id"):
        return

    try:
        channel_id = context.channel_id
        text = event.get("text", "")
        thread_ts = event.get("thread_ts") or event["ts"]
        user_id = context.user_id

        cleaned_text = text.replace(f"<@{context.bot_user_id}>", "").strip()

        if not cleaned_text:
            say(
                text="Hey there! How can I help you? Ask me anything and I'll do my best.",
                thread_ts=thread_ts,
            )
            return

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

        history = conversation_store.get_history(channel_id, thread_ts, user_id)

        if history:
            input_items = history + [{"role": "user", "content": cleaned_text}]
        else:
            input_items = cleaned_text

        deps = build_reply_deps(client, context, event, is_private_reply=False)
        result = asyncio.run(run_agent(input_items, deps))

        streamer = say_stream()
        streamer.append(markdown_text=result.final_output)
        feedback_blocks = build_feedback_blocks()
        streamer.stop(blocks=feedback_blocks)

        conversation_store.set_history(
            channel_id, thread_ts, user_id, result.to_input_list()
        )

    except Exception as e:
        logger.exception("Failed to handle app mention")
        say(
            text=f":warning: Something went wrong! ({e})",
            thread_ts=event.get("thread_ts") or event["ts"],
        )
