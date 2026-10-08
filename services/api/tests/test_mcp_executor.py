"""Tests for Nexa MCP execution."""

import pytest

from nexa_api.mcp_orchestrator import (
    MCPToolCall,
    run_mcp_conversation_turn,
)


@pytest.mark.anyio
async def test_run_mcp_conversation_turn_executes_planned_tool(
    monkeypatch,
) -> None:
    """Conversation turns should execute their planned MCP tool."""

    from nexa_api import mcp_orchestrator

    planned_call = MCPToolCall(
        tool_name="get_open_tasks",
        arguments={},
    )

    received_call = None
    received_url = None

    monkeypatch.setattr(
        mcp_orchestrator,
        "resolve_mcp_tool_call",
        lambda message, **kwargs: planned_call,
    )

    async def fake_execute_mcp_tool_call(
        tool_call: MCPToolCall,
        url: str,
    ) -> object:
        nonlocal received_call
        nonlocal received_url

        received_call = tool_call
        received_url = url

        return {
            "result": [
                {
                    "title": "Service the generator",
                    "status": "open",
                }
            ]
        }

    from nexa_api import mcp_executor

    monkeypatch.setattr(
        mcp_executor,
        "execute_mcp_tool_call",
        fake_execute_mcp_tool_call,
    )

    result = await run_mcp_conversation_turn(
        "What tasks are open?",
        mcp_url="http://test-server/mcp",
    )

    assert received_call == planned_call
    assert received_url == "http://test-server/mcp"

    assert result == {
        "result": [
            {
                "title": "Service the generator",
                "status": "open",
            }
        ]
    }


@pytest.mark.anyio
async def test_run_mcp_conversation_turn_returns_none_when_no_tool(
    monkeypatch,
) -> None:
    """Unsupported conversation turns should not invoke MCP."""

    from nexa_api import mcp_orchestrator

    monkeypatch.setattr(
        mcp_orchestrator,
        "resolve_mcp_tool_call",
        lambda message, **kwargs: None,
    )

    result = await run_mcp_conversation_turn(
        "Tell me a joke.",
    )

    assert result is None


@pytest.mark.anyio
async def test_run_mcp_conversation_turn_preserves_confirmation(
    monkeypatch,
) -> None:
    """Conversation confirmation should reach MCP planning."""

    from nexa_api import mcp_orchestrator

    received_confirm = None

    def fake_resolve(
        message: str,
        **kwargs,
    ) -> MCPToolCall:
        nonlocal received_confirm

        received_confirm = kwargs.get("confirm")

        return MCPToolCall(
            tool_name="complete_task",
            arguments={
                "title": "Service the generator",
                "confirm": kwargs.get("confirm", False),
            },
        )

    monkeypatch.setattr(
        mcp_orchestrator,
        "resolve_mcp_tool_call",
        fake_resolve,
    )

    async def fake_execute(
        tool_call: MCPToolCall,
        url: str,
    ) -> object:
        return {
            "action_executed": tool_call.arguments["confirm"],
        }

    from nexa_api import mcp_executor

    monkeypatch.setattr(
        mcp_executor,
        "execute_mcp_tool_call",
        fake_execute,
    )

    result = await run_mcp_conversation_turn(
        "Mark the generator task done.",
        confirm=True,
    )

    assert received_confirm is True
    assert result == {
        "action_executed": True,
    }