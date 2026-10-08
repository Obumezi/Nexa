"""Live end-to-end tests for Nexa MCP over Streamable HTTP."""

import pytest

from nexa_api.mcp_orchestrator import (
    run_mcp_conversation_turn,
)

pytestmark = pytest.mark.anyio


async def test_live_presence_read() -> None:
    """Nexa should read household presence through MCP."""

    result = await run_mcp_conversation_turn(
        "Who is home?",
    )

    assert isinstance(result, dict)
    assert "result" in result
    assert isinstance(result["result"], list)


async def test_live_open_tasks_read() -> None:
    """Nexa should read open tasks through MCP."""

    result = await run_mcp_conversation_turn(
        "What tasks are open?",
    )

    assert isinstance(result, dict)
    assert "result" in result
    assert isinstance(result["result"], list)


async def test_live_create_task_requires_confirmation() -> None:
    """A write action must not execute without confirmation."""

    result = await run_mcp_conversation_turn(
        "Create a task called Live E2E safety test.",
        confirm=False,
    )

    assert isinstance(result, dict)

    assert result["intent"] == "create_task"
    assert result["requires_confirmation"] is True
    assert result["action_executed"] is False


async def test_live_create_task_executes_after_confirmation() -> None:
    """The confirmed write action should execute through MCP."""

    result = await run_mcp_conversation_turn(
        "Create a task called Live E2E confirmation test.",
        confirm=True,
    )

    assert isinstance(result, dict)

    assert result["intent"] == "create_task"
    assert result["requires_confirmation"] is False
    assert result["action_executed"] is True

    created_tasks = result["data"]

    assert isinstance(created_tasks, list)
    assert created_tasks

    assert (
        created_tasks[0]["title"]
        == "Live E2E confirmation test"
    )