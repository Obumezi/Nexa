"""Tests for Nexa conversational MCP orchestration."""

from nexa_api.mcp_orchestrator import (
    plan_mcp_tool_call,
    resolve_mcp_tool_call,
)
from nexa_api.schemas import AgentDecision, AgentIntent


def test_plan_open_tasks_read_tool() -> None:
    """Open-task decisions should map to the read MCP tool."""

    decision = AgentDecision(
        intent=AgentIntent.GET_OPEN_TASKS,
        confidence=1.0,
    )

    call = plan_mcp_tool_call(decision)

    assert call is not None
    assert call.tool_name == "get_open_tasks"
    assert call.arguments == {}


def test_plan_create_task_tool() -> None:
    """Task creation should map structured fields into MCP arguments."""

    decision = AgentDecision(
        intent=AgentIntent.CREATE_TASK,
        confidence=0.99,
        task_title="Service the generator",
        task_description="Book generator maintenance",
    )

    call = plan_mcp_tool_call(
        decision,
        confirm=False,
    )

    assert call is not None
    assert call.tool_name == "create_task"
    assert call.arguments == {
        "title": "Service the generator",
        "description": "Book generator maintenance",
        "confirm": False,
    }


def test_plan_complete_task_preserves_confirmation() -> None:
    """Confirmed task completion should pass confirm=true."""

    decision = AgentDecision(
        intent=AgentIntent.COMPLETE_TASK,
        confidence=0.99,
        target_task_title="Service the generator",
    )

    call = plan_mcp_tool_call(
        decision,
        confirm=True,
    )

    assert call is not None
    assert call.tool_name == "complete_task"
    assert call.arguments["confirm"] is True


def test_plan_visitor_arrival_tool() -> None:
    """Visitor arrival decisions should map to the visitor MCP tool."""

    decision = AgentDecision(
        intent=AgentIntent.MARK_VISITOR_ARRIVED,
        confidence=0.99,
        target_visitor_name="Chinedu Okafor",
    )

    call = plan_mcp_tool_call(decision)

    assert call is not None
    assert call.tool_name == "mark_visitor_arrived"
    assert call.arguments["visitor_name"] == "Chinedu Okafor"


def test_plan_delivery_collection_tool() -> None:
    """Delivery collection should map to the correct MCP tool."""

    decision = AgentDecision(
        intent=AgentIntent.MARK_DELIVERY_COLLECTED,
        confidence=0.99,
        target_delivery_description="Dell Laptop",
    )

    call = plan_mcp_tool_call(decision)

    assert call is not None
    assert call.tool_name == "mark_delivery_collected"
    assert call.arguments["description"] == "Dell Laptop"


def test_plan_presence_uses_speaker_identity() -> None:
    """Presence updates may use the current speaker identity."""

    decision = AgentDecision(
        intent=AgentIntent.UPDATE_PRESENCE,
        confidence=0.99,
        target_presence_status="home",
    )

    call = plan_mcp_tool_call(
        decision,
        speaker_name="Obumneme",
    )

    assert call is not None
    assert call.tool_name == "update_presence"
    assert call.arguments["occupant_name"] == "Obumneme"
    assert call.arguments["status"] == "home"


def test_plan_missing_action_target_returns_none() -> None:
    """Incomplete structured actions should not produce an MCP call."""

    decision = AgentDecision(
        intent=AgentIntent.COMPLETE_TASK,
        confidence=0.99,
    )

    assert plan_mcp_tool_call(decision) is None


def test_resolve_mcp_tool_call_uses_conversation_resolver(
    monkeypatch,
) -> None:
    """Conversation resolution should feed the MCP planner."""

    from nexa_api import mcp_orchestrator

    decision = AgentDecision(
        intent=AgentIntent.MARK_VISITOR_ARRIVED,
        confidence=0.99,
        target_visitor_name="Chinedu Okafor",
    )

    monkeypatch.setattr(
        mcp_orchestrator,
        "resolve_agent_intent",
        lambda message: decision,
    )

    call = resolve_mcp_tool_call(
        "Chinedu is here.",
    )

    assert call is not None
    assert call.tool_name == "mark_visitor_arrived"
    assert call.arguments["visitor_name"] == "Chinedu Okafor"