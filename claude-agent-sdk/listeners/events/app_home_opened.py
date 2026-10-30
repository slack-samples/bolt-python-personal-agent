from logging import Logger

from slack_bolt.context.async_context import AsyncBoltContext
from slack_sdk.web.async_client import AsyncWebClient

from agent.access import is_owner
from agent.soul import is_template, load_soul
from listeners.install_url import install_url
from listeners.views.app_home_builder import build_app_home_view

OWNER_PROMPTS = [
    {
        "title": "Find a Runbook",
        "message": "Is there a runbook for rotating our app's signing secret?",
    },
    {
        "title": "Write a Runbook",
        "message": "Help me write a runbook for onboarding a new teammate",
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


async def handle_app_home_opened(
    client: AsyncWebClient, event: dict, context: AsyncBoltContext, logger: Logger
):
    """Publish App Home view with MCP connection status and soul status for owner, or suggested prompts for the Messages tab."""
    try:
        user_id = context.user_id
        user_is_owner = is_owner(user_id)

        if event.get("tab") == "messages":
            prompts = OWNER_PROMPTS if user_is_owner else GUEST_PROMPTS
            await client.assistant_threads_setSuggestedPrompts(
                channel_id=event["channel"],
                title="How can I help you today?",
                prompts=prompts,
            )
            return

        soul_status = None
        if user_is_owner:
            soul_text = load_soul()
            soul_status = "template" if is_template(soul_text) else "personalized"

        url = install_url()
        is_connected = url is not None and bool(context.user_token)

        view = build_app_home_view(
            install_url=None if is_connected else url,
            is_connected=is_connected,
            soul_status=soul_status,
        )
        await client.views_publish(user_id=user_id, view=view)
    except Exception:
        logger.exception("Failed to handle app_home_opened")
