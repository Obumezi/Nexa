"""Tests for the Nexa MCP server."""

from collections.abc import Generator
from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from nexa_api.database import Base
from nexa_api.enums import (
    DeliveryStatus,
    PresenceStatus,
    TaskStatus,
    VisitorStatus,
)
from nexa_api.mcp_server import (
    _cancel_visitor_action,
    _complete_task_action,
    _create_task_action,
    _mark_delivery_collected_action,
    _mark_delivery_delivered_action,
    _mark_visitor_arrived_action,
    _mark_visitor_departed_action,
    _serialize_expected_visitors,
    _serialize_household_presence,
    _serialize_open_tasks,
    _serialize_pending_deliveries,
    _update_presence_action,
)
from nexa_api.models import (
    Delivery,
    ExpectedVisitor,
    HouseholdPresence,
    HouseholdTask,
)


@pytest.fixture
def session() -> Generator[Session, None, None]:
    """Create an isolated in-memory database session for MCP tests."""

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )

    Base.metadata.create_all(bind=engine)

    testing_session_local = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )

    db = testing_session_local()

    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def test_serialize_household_presence_returns_records(
    session: Session,
) -> None:
    """MCP should serialize household presence records."""

    presence = HouseholdPresence(
        occupant_name="Obumneme",
        status=PresenceStatus.HOME,
        since=datetime(2030, 1, 1, 10, 0, tzinfo=UTC),
        note="Working from home",
    )

    session.add(presence)
    session.commit()
    session.refresh(presence)

    result = _serialize_household_presence(session)

    assert len(result) == 1

    assert result[0]["id"] == presence.id
    assert result[0]["occupant_name"] == "Obumneme"
    assert result[0]["status"] == "home"
    assert result[0]["note"] == "Working from home"
    assert result[0]["since"] is not None


def test_serialize_household_presence_returns_empty_list(
    session: Session,
) -> None:
    """MCP should safely return an empty list when nobody is recorded."""

    result = _serialize_household_presence(session)

    assert result == []

def test_serialize_expected_visitors_returns_only_expected(
    session: Session,
) -> None:
    """MCP should expose only visitors who are still expected."""

    expected_visitor = ExpectedVisitor(
        name="Ada Okafor",
        purpose="Dinner",
        expected_start=datetime(2030, 1, 1, 18, 0, tzinfo=UTC),
        expected_end=datetime(2030, 1, 1, 20, 0, tzinfo=UTC),
        status=VisitorStatus.EXPECTED,
    )

    arrived_visitor = ExpectedVisitor(
        name="Chinedu Okafor",
        purpose="Maintenance",
        expected_start=datetime(2030, 1, 1, 10, 0, tzinfo=UTC),
        expected_end=datetime(2030, 1, 1, 11, 0, tzinfo=UTC),
        status=VisitorStatus.ARRIVED,
    )

    session.add_all(
        [
            expected_visitor,
            arrived_visitor,
        ]
    )
    session.commit()

    result = _serialize_expected_visitors(session)

    assert len(result) == 1
    assert result[0]["name"] == "Ada Okafor"
    assert result[0]["purpose"] == "Dinner"
    assert result[0]["status"] == "expected"

def test_serialize_pending_deliveries_returns_only_expected(
    session: Session,
) -> None:
    """MCP should expose only deliveries that are still expected."""

    expected_delivery = Delivery(
        description="Dell Laptop",
        carrier="DHL",
        tracking_reference="NEXA-DHL-001",
        status=DeliveryStatus.EXPECTED,
    )

    delivered_delivery = Delivery(
        description="Office Monitor",
        carrier="UPS",
        tracking_reference="NEXA-UPS-001",
        status=DeliveryStatus.DELIVERED,
    )

    session.add_all(
        [
            expected_delivery,
            delivered_delivery,
        ]
    )
    session.commit()

    result = _serialize_pending_deliveries(session)

    assert len(result) == 1
    assert result[0]["description"] == "Dell Laptop"
    assert result[0]["carrier"] == "DHL"
    assert result[0]["tracking_reference"] == "NEXA-DHL-001"
    assert result[0]["status"] == "expected"

