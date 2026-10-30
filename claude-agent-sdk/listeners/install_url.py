import os
from urllib.parse import urljoin

README_MCP_URL = "https://github.com/slack-samples/bolt-python-personal-agent/blob/main/claude-agent-sdk/README.md#slack-mcp-server"


def install_url() -> str | None:
    if not os.environ.get("SLACK_CLIENT_ID"):
        return None
    redirect_uri = os.environ.get("SLACK_REDIRECT_URI", "")
    return urljoin(redirect_uri, "/slack/install")


def connect_message() -> str:
    url = install_url()
    if url:
        return f"Please connect your Slack account first: {url}"
    return f"Please connect your Slack account first. See: {README_MCP_URL}"
