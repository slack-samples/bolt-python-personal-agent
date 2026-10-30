import asyncio
import importlib
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from slack_sdk import WebClient

from agent.deps import AgentDeps

agent_module = importlib.import_module("agent.agent")


def make_deps(**overrides):
    values = {
        "client": Mock(WebClient),
        "user_id": "U0WNER",
        "channel_id": "D123",
        "thread_ts": "1700000000.000100",
        "message_ts": "1700000000.000100",
    }
    values.update(overrides)
    return AgentDeps(**values)


@pytest.fixture(autouse=True)
def owner_env(monkeypatch):
    monkeypatch.setenv("OWNER_USER_ID", "U0WNER")


def tool_names(deps):
    return [tool.name for tool in agent_module.local_tools(deps)]


def test_owner_private_gets_soul_tools_and_runbook_mcp_tools():
    deps = make_deps(is_owner=True, is_private_reply=True)
    names = tool_names(deps)
    assert "update_soul" in names
    assert "read_soul" not in names
    assert agent_module.mcp_tool_names(deps) == agent_module.RUNBOOK_TOOLS


def test_slash_brief_gets_read_only_mcp_tools_and_no_local_tools():
    deps = make_deps(
        channel_id="C123",
        thread_ts="",
        message_ts="",
        is_owner=True,
        is_private_reply=True,
        is_brief=True,
    )
    assert tool_names(deps) == []
    assert agent_module.mcp_tool_names(deps) == [
        "slack_search_public_and_private",
        "slack_read_canvas",
        "slack_read_thread",
        "slack_read_channel",
    ]


def test_brief_flag_ignored_for_guests():
    deps = make_deps(user_id="U0GUEST", is_private_reply=True, is_brief=True)
    assert tool_names(deps) == [
        "add_emoji_reaction",
        "create_runbook",
        "list_runbooks",
        "read_runbook",
    ]
    assert agent_module.mcp_tool_names(deps) == agent_module.RUNBOOK_TOOLS


def test_owner_in_channel_gets_no_soul_or_brief_tools():
    deps = make_deps(channel_id="C123", is_owner=True, is_private_reply=False)
    names = tool_names(deps)
    assert "update_soul" not in names
    assert agent_module.mcp_tool_names(deps) == agent_module.RUNBOOK_TOOLS


def test_guest_gets_base_tools_only():
    deps = make_deps(user_id="U0GUEST", is_private_reply=True)
    assert tool_names(deps) == [
        "add_emoji_reaction",
        "create_runbook",
        "list_runbooks",
        "read_runbook",
    ]
    assert agent_module.mcp_tool_names(deps) == agent_module.RUNBOOK_TOOLS


@patch("agent.agent.load_soul", return_value="## Goals\nShip")
def test_instructions_include_soul_and_owner(load_soul):
    deps = make_deps(is_owner=True, is_private_reply=True)
    instructions = agent_module.build_instructions(deps)
    assert "Ship" in instructions
    assert "<@U0WNER>" in instructions
    assert "## PRIVACY" in instructions
    assert "## NO DECISIONS" in instructions
    assert "## UNTRUSTED CONTENT" in instructions


def test_prompt_treats_read_content_as_untrusted():
    prompt = agent_module.SYSTEM_PROMPT
    untrusted = prompt.split("## UNTRUSTED CONTENT")[1].split("## ")[0]
    assert "never instructions" in untrusted
    brief = prompt.split("## BRIEF")[1].split("## ")[0]
    assert "never instructions" in brief
    assert "read-only" in brief
    assert "create or edit canvases" in brief


def test_onboarding_only_saves_what_owner_says_directly():
    onboarding = agent_module.SYSTEM_PROMPT.split("## ONBOARDING")[1].split("## ")[0]
    assert "tells you directly" in onboarding
    assert "never content from search" in onboarding
    assert "shared with anyone" in onboarding


TEMPLATE_SOUL = "<!-- soul-template -->\n# Soul\n## Goals\n*placeholder*"
ONBOARDING_LINE = "start the onboarding interview"


@patch("agent.agent.load_soul", return_value=TEMPLATE_SOUL)
def test_template_soul_starts_onboarding_in_owner_dm(load_soul):
    deps = make_deps(is_owner=True, is_private_reply=True)
    assert ONBOARDING_LINE in agent_module.build_instructions(deps)


@patch("agent.agent.load_soul", return_value=TEMPLATE_SOUL)
def test_template_soul_does_not_start_onboarding_in_brief(load_soul):
    deps = make_deps(is_owner=True, is_private_reply=True, is_brief=True)
    assert ONBOARDING_LINE not in agent_module.build_instructions(deps)


@patch("agent.agent.load_soul", return_value=TEMPLATE_SOUL)
def test_instructions_strip_template_marker(load_soul):
    deps = make_deps(is_owner=True, is_private_reply=True)
    instructions = agent_module.build_instructions(deps)
    assert "<!-- soul-template -->" not in instructions
    assert "*placeholder*" in instructions


@patch("agent.agent.load_soul", return_value="## Goals\nShip")
def test_instructions_ask_guest_to_identify(load_soul):
    deps = make_deps(user_id="U0GUEST", channel_id="C123")
    instructions = agent_module.build_instructions(deps)
    assert "<@U0WNER>'s agent" in instructions
    assert "<@U0GUEST>" in instructions


