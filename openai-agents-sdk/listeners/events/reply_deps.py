from slack_bolt import BoltContext
from slack_sdk import WebClient

from agent import AgentDeps
from agent.access import is_owner, reply_user_token


def build_reply_deps(
    client: WebClient,
    context: BoltContext,
    event: dict,
    is_private_reply: bool,
) -> AgentDeps:
    return AgentDeps(
        client=client,
        user_id=context.user_id,
        channel_id=context.channel_id,
        thread_ts=event.get("thread_ts") or event["ts"],
        message_ts=event["ts"],
        user_token=reply_user_token(context.user_token, is_private_reply),
        is_owner=is_owner(context.user_id),
        is_private_reply=is_private_reply,
    )