def test_serialize_open_tasks_returns_only_open_tasks(
    session: Session,
) -> None:
    """MCP should expose only household tasks that are still open."""

    open_task = HouseholdTask(
        title="Service the generator",
        description="Arrange generator maintenance",
        status=TaskStatus.OPEN,
    )

    completed_task = HouseholdTask(
        title="Buy groceries",
        description="Weekly grocery shopping",
        status=TaskStatus.COMPLETED,
    )

    session.add_all(
        [
            open_task,
            completed_task,
        ]
    )
    session.commit()

    result = _serialize_open_tasks(session)

    assert len(result) == 1
    assert result[0]["title"] == "Service the generator"
    assert result[0]["description"] == "Arrange generator maintenance"
    assert result[0]["status"] == "open"

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

def test_complete_task_action_requires_confirmation(
    session: Session,
    monkeypatch,
) -> None:
    """MCP task completion should preserve Nexa's confirmation requirement."""

    from nexa_api import mcp_server
    from nexa_api.schemas import AgentIntent, AgentResponse

    expected_response = AgentResponse(
        intent=AgentIntent.COMPLETE_TASK,
        message="Mark 'Service the generator' as completed?",
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

    result = _complete_task_action(
        session,
        "Service the generator",
    )

    assert result["intent"] == "complete_task"
    assert result["requires_confirmation"] is True
    assert result["action_executed"] is False

def test_complete_task_action_passes_confirmation_to_agent(
    session: Session,
    monkeypatch,
) -> None:
    """Confirmed MCP task completion should pass confirm=true to Nexa."""

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
            intent=AgentIntent.COMPLETE_TASK,
            message="Task completed.",
            requires_confirmation=False,
            action_executed=True,
        )

    monkeypatch.setattr(
        mcp_server,
        "run_agent",
        fake_run_agent,
    )

    result = _complete_task_action(
        session,
        "Service the generator",
        confirm=True,
    )

    assert received_confirmation is True
    assert result["intent"] == "complete_task"
    assert result["requires_confirmation"] is False
    assert result["action_executed"] is True

def test_cancel_visitor_action_requires_confirmation(
    session: Session,
    monkeypatch,
) -> None:
    """MCP visitor cancellation should preserve confirmation."""

    from nexa_api import mcp_server
    from nexa_api.schemas import AgentIntent, AgentResponse

    expected_response = AgentResponse(
        intent=AgentIntent.CANCEL_VISITOR,
        message="Cancel Ada Okafor's visit?",
        requires_confirmation=True,
        action_executed=False,
    )

    monkeypatch.setattr(
        mcp_server,
        "run_agent",
        lambda db, message, confirm=False: expected_response,
    )

    result = _cancel_visitor_action(
        session,
        "Ada Okafor",
    )

    assert result["intent"] == "cancel_visitor"
    assert result["requires_confirmation"] is True
    assert result["action_executed"] is False


def test_cancel_visitor_action_passes_confirmation(
    session: Session,
    monkeypatch,
) -> None:
    """Confirmed visitor cancellation should pass confirm=true."""

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
            intent=AgentIntent.CANCEL_VISITOR,
            message="Visitor cancelled.",
            action_executed=True,
        )

    monkeypatch.setattr(
        mcp_server,
        "run_agent",
        fake_run_agent,
    )

    result = _cancel_visitor_action(
        session,
        "Ada Okafor",
        confirm=True,
    )

    assert received_confirmation is True
    assert result["action_executed"] is True


def test_mark_visitor_arrived_action_requires_confirmation(
    session: Session,
    monkeypatch,
) -> None:
    """MCP visitor arrival should preserve confirmation."""

    from nexa_api import mcp_server
    from nexa_api.schemas import AgentIntent, AgentResponse

    expected_response = AgentResponse(
        intent=AgentIntent.MARK_VISITOR_ARRIVED,
        message="Mark Chinedu Okafor as arrived?",
        requires_confirmation=True,
        action_executed=False,
    )

    monkeypatch.setattr(
        mcp_server,
        "run_agent",
        lambda db, message, confirm=False: expected_response,
    )

    result = _mark_visitor_arrived_action(
        session,
        "Chinedu Okafor",
    )

    assert result["intent"] == "mark_visitor_arrived"
    assert result["requires_confirmation"] is True
    assert result["action_executed"] is False