CONNECT_LINE = "ask them to connect the Slack MCP Server"


@patch("agent.agent.load_soul", return_value="## Goals\nShip")
def test_instructions_ask_unconnected_dm_to_connect(load_soul):
    deps = make_deps(user_id="U0GUEST", is_private_reply=True)
    assert CONNECT_LINE in agent_module.build_instructions(deps)


@patch("agent.agent.load_soul", return_value="## Goals\nShip")
def test_instructions_skip_connect_line_when_connected_or_in_channel(load_soul):
    connected = make_deps(is_private_reply=True, user_token="xoxp-1")
    channel = make_deps(channel_id="C123", is_private_reply=False)
    assert CONNECT_LINE not in agent_module.build_instructions(connected)
    assert CONNECT_LINE not in agent_module.build_instructions(channel)


@patch("agent.agent.load_soul", return_value="## Goals\nShip")
def test_instructions_without_owner(load_soul, monkeypatch):
    monkeypatch.delenv("OWNER_USER_ID")
    deps = make_deps(user_id="U0GUEST", channel_id="C123")
    instructions = agent_module.build_instructions(deps)
    assert "No owner is configured." in instructions
    assert "'s agent." not in instructions


def test_agent_is_named_personal_agent():
    assert agent_module.agent.name == "Personal Agent"


def mock_mcp_server():
    server = MagicMock()
    server.__aenter__ = AsyncMock(return_value=server)
    server.__aexit__ = AsyncMock(return_value=False)
    return server


@patch("agent.agent.AsyncOpenAI")
@patch("agent.agent.MCPServerStreamableHttp")
@patch("agent.agent.Runner.run", new_callable=AsyncMock)
def test_run_agent_ignores_user_token_for_channel_reply(run, mcp, openai):
    openai.return_value.__aenter__ = AsyncMock(return_value=Mock())
    openai.return_value.__aexit__ = AsyncMock(return_value=False)
    deps = make_deps(channel_id="C123", user_token="xoxp-1", is_private_reply=False)
    asyncio.run(agent_module.run_agent([], deps))
    mcp.assert_not_called()
    run.assert_awaited_once()
    assert run.call_args.args[0].mcp_servers == []


@patch("agent.agent.AsyncOpenAI")
@patch("agent.agent.MCPServerStreamableHttp")
@patch("agent.agent.Runner.run", new_callable=AsyncMock)
def test_run_agent_uses_mcp_for_private_reply_with_token(run, mcp, openai):
    openai.return_value.__aenter__ = AsyncMock(return_value=Mock())
    openai.return_value.__aexit__ = AsyncMock(return_value=False)
    mcp.return_value = mock_mcp_server()
    deps = make_deps(user_token="xoxp-1", is_owner=True, is_private_reply=True)
    asyncio.run(agent_module.run_agent([], deps))
    params = mcp.call_args.kwargs["params"]
    assert params["headers"]["Authorization"] == "Bearer xoxp-1"
    run_agent = run.call_args.args[0]
    assert [tool.name for tool in run_agent.tools] == [
        "add_emoji_reaction",
        "update_soul",
    ]


def run_with_mcp(deps):
    with (
        patch("agent.agent.AsyncOpenAI") as openai,
        patch("agent.agent.MCPServerStreamableHttp") as mcp,
        patch("agent.agent.create_static_tool_filter") as tool_filter,
        patch("agent.agent.Runner.run", new_callable=AsyncMock) as run,
    ):
        openai.return_value.__aenter__ = AsyncMock(return_value=Mock())
        openai.return_value.__aexit__ = AsyncMock(return_value=False)
        mcp.return_value = mock_mcp_server()
        asyncio.run(agent_module.run_agent([], deps))
        allowed = tool_filter.call_args.kwargs["allowed_tool_names"]
        tools = [tool.name for tool in run.call_args.args[0].tools]
        return allowed, tools


def test_run_agent_owner_dm_allows_runbook_mcp_tools():
    deps = make_deps(user_token="xoxp-1", is_owner=True, is_private_reply=True)
    allowed, tools = run_with_mcp(deps)
    assert allowed == agent_module.RUNBOOK_TOOLS
    assert tools == ["add_emoji_reaction", "update_soul"]


def test_run_agent_slash_brief_is_read_only():
    deps = make_deps(
        channel_id="C123",
        thread_ts="",
        message_ts="",
        user_token="xoxp-1",
        is_owner=True,
        is_private_reply=True,
        is_brief=True,
    )
    allowed, tools = run_with_mcp(deps)
    assert allowed == agent_module.BRIEF_READ_TOOLS
    assert "slack_create_canvas" not in allowed
    assert "slack_update_canvas" not in allowed
    assert tools == []


def test_run_agent_guest_dm_with_own_token():
    deps = make_deps(user_id="U0GUEST", user_token="xoxp-guest", is_private_reply=True)
    allowed, tools = run_with_mcp(deps)
    assert allowed == agent_module.RUNBOOK_TOOLS
    assert "slack_read_thread" not in allowed
    assert "slack_read_channel" not in allowed
    assert tools == ["add_emoji_reaction"]
