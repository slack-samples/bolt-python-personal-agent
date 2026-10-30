import os
from logging import Logger
from urllib.parse import urljoin

from slack_bolt import BoltContext
from slack_sdk import WebClient

from agent.access import is_owner
from agent.soul import is_template, load_soul
from listeners.views.app_home_builder import build_app_home_view

OWNER_PROMPTS = [
    {
        "title": "Brief me",
        "message": "Brief me",
    },
    {
        "title": "Find a Runbook",
        "message": "Is there a runbook for rotating our app's signing secret?",
    },
    {
        "title": "Update my soul",
        "message": "Help me update my soul",
    },
]

GUEST_PROMPTS = [
    {
        "title": "Find a Runbook",
        "message": "Is there a runbook for rotating our app's signing secret?",
    },
    {
        "title": "Ask what they're working on",
        "message": "What is your owner working on right now?",
    },
    {
        "title": "Triage a Request",
        "message": "Deploys started failing this morning. What should I do?",
    },
]


def handle_app_home_opened(
    client: WebClient, event: dict, context: BoltContext, logger: Logger
):
    try:
        user_id = context.user_id
        user_is_owner = is_owner(user_id)

        if event.get("tab") == "messages":
            prompts = OWNER_PROMPTS if user_is_owner else GUEST_PROMPTS
            client.assistant_threads_setSuggestedPrompts(
                channel_id=event["channel"],
                title="How can I help you today?",
                prompts=prompts,
            )
            return

        soul_status = None
        if user_is_owner:
            soul_text = load_soul()
            soul_status = "template" if is_template(soul_text) else "personalized"

        install_url = None
        is_connected = False

        if os.environ.get("SLACK_CLIENT_ID"):
            if context.user_token:
                is_connected = True
            else:
                redirect_uri = os.environ.get("SLACK_REDIRECT_URI", "")
                install_url = urljoin(redirect_uri, "/slack/install")

        view = build_app_home_view(
            install_url=install_url, is_connected=is_connected, soul_status=soul_status
        )
        client.views_publish(user_id=user_id, view=view)
    except Exception:
        logger.exception("Failed to handle app_home_opened")
