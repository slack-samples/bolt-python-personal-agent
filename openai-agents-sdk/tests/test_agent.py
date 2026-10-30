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


def test_owner_private_gets_soul_and_brief_tools():
    deps = make_deps(is_owner=True, is_private_reply=True)
    names = tool_names(deps)
    assert "read_soul" in names
    assert "update_soul" in names
    assert (
        agent_module.mcp_tool_names(deps)
        == agent_module.RUNBOOK_TOOLS + agent_module.BRIEF_TOOLS
    )


def test_owner_in_channel_gets_no_soul_or_brief_tools():
    deps = make_deps(channel_id="C123", is_owner=True, is_private_reply=False)
    names = tool_names(deps)
    assert "read_soul" not in names
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


@patch("agent.agent.load_soul", return_value="## Goals\nShip")
def test_instructions_ask_guest_to_identify(load_soul):
    deps = make_deps(user_id="U0GUEST", channel_id="C123")
    instructions = agent_module.build_instructions(deps)
    assert "<@U0WNER>'s agent" in instructions
    assert "<@U0GUEST>" in instructions


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
        "read_soul",
        "update_soul",
    ]
