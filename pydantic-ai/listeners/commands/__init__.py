from slack_bolt import App

from listeners.commands import brief


def register(app: App):
    app.command("/brief")(brief.handle_brief)
