"""Nexa MCP server.

Exposes Nexa capabilities through the Model Context Protocol using
Streamable HTTP transport.
"""

from mcp.server.mcpserver import MCPServer
from sqlalchemy.orm import Session

from nexa_api.agent_service import run_agent
from nexa_api.database import SessionLocal
from nexa_api.delivery_service import list_deliveries
from nexa_api.enums import DeliveryStatus, TaskStatus, VisitorStatus
from nexa_api.presence_service import list_presence
from nexa_api.schemas import AgentResponse
from nexa_api.task_service import list_tasks
from nexa_api.visitor_service import list_visitors
from mcp.server.transport_security import TransportSecuritySettings

mcp = MCPServer("Nexa")


def _serialize_household_presence(
    session: Session,
) -> list[dict[str, object]]:
    """Return household presence records in an MCP-safe format."""

    records = list_presence(session)

    return [
        {
            "id": record.id,
            "occupant_name": record.occupant_name,
            "status": record.status.value,
            "since": record.since.isoformat() if record.since else None,
            "note": record.note,
        }
        for record in records
    ]


def _serialize_expected_visitors(
    session: Session,
) -> list[dict[str, object]]:
    """Return currently expected visitors in an MCP-safe format."""

    visitors = list_visitors(
        session,
        status=VisitorStatus.EXPECTED,
    )

    return [
        {
            "id": visitor.id,
            "name": visitor.name,
            "purpose": visitor.purpose,
            "status": visitor.status.value,
            "expected_start": (
                visitor.expected_start.isoformat()
                if visitor.expected_start
                else None
            ),
            "expected_end": (
                visitor.expected_end.isoformat()
                if visitor.expected_end
                else None
            ),
        }
        for visitor in visitors
    ]


def _serialize_pending_deliveries(
    session: Session,
) -> list[dict[str, object]]:
    """Return currently expected deliveries in an MCP-safe format."""

    deliveries = list_deliveries(
        session,
        status=DeliveryStatus.EXPECTED,
    )

    return [
        {
            "id": delivery.id,
            "description": delivery.description,
            "carrier": delivery.carrier,
            "tracking_reference": delivery.tracking_reference,
            "status": delivery.status.value,
            "expected_at": (
                delivery.expected_at.isoformat()
                if delivery.expected_at
                else None
            ),
            "delivery_location": delivery.delivery_location,
        }
        for delivery in deliveries
    ]


def _serialize_open_tasks(
    session: Session,
) -> list[dict[str, object]]:
    """Return currently open household tasks in an MCP-safe format."""

    tasks = list_tasks(
        session,
        status=TaskStatus.OPEN,
    )

    return [
        {
            "id": task.id,
            "title": task.title,
            "description": task.description,
            "status": task.status.value,
            "priority": task.priority.value,
            "requires_confirmation": task.requires_confirmation,
            "due_at": task.due_at.isoformat() if task.due_at else None,
        }
        for task in tasks
    ]


def _serialize_agent_response(
    response: AgentResponse,
) -> dict[str, object]:
    """Convert an AgentResponse into an MCP-safe dictionary."""

    return {
        "intent": response.intent.value,
        "message": response.message,
        "data": response.data,
        "requires_confirmation": response.requires_confirmation,
        "action_executed": response.action_executed,
        "proposed_action": response.proposed_action,
        "session_id": response.session_id,
    }


def _create_task_action(
    session: Session,
    title: str,
    description: str | None = None,
    confirm: bool = False,
) -> dict[str, object]:
    """Run Nexa's existing safe task-creation flow."""

    message = f"Create a task called {title}."

    if description:
        message += f" Description: {description}."

    response = run_agent(
        session,
        message,
        confirm=confirm,
    )

    return _serialize_agent_response(response)

def _complete_task_action(
    session: Session,
    title: str,
    confirm: bool = False,
) -> dict[str, object]:
    """Run Nexa's existing safe task-completion flow."""

    message = f"Mark {title} as done."

    response = run_agent(
        session,
        message,
        confirm=confirm,
    )

    return _serialize_agent_response(response)

def _cancel_visitor_action(
    session: Session,
    visitor_name: str,
    confirm: bool = False,
) -> dict[str, object]:
    """Run Nexa's safe visitor-cancellation flow."""

    message = f"Cancel {visitor_name}'s visit."

    response = run_agent(
        session,
        message,
        confirm=confirm,
    )

    return _serialize_agent_response(response)


