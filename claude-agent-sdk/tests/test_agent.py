import importlib
from unittest.mock import AsyncMock, Mock, patch

import pytest
from claude_agent_sdk import AssistantMessage, ResultMessage, ToolUseBlock
from slack_sdk.web.async_client import AsyncWebClient

from agent.deps import AgentDeps

agent_module = importlib.import_module("agent.agent")


def make_deps(**overrides):
    values = {
        "client": Mock(AsyncWebClient),
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
def test_template_soul_does_not_start_onboarding_for_guest_dm(load_soul):
    deps = make_deps(user_id="U0GUEST", is_private_reply=True)
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
def test_instructions_skip_connect_line_when_connected(load_soul):
    connected = make_deps(is_private_reply=True, user_token="xoxp-1")
    assert CONNECT_LINE not in agent_module.build_instructions(connected)


@patch("agent.agent.load_soul", return_value="## Goals\nShip")
def test_instructions_show_channel_scope_message_without_token(load_soul):
    channel = make_deps(channel_id="C123", is_private_reply=False)
    instructions = agent_module.build_instructions(channel)
    assert "You can only see runbooks shared in this channel." in instructions
    assert CONNECT_LINE not in instructions


@patch("agent.agent.load_soul", return_value="## Goals\nShip")
def test_instructions_without_owner(load_soul, monkeypatch):
    monkeypatch.delenv("OWNER_USER_ID")
    deps = make_deps(user_id="U0GUEST", channel_id="C123")
    instructions = agent_module.build_instructions(deps)
    assert "No owner is configured." in instructions
    assert "'s agent." not in instructions


def result_message(**overrides):
    values = {
        "subtype": "success",
        "duration_ms": 1,
        "duration_api_ms": 1,
        "is_error": False,
        "num_turns": 1,
        "session_id": "session-1",
        "result": "Done.",
    }
    values.update(overrides)
    return ResultMessage(**values)


def fake_sdk_client(messages):
    client = Mock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    client.query = AsyncMock()

    async def receive_response():
        for message in messages:
            yield message

    client.receive_response = receive_response
    return client


async def run_with(deps, messages=None, session_id=None):
    messages = messages if messages is not None else [result_message()]
    with patch("agent.agent.ClaudeSDKClient") as sdk_client:
        sdk_client.return_value = fake_sdk_client(messages)
        result = await agent_module.run_agent("hi", deps, session_id=session_id)
    options = sdk_client.call_args.args[0]
    return options, result


@pytest.mark.asyncio
async def test_run_agent_ignores_user_token_for_channel_reply():
    deps = make_deps(channel_id="C123", user_token="xoxp-1", is_private_reply=False)
    options, _ = await run_with(deps)
    assert "slack-mcp" not in options.mcp_servers
    assert not [t for t in options.allowed_tools if t.startswith("mcp__slack-mcp__")]
    assert "xoxp-1" not in str(options)


@pytest.mark.asyncio
async def test_run_agent_uses_mcp_for_private_reply_with_token():
    deps = make_deps(user_token="xoxp-1", is_owner=True, is_private_reply=True)
    options, _ = await run_with(deps)
    slack_mcp = options.mcp_servers["slack-mcp"]
    assert slack_mcp["url"] == agent_module.SLACK_MCP_URL
    assert slack_mcp["headers"]["Authorization"] == "Bearer xoxp-1"


def allowed_local(options):
    prefix = "mcp__agent-tools__"
    return [t[len(prefix) :] for t in options.allowed_tools if t.startswith(prefix)]


def allowed_mcp(options):
    prefix = "mcp__slack-mcp__"
    return [t[len(prefix) :] for t in options.allowed_tools if t.startswith(prefix)]


@pytest.mark.asyncio
async def test_run_agent_owner_dm_allows_runbook_mcp_tools():
    deps = make_deps(user_token="xoxp-1", is_owner=True, is_private_reply=True)
    options, _ = await run_with(deps)
    assert allowed_mcp(options) == agent_module.RUNBOOK_TOOLS
    assert allowed_local(options) == ["add_emoji_reaction", "update_soul"]


@pytest.mark.asyncio
async def test_run_agent_slash_brief_is_read_only():
    deps = make_deps(
        channel_id="C123",
        thread_ts="",
        message_ts="",
        user_token="xoxp-1",
        is_owner=True,
        is_private_reply=True,
        is_brief=True,
    )
    options, _ = await run_with(deps)
    allowed = allowed_mcp(options)
    assert allowed == agent_module.BRIEF_READ_TOOLS
    assert "slack_create_canvas" not in allowed
    assert "slack_update_canvas" not in allowed
    assert allowed_local(options) == []
    assert "agent-tools" not in options.mcp_servers


@pytest.mark.asyncio
async def test_run_agent_guest_dm_with_own_token():
    deps = make_deps(user_id="U0GUEST", user_token="xoxp-guest", is_private_reply=True)
    options, _ = await run_with(deps)
    allowed = allowed_mcp(options)
    assert allowed == agent_module.RUNBOOK_TOOLS
    assert "slack_read_thread" not in allowed
    assert "slack_read_channel" not in allowed
    assert allowed_local(options) == ["add_emoji_reaction"]


@pytest.mark.asyncio
async def test_run_agent_guest_dm_without_token_gets_no_soul_tools():
    deps = make_deps(user_id="U0GUEST", is_private_reply=True)
    options, _ = await run_with(deps)
    assert "slack-mcp" not in options.mcp_servers
    assert allowed_local(options) == [
        "add_emoji_reaction",
        "create_runbook",
        "list_runbooks",
        "read_runbook",
    ]


@pytest.mark.asyncio
async def test_run_agent_allows_only_listed_tools():
    deps = make_deps(user_token="xoxp-1", is_owner=True, is_private_reply=True)
    options, _ = await run_with(deps)
    assert options.tools == []
    assert options.permission_mode == "dontAsk"
    assert options.setting_sources == []
    assert options.strict_mcp_config is True
    assert options.verbatim_prompts is True
    assert set(options.mcp_servers) == {"agent-tools", "slack-mcp"}
    assert all(t.startswith("mcp__") for t in options.allowed_tools)


@pytest.mark.asyncio
@patch("agent.agent.load_soul", return_value="## Goals\nShip")
async def test_run_agent_uses_the_built_instructions(load_soul):
    deps = make_deps(is_owner=True, is_private_reply=True)
    options, _ = await run_with(deps)
    assert options.system_prompt == agent_module.build_instructions(deps)


@pytest.mark.asyncio
async def test_run_agent_resumes_the_given_session():
    options, result = await run_with(make_deps(), session_id="session-0")
    assert options.resume == "session-0"
    assert result.session_id == "session-1"
    assert result.final_output == "Done."


@pytest.mark.asyncio
async def test_run_agent_reports_tool_calls():
    messages = [
        AssistantMessage(
            content=[
                ToolUseBlock(
                    id="t1",
                    name="mcp__agent-tools__create_runbook",
                    input={},
                )
            ],
            model="claude",
        ),
        result_message(),
    ]
    _, result = await run_with(make_deps(), messages=messages)
    assert result.tool_names == ["mcp__agent-tools__create_runbook"]


@pytest.mark.asyncio
async def test_run_agent_explains_max_turns():
    messages = [result_message(subtype="error_max_turns", result=None)]
    _, result = await run_with(make_deps(), messages=messages)
    assert result.final_output == agent_module.MAX_TURNS_REPLY


@pytest.mark.asyncio
async def test_run_agent_raises_without_a_result():
    with pytest.raises(RuntimeError):
        await run_with(make_deps(), messages=[])