def test_mark_visitor_arrived_action_passes_confirmation(
    session: Session,
    monkeypatch,
) -> None:
    """Confirmed visitor arrival should pass confirm=true."""

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
            intent=AgentIntent.MARK_VISITOR_ARRIVED,
            message="Visitor marked as arrived.",
            action_executed=True,
        )

    monkeypatch.setattr(
        mcp_server,
        "run_agent",
        fake_run_agent,
    )

    result = _mark_visitor_arrived_action(
        session,
        "Chinedu Okafor",
        confirm=True,
    )

    assert received_confirmation is True
    assert result["action_executed"] is True


def test_mark_visitor_departed_action_requires_confirmation(
    session: Session,
    monkeypatch,
) -> None:
    """MCP visitor departure should preserve confirmation."""

    from nexa_api import mcp_server
    from nexa_api.schemas import AgentIntent, AgentResponse

    expected_response = AgentResponse(
        intent=AgentIntent.MARK_VISITOR_DEPARTED,
        message="Mark Chinedu Okafor as departed?",
        requires_confirmation=True,
        action_executed=False,
    )

    monkeypatch.setattr(
        mcp_server,
        "run_agent",
        lambda db, message, confirm=False: expected_response,
    )

    result = _mark_visitor_departed_action(
        session,
        "Chinedu Okafor",
    )

    assert result["intent"] == "mark_visitor_departed"
    assert result["requires_confirmation"] is True
    assert result["action_executed"] is False


def test_mark_visitor_departed_action_passes_confirmation(
    session: Session,
    monkeypatch,
) -> None:
    """Confirmed visitor departure should pass confirm=true."""

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
            intent=AgentIntent.MARK_VISITOR_DEPARTED,
            message="Visitor marked as departed.",
            action_executed=True,
        )

    monkeypatch.setattr(
        mcp_server,
        "run_agent",
        fake_run_agent,
    )

    result = _mark_visitor_departed_action(
        session,
        "Chinedu Okafor",
        confirm=True,
    )

    assert received_confirmation is True
    assert result["action_executed"] is True

def test_mark_delivery_delivered_action_requires_confirmation(
    session: Session,
    monkeypatch,
) -> None:
    """MCP delivery arrival should preserve confirmation."""

    from nexa_api import mcp_server
    from nexa_api.schemas import AgentIntent, AgentResponse

    expected_response = AgentResponse(
        intent=AgentIntent.MARK_DELIVERY_DELIVERED,
        message="Mark Dell Laptop as delivered?",
        requires_confirmation=True,
        action_executed=False,
    )

    monkeypatch.setattr(
        mcp_server,
        "run_agent",
        lambda db, message, confirm=False: expected_response,
    )

    result = _mark_delivery_delivered_action(
        session,
        "Dell Laptop",
    )

    assert result["intent"] == "mark_delivery_delivered"
    assert result["requires_confirmation"] is True
    assert result["action_executed"] is False


def test_mark_delivery_delivered_action_passes_confirmation(
    session: Session,
    monkeypatch,
) -> None:
    """Confirmed delivery arrival should pass confirm=true."""

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
            intent=AgentIntent.MARK_DELIVERY_DELIVERED,
            message="Delivery marked as delivered.",
            action_executed=True,
        )

    monkeypatch.setattr(
        mcp_server,
        "run_agent",
        fake_run_agent,
    )

    result = _mark_delivery_delivered_action(
        session,
        "Dell Laptop",
        confirm=True,
    )

    assert received_confirmation is True
    assert result["action_executed"] is True


def test_mark_delivery_collected_action_requires_confirmation(
    session: Session,
    monkeypatch,
) -> None:
    """MCP delivery collection should preserve confirmation."""

    from nexa_api import mcp_server
    from nexa_api.schemas import AgentIntent, AgentResponse

    expected_response = AgentResponse(
        intent=AgentIntent.MARK_DELIVERY_COLLECTED,
        message="Mark Dell Laptop as collected?",
        requires_confirmation=True,
        action_executed=False,
    )

    monkeypatch.setattr(
        mcp_server,
        "run_agent",
        lambda db, message, confirm=False: expected_response,
    )

    result = _mark_delivery_collected_action(
        session,
        "Dell Laptop",
    )

    assert result["intent"] == "mark_delivery_collected"
    assert result["requires_confirmation"] is True
    assert result["action_executed"] is False