def _mark_visitor_arrived_action(
    session: Session,
    visitor_name: str,
    confirm: bool = False,
) -> dict[str, object]:
    """Run Nexa's safe visitor-arrival flow."""

    message = f"{visitor_name} has arrived."

    response = run_agent(
        session,
        message,
        confirm=confirm,
    )

    return _serialize_agent_response(response)


def _mark_visitor_departed_action(
    session: Session,
    visitor_name: str,
    confirm: bool = False,
) -> dict[str, object]:
    """Run Nexa's safe visitor-departure flow."""

    message = f"{visitor_name} has left."

    response = run_agent(
        session,
        message,
        confirm=confirm,
    )

    return _serialize_agent_response(response)


def _mark_delivery_delivered_action(
    session: Session,
    description: str,
    confirm: bool = False,
) -> dict[str, object]:
    """Run Nexa's safe delivery-arrival flow."""

    message = f"The {description} package has arrived."

    response = run_agent(
        session,
        message,
        confirm=confirm,
    )

    return _serialize_agent_response(response)


def _mark_delivery_collected_action(
    session: Session,
    description: str,
    confirm: bool = False,
) -> dict[str, object]:
    """Run Nexa's safe delivery-collection flow."""

    message = f"Mark the {description} package as collected."

    response = run_agent(
        session,
        message,
        confirm=confirm,
    )

    return _serialize_agent_response(response)


def _update_presence_action(
    session: Session,
    occupant_name: str,
    status: str,
    confirm: bool = False,
) -> dict[str, object]:
    """Run Nexa's safe household-presence update flow."""

    normalized_status = status.strip().casefold()

    if normalized_status == "home":
        message = f"{occupant_name} is home."
    elif normalized_status == "away":
        message = f"{occupant_name} is leaving."
    elif normalized_status == "sleeping":
        message = f"{occupant_name} is going to sleep."
    else:
        return {
            "intent": "update_presence",
            "message": (
                "Unsupported presence status. "
                "Use home, away, or sleeping."
            ),
            "data": [],
            "requires_confirmation": False,
            "action_executed": False,
            "proposed_action": None,
            "session_id": None,
        }

    response = run_agent(
        session,
        message,
        confirm=confirm,
        speaker_name=occupant_name,
    )

    return _serialize_agent_response(response)


@mcp.tool()
def nexa_status() -> dict[str, str]:
    """Check whether the Nexa MCP server is available."""

    return {
        "name": "Nexa",
        "status": "available",
        "transport": "streamable-http",
    }


@mcp.tool()
def get_household_presence() -> list[dict[str, object]]:
    """Get the current presence status of household occupants."""

    with SessionLocal() as session:
        return _serialize_household_presence(session)


@mcp.tool()
def get_expected_visitors() -> list[dict[str, object]]:
    """Get visitors who are currently expected by the household."""

    with SessionLocal() as session:
        return _serialize_expected_visitors(session)


@mcp.tool()
def get_pending_deliveries() -> list[dict[str, object]]:
    """Get deliveries that are currently expected by the household."""

    with SessionLocal() as session:
        return _serialize_pending_deliveries(session)


@mcp.tool()
def get_open_tasks() -> list[dict[str, object]]:
    """Get household tasks that are currently open."""

    with SessionLocal() as session:
        return _serialize_open_tasks(session)


@mcp.tool()
def create_task(
    title: str,
    description: str | None = None,
    confirm: bool = False,
) -> dict[str, object]:
    """Create a household task through Nexa's safe agent workflow.

    Call initially with confirm=false. If Nexa returns
    requires_confirmation=true, ask the user for confirmation and call
    the tool again with confirm=true only after the user agrees.
    """

    with SessionLocal() as session:
        return _create_task_action(
            session,
            title,
            description=description,
            confirm=confirm,
        )

@mcp.tool()
def complete_task(
    title: str,
    confirm: bool = False,
) -> dict[str, object]:
    """Complete an open household task through Nexa's safe agent workflow.

    Call initially with confirm=false. If Nexa returns
    requires_confirmation=true, ask the user for confirmation and call
    the tool again with confirm=true only after the user agrees.
    """

    with SessionLocal() as session:
        return _complete_task_action(
            session,
            title,
            confirm=confirm,
        )

@mcp.tool()
def cancel_visitor(
    visitor_name: str,
    confirm: bool = False,
) -> dict[str, object]:
    """Cancel an expected visitor through Nexa's safe agent workflow.

    Call initially with confirm=false. If confirmation is required,
    ask the user before calling again with confirm=true.
    """

    with SessionLocal() as session:
        return _cancel_visitor_action(
            session,
            visitor_name,
            confirm=confirm,
        )


