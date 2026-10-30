import asyncio
import os
from logging import Logger
from urllib.parse import urljoin

from slack_bolt import BoltContext
from slack_sdk import WebClient

from agent import AgentDeps, run_agent
from agent.access import is_owner, owner_user_id
from agent.brief import BRIEF_PROMPT


def handle_brief(
    ack,
    command: dict,
    client: WebClient,
    context: BoltContext,
    respond,
    logger: Logger,
) -> None:
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
            if os.environ.get("SLACK_CLIENT_ID"):
                redirect_uri = os.environ.get("SLACK_REDIRECT_URI", "")
                install_url = urljoin(redirect_uri, "/slack/install")
                respond(text=f"Please connect your Slack account first: {install_url}")
            else:
                readme_url = "https://github.com/slack-samples/bolt-python-personal-agent/blob/main/openai-agents-sdk/README.md#slack-mcp-server"
                respond(
                    text=f"Please connect your Slack account first. See: {readme_url}"
                )
            return

        deps = AgentDeps(
            client=client,
            user_id=user_id,
            channel_id=command["channel_id"],
            thread_ts="",
            message_ts="",
            user_token=context.user_token,
            is_owner=True,
            is_private_reply=True,
        )

        result = asyncio.run(run_agent(BRIEF_PROMPT, deps))
        respond(text=result.final_output)

    except Exception as e:
        logger.exception("Failed to handle /brief command")
        respond(text=f":warning: Something went wrong! ({e})")
