from listeners.views.app_home_builder import build_app_home_view
from listeners.views.feedback_builder import build_feedback_blocks


def test_build_feedback_blocks():
    blocks = build_feedback_blocks()

    assert len(blocks) > 0
    block_dict = blocks[0].to_dict()
    action_ids = [e["action_id"] for e in block_dict["elements"]]
    assert "feedback" in action_ids


def test_build_app_home_view_default():
    """Default args (Socket Mode) — shows disconnected status with learn-more link."""
    view = build_app_home_view()

    assert view["type"] == "home"

    # Should have a header and a section
    block_types = [b["type"] for b in view["blocks"]]
    assert "header" in block_types
    assert "section" in block_types

    # Shows MCP status as disconnected with learn-more link
    section_texts = [
        b["text"]["text"] for b in view["blocks"] if b["type"] == "section"
    ]
    mcp_section = next(t for t in section_texts if "Slack MCP Server" in t)
    assert "disconnected" in mcp_section
    assert "Learn how to enable" in mcp_section


def test_build_app_home_view_connect():
    """install_url provided — shows disconnected status with install link."""
    view = build_app_home_view(install_url="https://example.com/slack/install")

    section_texts = [
        b["text"]["text"] for b in view["blocks"] if b["type"] == "section"
    ]
    mcp_section = next(t for t in section_texts if "Slack MCP Server" in t)
    assert "disconnected" in mcp_section
    assert "https://example.com/slack/install" in mcp_section


def test_build_app_home_view_connected():
    """is_connected=True — shows connected status."""
    view = build_app_home_view(is_connected=True)

    section_texts = [
        b["text"]["text"] for b in view["blocks"] if b["type"] == "section"
    ]
    mcp_section = next(t for t in section_texts if "Slack MCP Server" in t)
    assert "connected" in mcp_section


def test_build_app_home_view_soul_status_template():
    """soul_status='template' — shows setup prompt."""
    view = build_app_home_view(soul_status="template")

    section_texts = [
        b["text"]["text"] for b in view["blocks"] if b["type"] == "section"
    ]
    soul_section = next((t for t in section_texts if "soul" in t.lower()), None)
    assert soul_section is not None
    assert "isn't set up" in soul_section
    assert ":sparkles:" in soul_section


def test_build_app_home_view_soul_status_personalized():
    """soul_status='personalized' — shows personalized status."""
    view = build_app_home_view(soul_status="personalized")

    section_texts = [
        b["text"]["text"] for b in view["blocks"] if b["type"] == "section"
    ]
    soul_section = next((t for t in section_texts if "soul" in t.lower()), None)
    assert soul_section is not None
    assert "is set up" in soul_section
    assert ":white_check_mark:" in soul_section


def test_build_app_home_view_soul_status_none():
    """soul_status=None — no soul status section."""
    view = build_app_home_view(soul_status=None)

    section_texts = [
        b["text"]["text"] for b in view["blocks"] if b["type"] == "section"
    ]
    soul_sections = [t for t in section_texts if "soul" in t.lower()]
    assert len(soul_sections) == 0


def context_texts(view):
    return [
        element["text"]
        for block in view["blocks"]
        if block["type"] == "context"
        for element in block["elements"]
    ]


def test_build_app_home_view_scopes_mcp_to_dms():
    for view in (
        build_app_home_view(),
        build_app_home_view(install_url="https://example.com/slack/install"),
        build_app_home_view(is_connected=True),
    ):
        mcp_context = next(t for t in context_texts(view) if "Slack MCP Server" in t)
        assert "only in your DMs with the agent" in mcp_context
