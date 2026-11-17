from listeners.install_url import README_MCP_URL, connect_message, install_url


def test_install_url_with_oauth(monkeypatch):
    monkeypatch.setenv("SLACK_CLIENT_ID", "123.456")
    monkeypatch.setenv("SLACK_REDIRECT_URI", "https://example.com/slack/oauth_redirect")
    assert install_url() == "https://example.com/slack/install"
    assert connect_message() == (
        "Please connect your Slack account first: https://example.com/slack/install"
    )


def test_install_url_without_oauth(monkeypatch):
    monkeypatch.delenv("SLACK_CLIENT_ID", raising=False)
    assert install_url() is None
    assert connect_message() == (
        f"Please connect your Slack account first. See: {README_MCP_URL}"
    )


def test_install_url_without_redirect_uri(monkeypatch):
    monkeypatch.setenv("SLACK_CLIENT_ID", "123.456")
    monkeypatch.delenv("SLACK_REDIRECT_URI", raising=False)
    assert install_url() is None
    assert connect_message() == (
        f"Please connect your Slack account first. See: {README_MCP_URL}"
    )
