from listeners.install_url import README_MCP_URL

MCP_SCOPE = (
    "The agent uses the Slack MCP Server as you only in your DMs with the agent "
    "and in `/brief`. Channel replies use the bot token."
)


def build_app_home_view(
    install_url: str | None = None,
    is_connected: bool = False,
    soul_status: str | None = None,
) -> dict:
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "Hey there :wave: I'm a personal agent.",
            },
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    "I answer as my owner's agent, keep runbooks current, "
                    "and never decide for my owner."
                ),
            },
        },
        {"type": "divider"},
    ]

    if soul_status == "template":
        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": ":sparkles: *Your soul isn't set up yet.* Send me a DM and I'll interview you.",
                },
            }
        )
    elif soul_status == "personalized":
        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": ':white_check_mark: *Your soul is set up.* Say "update my soul" anytime.',
                },
            }
        )

    if is_connected:
        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "\U0001f7e2 *Slack MCP Server is connected.*",
                },
            }
        )
        blocks.append(
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": MCP_SCOPE,
                    }
                ],
            }
        )
    elif install_url:
        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"\U0001f534 *Slack MCP Server is disconnected.* <{install_url}|Connect the Slack MCP Server.>",
                },
            }
        )
        blocks.append(
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"Connect the Slack MCP Server. {MCP_SCOPE}",
                    }
                ],
            }
        )
    else:
        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"\U0001f534 *Slack MCP Server is disconnected.* <{README_MCP_URL}|Learn how to enable the Slack MCP Server.>",
                },
            }
        )
        blocks.append(
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"Connect the Slack MCP Server. {MCP_SCOPE}",
                    }
                ],
            }
        )

    return {
        "type": "home",
        "blocks": blocks,
    }
