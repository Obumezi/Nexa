"""Translate Nexa conversational decisions into MCP tool calls."""

from dataclasses import dataclass

from nexa_api.agent_service import resolve_agent_intent
from nexa_api.schemas import AgentDecision, AgentIntent

"""  """



@dataclass(frozen=True)
class MCPToolCall:
    """A planned MCP tool invocation."""

    tool_name: str
    arguments: dict[str, object]


def plan_mcp_tool_call(
    decision: AgentDecision,
    *,
    confirm: bool = False,
    speaker_name: str | None = None,
) -> MCPToolCall | None:
    """Translate an AgentDecision into a Nexa MCP tool call."""

    if decision.intent == AgentIntent.GET_EXPECTED_VISITORS:
        return MCPToolCall(
            tool_name="get_expected_visitors",
            arguments={},
        )

    if decision.intent == AgentIntent.GET_PENDING_DELIVERIES:
        return MCPToolCall(
            tool_name="get_pending_deliveries",
            arguments={},
        )

    if decision.intent == AgentIntent.GET_HOUSEHOLD_PRESENCE:
        return MCPToolCall(
            tool_name="get_household_presence",
            arguments={},
        )

    if decision.intent == AgentIntent.GET_OPEN_TASKS:
        return MCPToolCall(
            tool_name="get_open_tasks",
            arguments={},
        )

    if decision.intent == AgentIntent.CREATE_TASK:
        if not decision.task_title:
            return None

        arguments: dict[str, object] = {
            "title": decision.task_title,
            "confirm": confirm,
        }

        if decision.task_description:
            arguments["description"] = decision.task_description

        return MCPToolCall(
            tool_name="create_task",
            arguments=arguments,
        )

    if decision.intent == AgentIntent.COMPLETE_TASK:
        if not decision.target_task_title:
            return None

        return MCPToolCall(
            tool_name="complete_task",
            arguments={
                "title": decision.target_task_title,
                "confirm": confirm,
            },
        )

    if decision.intent == AgentIntent.CANCEL_VISITOR:
        if not decision.target_visitor_name:
            return None

        return MCPToolCall(
            tool_name="cancel_visitor",
            arguments={
                "visitor_name": decision.target_visitor_name,
                "confirm": confirm,
            },
        )

    if decision.intent == AgentIntent.MARK_VISITOR_ARRIVED:
        if not decision.target_visitor_name:
            return None

        return MCPToolCall(
            tool_name="mark_visitor_arrived",
            arguments={
                "visitor_name": decision.target_visitor_name,
                "confirm": confirm,
            },
        )

    if decision.intent == AgentIntent.MARK_VISITOR_DEPARTED:
        if not decision.target_visitor_name:
            return None

        return MCPToolCall(
            tool_name="mark_visitor_departed",
            arguments={
                "visitor_name": decision.target_visitor_name,
                "confirm": confirm,
            },
        )

    if decision.intent == AgentIntent.MARK_DELIVERY_DELIVERED:
        if not decision.target_delivery_description:
            return None

        return MCPToolCall(
            tool_name="mark_delivery_delivered",
            arguments={
                "description": decision.target_delivery_description,
                "confirm": confirm,
            },
        )

    if decision.intent == AgentIntent.MARK_DELIVERY_COLLECTED:
        if not decision.target_delivery_description:
            return None

        return MCPToolCall(
            tool_name="mark_delivery_collected",
            arguments={
                "description": decision.target_delivery_description,
                "confirm": confirm,
            },
        )

    if decision.intent == AgentIntent.UPDATE_PRESENCE:
        occupant_name = (
            decision.target_occupant_name
            or speaker_name
        )

        if not occupant_name:
            return None

        if not decision.target_presence_status:
            return None

        return MCPToolCall(
            tool_name="update_presence",
            arguments={
                "occupant_name": occupant_name,
                "status": decision.target_presence_status,
                "confirm": confirm,
            },
        )

    return None


def resolve_mcp_tool_call(
    message: str,
    *,
    history: list[dict[str, str]] | None = None,
    speaker_name: str | None = None,
    confirm: bool = False,
) -> MCPToolCall | None:
    """Resolve a conversation message into an MCP tool invocation."""

    if history and speaker_name:
        decision = resolve_agent_intent(
            message,
            history=history,
            speaker_name=speaker_name,
        )
    elif history:
        decision = resolve_agent_intent(
            message,
            history=history,
        )
    elif speaker_name:
        decision = resolve_agent_intent(
            message,
            speaker_name=speaker_name,
        )
    else:
        decision = resolve_agent_intent(message)

    return plan_mcp_tool_call(
        decision,
        confirm=confirm,
        speaker_name=speaker_name,
    )

async def run_mcp_conversation_turn(
    message: str,
    *,
    history: list[dict[str, str]] | None = None,
    speaker_name: str | None = None,
    confirm: bool = False,
    mcp_url: str = "http://127.0.0.1:8000/mcp",
) -> object | None:
    """Resolve a conversational request and execute its MCP tool call."""

    from nexa_api.mcp_executor import execute_mcp_tool_call

    tool_call = resolve_mcp_tool_call(
        message,
        history=history,
        speaker_name=speaker_name,
        confirm=confirm,
    )

    if tool_call is None:
        return None

    return await execute_mcp_tool_call(
        tool_call,
        url=mcp_url,
    )