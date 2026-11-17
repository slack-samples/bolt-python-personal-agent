import asyncio
import importlib
from unittest.mock import Mock, patch

import pytest
from pydantic_ai.messages import ModelResponse, TextPart, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel
from pydantic_ai.toolsets import FunctionToolset
from slack_sdk import WebClient

from agent.deps import AgentDeps
from agent.soul import load_template

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
    return [tool.__name__ for tool in agent_module.local_tools(deps)]


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


def test_learning_run_gets_no_emoji_tool():
    deps = make_deps(channel_id="C123", is_learning=True)
    assert tool_names(deps) == ["create_runbook", "list_runbooks", "read_runbook"]
    assert agent_module.mcp_local_tools(deps) == []


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


TEMPLATE_SOUL = load_template()
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


def test_agent_is_named_personal_agent():
    assert agent_module.agent.name == "Personal Agent"


SLACK_MCP_TOOLS = [
    "slack_add_reaction",
    "slack_create_canvas",
    "slack_create_conversation",
    "slack_get_reactions",
    "slack_list_channel_members",
    "slack_list_unreads",
    "slack_mark_read",
    "slack_read_canvas",
    "slack_read_channel",
    "slack_read_file",
    "slack_read_thread",
    "slack_read_user_profile",
    "slack_schedule_message",
    "slack_search_channels",
    "slack_search_emojis",
    "slack_search_public",
    "slack_search_public_and_private",
    "slack_search_users",
    "slack_send_message",
    "slack_send_message_as_agent",
    "slack_send_message_draft",
    "slack_update_canvas",
]

BOT_TOOLS = ["add_emoji_reaction", "create_runbook", "list_runbooks", "read_runbook"]


def fake_slack_mcp(called=None) -> FunctionToolset:
    toolset = FunctionToolset()
    for name in SLACK_MCP_TOOLS:

        async def call(name: str = name) -> str:
            if called is not None:
                called.append(name)
            return name

        toolset.add_function(call, takes_ctx=False, name=name)
    return toolset


def reply(text="done"):
    def respond(messages, info: AgentInfo) -> ModelResponse:
        return ModelResponse(parts=[TextPart(text)])

    return respond


def run_and_capture(deps, respond=None, message_history=None, called=None):
    seen = {}

    def model(messages, info: AgentInfo) -> ModelResponse:
        seen.setdefault("tools", sorted(tool.name for tool in info.function_tools))
        seen.setdefault("instructions", info.instructions)
        return (respond or reply())(messages, info)

    with (
        patch("agent.agent.MCPToolset", return_value=fake_slack_mcp(called)) as mcp,
        agent_module.agent.override(model=FunctionModel(model)),
    ):
        result = asyncio.run(
            agent_module.run_agent("hi", deps, message_history=message_history)
        )
    return seen, mcp, result


def test_run_agent_ignores_user_token_for_channel_reply():
    deps = make_deps(channel_id="C123", user_token="xoxp-1", is_private_reply=False)
    seen, mcp, result = run_and_capture(deps)
    mcp.assert_not_called()
    assert seen["tools"] == BOT_TOOLS
    assert result.final_output == "done"


def test_run_agent_uses_mcp_for_private_reply_with_token():
    deps = make_deps(user_token="xoxp-1", is_owner=True, is_private_reply=True)
    _, mcp, _ = run_and_capture(deps)
    assert mcp.call_args.args == (agent_module.SLACK_MCP_URL,)
    assert mcp.call_args.kwargs["headers"]["Authorization"] == "Bearer xoxp-1"


def test_run_agent_owner_dm_allows_runbook_mcp_tools():
    deps = make_deps(user_token="xoxp-1", is_owner=True, is_private_reply=True)
    seen, _, _ = run_and_capture(deps)
    assert seen["tools"] == sorted(
        agent_module.RUNBOOK_TOOLS + ["add_emoji_reaction", "update_soul"]
    )


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
    seen, _, _ = run_and_capture(deps)
    assert seen["tools"] == sorted(agent_module.BRIEF_READ_TOOLS)
    assert "slack_create_canvas" not in seen["tools"]
    assert "slack_update_canvas" not in seen["tools"]


