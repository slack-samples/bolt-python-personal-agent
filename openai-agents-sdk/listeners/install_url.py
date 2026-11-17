import os
from urllib.parse import urljoin

README_MCP_URL = "https://github.com/slack-samples/bolt-python-personal-agent/blob/main/openai-agents-sdk/README.md#slack-mcp-server"


def install_url() -> str | None:
    redirect_uri = os.environ.get("SLACK_REDIRECT_URI")
    if not os.environ.get("SLACK_CLIENT_ID") or not redirect_uri:
        return None
    return urljoin(redirect_uri, "/slack/install")


def connect_message() -> str:
    url = install_url()
    if url:
        return f"Please connect your Slack account first: {url}"
    return f"Please connect your Slack account first. See: {README_MCP_URL}"