@mcp.tool()
def mark_visitor_arrived(
    visitor_name: str,
    confirm: bool = False,
) -> dict[str, object]:
    """Mark an expected visitor as arrived through Nexa's safe workflow.

    Call initially with confirm=false. If confirmation is required,
    ask the user before calling again with confirm=true.
    """

    with SessionLocal() as session:
        return _mark_visitor_arrived_action(
            session,
            visitor_name,
            confirm=confirm,
        )


@mcp.tool()
def mark_visitor_departed(
    visitor_name: str,
    confirm: bool = False,
) -> dict[str, object]:
    """Mark an arrived visitor as departed through Nexa's safe workflow.

    Call initially with confirm=false. If confirmation is required,
    ask the user before calling again with confirm=true.
    """

    with SessionLocal() as session:
        return _mark_visitor_departed_action(
            session,
            visitor_name,
            confirm=confirm,
        )

@mcp.tool()
def mark_delivery_delivered(
    description: str,
    confirm: bool = False,
) -> dict[str, object]:
    """Mark an expected delivery as delivered through Nexa's safe workflow.

    Call initially with confirm=false. If confirmation is required,
    ask the user before calling again with confirm=true.
    """

    with SessionLocal() as session:
        return _mark_delivery_delivered_action(
            session,
            description,
            confirm=confirm,
        )


@mcp.tool()
def mark_delivery_collected(
    description: str,
    confirm: bool = False,
) -> dict[str, object]:
    """Mark a delivered package as collected through Nexa's safe workflow.

    Call initially with confirm=false. If confirmation is required,
    ask the user before calling again with confirm=true.
    """

    with SessionLocal() as session:
        return _mark_delivery_collected_action(
            session,
            description,
            confirm=confirm,
        )

@mcp.tool()
def update_presence(
    occupant_name: str,
    status: str,
    confirm: bool = False,
) -> dict[str, object]:
    """Update a household occupant's presence through Nexa's safe workflow.

    Supported statuses are home, away, and sleeping.

    Call initially with confirm=false. If Nexa returns
    requires_confirmation=true, ask the user before calling again
    with confirm=true.
    """

    with SessionLocal() as session:
        return _update_presence_action(
            session,
            occupant_name,
            status,
            confirm=confirm,
        )


def main() -> None:
    """Run the Nexa MCP server using Streamable HTTP."""

    mcp.run(
        transport="streamable-http",
        host="127.0.0.1",
        port=8001,
        stateless_http=True,
        json_response=True,
    )

def build_mcp_app():
    """Return Nexa's MCP Streamable HTTP ASGI application."""

    security = TransportSecuritySettings(
        enable_dns_rebinding_protection=False,
    )

    return mcp.streamable_http_app(
        streamable_http_path="/",
        stateless_http=True,
        json_response=True,
        transport_security=security,
    )


if __name__ == "__main__":
    main()

def test_create_task_action_requires_confirmation(
    session: Session,
    monkeypatch,
) -> None:
    """MCP task creation should preserve Nexa's confirmation requirement."""

    from nexa_api import mcp_server
    from nexa_api.schemas import AgentIntent, AgentResponse

    expected_response = AgentResponse(
        intent=AgentIntent.CREATE_TASK,
        message="Create the task 'Service the generator'?",
        requires_confirmation=True,
        action_executed=False,
        proposed_action={
            "title": "Service the generator",
        },
    )

    monkeypatch.setattr(
        mcp_server,
        "run_agent",
        lambda db, message, confirm=False: expected_response,
    )

    result = _create_task_action(
        session,
        "Service the generator",
    )

    assert result["intent"] == "create_task"
    assert result["requires_confirmation"] is True
    assert result["action_executed"] is False


def test_create_task_action_passes_confirmation_to_agent(
    session: Session,
    monkeypatch,
) -> None:
    """Confirmed MCP task creation should pass confirm=true to Nexa."""

    from nexa_api import mcp_server
    from nexa_api.schemas import AgentIntent, AgentResponse

    received_confirmation = False

    def fake_run_agent(
        db: Session,
        message: str,
        confirm: bool = False,
    ) -> AgentResponse:
        nonlocal received_confirmation

        received_confirmation = confirm

        return AgentResponse(
            intent=AgentIntent.CREATE_TASK,
            message="Task created.",
            requires_confirmation=False,
            action_executed=True,
        )

    monkeypatch.setattr(
        mcp_server,
        "run_agent",
        fake_run_agent,
    )

    result = _create_task_action(
        session,
        "Service the generator",
        confirm=True,
    )

    assert received_confirmation is True
    assert result["intent"] == "create_task"
    assert result["requires_confirmation"] is False
    assert result["action_executed"] is True