def test_run_agent_guest_dm_with_own_token():
    deps = make_deps(user_id="U0GUEST", user_token="xoxp-guest", is_private_reply=True)
    seen, mcp, _ = run_and_capture(deps)
    assert mcp.call_args.kwargs["headers"]["Authorization"] == "Bearer xoxp-guest"
    assert seen["tools"] == sorted(agent_module.RUNBOOK_TOOLS + ["add_emoji_reaction"])
    assert "slack_read_thread" not in seen["tools"]
    assert "slack_read_channel" not in seen["tools"]


def test_run_agent_guest_dm_without_token_gets_no_soul_tools():
    deps = make_deps(user_id="U0GUEST", is_private_reply=True)
    seen, mcp, _ = run_and_capture(deps)
    mcp.assert_not_called()
    assert seen["tools"] == BOT_TOOLS


@pytest.mark.parametrize(
    "deps",
    [
        make_deps(user_token="xoxp-1", is_owner=True, is_private_reply=True),
        make_deps(user_id="U0GUEST", user_token="xoxp-2", is_private_reply=True),
        make_deps(
            user_token="xoxp-1", is_owner=True, is_private_reply=True, is_brief=True
        ),
    ],
)
def test_model_never_sees_mcp_tools_outside_the_allowlist(deps):
    seen, _, _ = run_and_capture(deps)
    allowed = set(agent_module.mcp_tool_names(deps))
    visible_mcp = {name for name in seen["tools"] if name.startswith("slack_")}
    assert visible_mcp == allowed
    assert "slack_send_message" not in seen["tools"]
    assert "slack_search_public" not in seen["tools"]


@patch("agent.agent.load_soul", return_value="## Goals\nShip")
def test_run_agent_sends_built_instructions(load_soul):
    deps = make_deps(is_owner=True, is_private_reply=True)
    seen, _, _ = run_and_capture(deps)
    assert seen["instructions"].strip() == agent_module.build_instructions(deps).strip()


def call_emoji(messages, info: AgentInfo) -> ModelResponse:
    return ModelResponse(
        parts=[ToolCallPart("add_emoji_reaction", {"emoji_name": "tada"})]
    )


def test_run_agent_reports_the_tools_it_called():
    deps = make_deps(channel_id="C123")
    calls = iter([call_emoji, reply()])

    _, _, result = run_and_capture(
        deps, respond=lambda messages, info: next(calls)(messages, info)
    )

    assert result.tool_names == ["add_emoji_reaction"]
    assert result.final_output == "done"


def test_run_agent_tool_names_skip_earlier_history():
    deps = make_deps(channel_id="C123")
    calls = iter([call_emoji, reply()])
    _, _, first = run_and_capture(
        deps, respond=lambda messages, info: next(calls)(messages, info)
    )

    _, _, second = run_and_capture(deps, message_history=first.messages)

    assert second.tool_names == []
    assert len(second.messages) > len(first.messages)


def test_run_agent_stops_at_max_turns_and_can_resume(monkeypatch):
    monkeypatch.setattr(agent_module, "MAX_TURNS", 2)
    deps = make_deps(channel_id="C123")

    _, _, stopped = run_and_capture(deps, respond=call_emoji)

    assert stopped.final_output == agent_module.MAX_TURNS_REPLY
    assert stopped.tool_names == ["add_emoji_reaction", "add_emoji_reaction"]

    _, _, resumed = run_and_capture(deps, message_history=stopped.messages)

    assert resumed.final_output == "done"


def test_model_cannot_call_a_hidden_mcp_tool():
    deps = make_deps(user_token="xoxp-1", is_owner=True, is_private_reply=True)
    called = []
    calls = iter(
        [
            lambda messages, info: ModelResponse(
                parts=[ToolCallPart("slack_send_message", {})]
            ),
            reply(),
        ]
    )

    run_and_capture(
        deps, respond=lambda messages, info: next(calls)(messages, info), called=called
    )

    assert called == []
