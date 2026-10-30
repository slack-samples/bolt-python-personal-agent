from slack_bolt.async_app import AsyncApp

from listeners.commands import brief


def register(app: AsyncApp):
    app.command("/brief")(brief.handle_brief)