def test_mark_delivery_collected_action_passes_confirmation(
    session: Session,
    monkeypatch,
) -> None:
    """Confirmed delivery collection should pass confirm=true."""

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
            intent=AgentIntent.MARK_DELIVERY_COLLECTED,
            message="Delivery marked as collected.",
            action_executed=True,
        )

    monkeypatch.setattr(
        mcp_server,
        "run_agent",
        fake_run_agent,
    )

    result = _mark_delivery_collected_action(
        session,
        "Dell Laptop",
        confirm=True,
    )

    assert received_confirmation is True
    assert result["action_executed"] is True

def test_update_presence_action_requires_confirmation(
    session: Session,
    monkeypatch,
) -> None:
    """MCP presence updates should preserve confirmation."""

    from nexa_api import mcp_server
    from nexa_api.schemas import AgentIntent, AgentResponse

    expected_response = AgentResponse(
        intent=AgentIntent.UPDATE_PRESENCE,
        message="Update Obumneme's presence to home?",
        requires_confirmation=True,
        action_executed=False,
    )

    monkeypatch.setattr(
        mcp_server,
        "run_agent",
        lambda db, message, confirm=False, speaker_name=None: (
            expected_response
        ),
    )

    result = _update_presence_action(
        session,
        "Obumneme",
        "home",
    )

    assert result["intent"] == "update_presence"
    assert result["requires_confirmation"] is True
    assert result["action_executed"] is False


def test_update_presence_action_passes_confirmation_and_identity(
    session: Session,
    monkeypatch,
) -> None:
    """Confirmed presence updates should preserve identity and confirmation."""

    from nexa_api import mcp_server
    from nexa_api.schemas import AgentIntent, AgentResponse

    received_confirmation = False
    received_speaker_name = None

    def fake_run_agent(
        db: Session,
        message: str,
        confirm: bool = False,
        speaker_name: str | None = None,
    ) -> AgentResponse:
        nonlocal received_confirmation
        nonlocal received_speaker_name

        received_confirmation = confirm
        received_speaker_name = speaker_name

        return AgentResponse(
            intent=AgentIntent.UPDATE_PRESENCE,
            message="Presence updated.",
            action_executed=True,
        )

    monkeypatch.setattr(
        mcp_server,
        "run_agent",
        fake_run_agent,
    )

    result = _update_presence_action(
        session,
        "Obumneme",
        "away",
        confirm=True,
    )

    assert received_confirmation is True
    assert received_speaker_name == "Obumneme"
    assert result["action_executed"] is True


def test_update_presence_action_supports_sleeping(
    session: Session,
    monkeypatch,
) -> None:
    """MCP presence updates should support sleeping status."""

    from nexa_api import mcp_server
    from nexa_api.schemas import AgentIntent, AgentResponse

    received_message = ""

    def fake_run_agent(
        db: Session,
        message: str,
        confirm: bool = False,
        speaker_name: str | None = None,
    ) -> AgentResponse:
        nonlocal received_message

        received_message = message

        return AgentResponse(
            intent=AgentIntent.UPDATE_PRESENCE,
            message="Presence updated.",
            action_executed=True,
        )

    monkeypatch.setattr(
        mcp_server,
        "run_agent",
        fake_run_agent,
    )

    _update_presence_action(
        session,
        "Obumneme",
        "sleeping",
        confirm=True,
    )

    assert received_message == "Obumneme is going to sleep."


def test_update_presence_action_rejects_invalid_status(
    session: Session,
) -> None:
    """MCP should reject unsupported presence states safely."""

    result = _update_presence_action(
        session,
        "Obumneme",
        "vacation",
    )

    assert result["intent"] == "update_presence"
    assert result["requires_confirmation"] is False
    assert result["action_executed"] is False
    assert "Unsupported presence status" in result["message"]