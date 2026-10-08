from collections.abc import Generator
from datetime import datetime
from unittest.mock import Mock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from nexa_api.agent_service import (
    find_delivered_delivery_fuzzy,
    find_expected_delivery_fuzzy,
    find_expected_visitor_fuzzy,
    find_open_task_fuzzy,
    resolve_intent,
    run_agent,
)
from nexa_api.database import Base
from nexa_api.delivery_service import (
    create_delivery,
    list_deliveries,
    mark_delivery_delivered,
)
from nexa_api.enums import DeliveryStatus, PresenceStatus, TaskStatus, VisitorStatus
from nexa_api.models import Delivery, ExpectedVisitor, HouseholdPresence, HouseholdTask
from nexa_api.presence_service import create_presence
from nexa_api.schemas import (
    AgentDecision,
    AgentIntent,
    DeliveryCreate,
    PresenceCreate,
    TaskCreate,
    VisitorCreate,
)
from nexa_api.task_service import (
    create_task,
    list_tasks,
)
from nexa_api.visitor_service import (
    create_visitor,
    list_visitors,
    mark_visitor_arrived,
)


@pytest.fixture
def session() -> Generator[Session, None, None]:
    """Provide an isolated in-memory database session."""

    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    Base.metadata.create_all(engine)

    session_factory = sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )

    with session_factory() as database_session:
        yield database_session

    Base.metadata.drop_all(engine)
    engine.dispose()


def test_resolve_expected_visitors_intent() -> None:
    decision = resolve_intent(
        "Who is coming today?"
    )

    assert decision.intent == AgentIntent.GET_EXPECTED_VISITORS


def test_resolve_pending_delivery_intent() -> None:
    decision = resolve_intent(
        "Do I have any expected deliveries coming?"
    )

    assert decision.intent == AgentIntent.GET_PENDING_DELIVERIES


def test_resolve_presence_intent() -> None:
    decision = resolve_intent(
        "Who is home?"
    )

    assert decision.intent == AgentIntent.GET_HOUSEHOLD_PRESENCE


def test_resolve_open_tasks_intent() -> None:
    decision = resolve_intent(
        "What needs to be done?"
    )

    assert decision.intent == AgentIntent.GET_OPEN_TASKS


def test_unknown_intent() -> None:
    decision = resolve_intent(
        "Play some jazz."
    )

    assert decision.intent == AgentIntent.UNKNOWN


def test_agent_returns_open_tasks(
    session: Session,
) -> None:
    create_task(
        session,
        TaskCreate(
            title="Take out the bins",
        ),
    )

    response = run_agent(
        session,
        "What needs to be done?",
    )

    assert response.intent == AgentIntent.GET_OPEN_TASKS
    assert len(response.data) == 1
    assert response.data[0]["title"] == "Take out the bins"


def test_agent_returns_presence(
    session: Session,
) -> None:
    create_presence(
        session,
        PresenceCreate(
            occupant_name="Obumneme",
            status=PresenceStatus.HOME,
        ),
    )

    response = run_agent(
        session,
        "Who is home?",
    )

    assert response.intent == AgentIntent.GET_HOUSEHOLD_PRESENCE
    assert len(response.data) == 1
    assert response.data[0]["occupant_name"] == "Obumneme"

def test_hybrid_resolver_uses_deterministic_intent_first(
    monkeypatch,
) -> None:
    """Known phrases should not require the LLM."""

    from nexa_api import agent_service

    mock_llm = Mock()
    monkeypatch.setattr(
        agent_service,
        "resolve_intent_with_llm",
        mock_llm,
    )

    decision = agent_service.resolve_agent_intent(
        "Who is home?"
    )

    assert decision.intent == AgentIntent.GET_HOUSEHOLD_PRESENCE
    mock_llm.assert_not_called()


def test_hybrid_resolver_uses_llm_for_unknown_phrase(
    monkeypatch,
) -> None:
    """Unknown local wording should fall through to the LLM."""

    from nexa_api import agent_service

    expected = AgentDecision(
        intent=AgentIntent.GET_PENDING_DELIVERIES,
        confidence=0.91,
    )

    mock_llm = Mock(return_value=expected)

    monkeypatch.setattr(
        agent_service,
        "resolve_intent_with_llm",
        mock_llm,
    )

    decision = agent_service.resolve_agent_intent(
        "Anything on its way to the house?"
    )

    assert decision.intent == AgentIntent.GET_PENDING_DELIVERIES
    assert decision.confidence == 0.91

    mock_llm.assert_called_once_with(
        "Anything on its way to the house?"
    )

def test_create_task_requires_confirmation(
    session: Session,
    monkeypatch,
) -> None:
    """A task request should be proposed before execution."""

    from nexa_api import agent_service

    decision = AgentDecision(
        intent=AgentIntent.CREATE_TASK,
        confidence=0.98,
        task_title="Call the plumber",
        task_description="Arrange a visit to inspect the kitchen sink.",
    )

    monkeypatch.setattr(
        agent_service,
        "resolve_agent_intent",
        lambda message: decision,
    )

    response = agent_service.run_agent(
        session,
        "Create a task to call the plumber.",
    )

    assert response.intent == AgentIntent.CREATE_TASK
    assert response.requires_confirmation is True
    assert response.action_executed is False
    assert response.proposed_action is not None
    assert (
        response.proposed_action["title"]
        == "Call the plumber"
    )

    tasks = list_tasks(session)

    assert tasks == []


def test_confirmed_create_task_executes(
    session: Session,
    monkeypatch,
) -> None:
    """A confirmed task proposal should create the task."""

    from nexa_api import agent_service

    decision = AgentDecision(
        intent=AgentIntent.CREATE_TASK,
        confidence=0.99,
        task_title="Call the plumber",
        task_description="Arrange a kitchen sink inspection.",
    )

    monkeypatch.setattr(
        agent_service,
        "resolve_agent_intent",
        lambda message: decision,
    )

    response = agent_service.run_agent(
        session,
        "Create a task to call the plumber.",
        confirm=True,
    )

    assert response.intent == AgentIntent.CREATE_TASK
    assert response.requires_confirmation is False
    assert response.action_executed is True
    assert len(response.data) == 1
    assert response.data[0]["title"] == "Call the plumber"

    tasks = list_tasks(session)

    assert len(tasks) == 1
    assert tasks[0].title == "Call the plumber"


def test_create_task_without_title_is_not_executed(
    session: Session,
    monkeypatch,
) -> None:
    """Incomplete LLM task decisions should fail safely."""

    from nexa_api import agent_service

    decision = AgentDecision(
        intent=AgentIntent.CREATE_TASK,
        confidence=0.75,
    )

    monkeypatch.setattr(
        agent_service,
        "resolve_agent_intent",
        lambda message: decision,
    )

    response = agent_service.run_agent(
        session,
        "Create something for me.",
        confirm=True,
    )

    assert response.intent == AgentIntent.UNKNOWN
    assert response.action_executed is False

    assert list_tasks(session) == []

def test_complete_task_requires_confirmation(
    session: Session,
    monkeypatch,
) -> None:
    """Completing a task should require confirmation."""

    from nexa_api import agent_service

    task = create_task(
        session,
        TaskCreate(
            title="Service the generator",
        ),
    )

    decision = AgentDecision(
        intent=AgentIntent.COMPLETE_TASK,
        confidence=0.99,
        target_task_title="Service the generator",
    )

    monkeypatch.setattr(
        agent_service,
        "resolve_agent_intent",
        lambda message: decision,
    )

    response = agent_service.run_agent(
        session,
        "Mark service the generator as done.",
    )

    assert response.intent == AgentIntent.COMPLETE_TASK
    assert response.requires_confirmation is True
    assert response.action_executed is False
    assert response.proposed_action is not None
    assert response.proposed_action["task_id"] == task.id

    session.refresh(task)

    assert task.status == TaskStatus.OPEN
    assert task.completed_at is None


def test_confirmed_complete_task_executes(
    session: Session,
    monkeypatch,
) -> None:
    """A confirmed completion should update the task."""

    from nexa_api import agent_service

    task = create_task(
        session,
        TaskCreate(
            title="Service the generator",
        ),
    )

    decision = AgentDecision(
        intent=AgentIntent.COMPLETE_TASK,
        confidence=0.99,
        target_task_title="Service the generator",
    )

    monkeypatch.setattr(
        agent_service,
        "resolve_agent_intent",
        lambda message: decision,
    )

    response = agent_service.run_agent(
        session,
        "Mark service the generator as done.",
        confirm=True,
    )

    assert response.intent == AgentIntent.COMPLETE_TASK
    assert response.requires_confirmation is False
    assert response.action_executed is True
    assert response.data[0]["status"] == "completed"

    session.refresh(task)

    assert task.status == TaskStatus.COMPLETED
    assert task.completed_at is not None


def test_complete_task_missing_target_fails_safely(
    session: Session,
    monkeypatch,
) -> None:
    """Missing task target should not mutate anything."""

    from nexa_api import agent_service

    decision = AgentDecision(
        intent=AgentIntent.COMPLETE_TASK,
        confidence=0.80,
    )

    monkeypatch.setattr(
        agent_service,
        "resolve_agent_intent",
        lambda message: decision,
    )

    response = agent_service.run_agent(
        session,
        "Mark it as done.",
        confirm=True,
    )

    assert response.intent == AgentIntent.UNKNOWN
    assert response.action_executed is False


def test_complete_task_unknown_title_does_not_execute(
    session: Session,
    monkeypatch,
) -> None:
    """Unknown task names should not complete another task."""

    from nexa_api import agent_service

    create_task(
        session,
        TaskCreate(
            title="Service the generator",
        ),
    )

    decision = AgentDecision(
        intent=AgentIntent.COMPLETE_TASK,
        confidence=0.95,
        target_task_title="Repair the roof",
    )

    monkeypatch.setattr(
        agent_service,
        "resolve_agent_intent",
        lambda message: decision,
    )

    response = agent_service.run_agent(
        session,
        "Mark repair the roof as done.",
        confirm=True,
    )

    assert response.intent == AgentIntent.COMPLETE_TASK
    assert response.action_executed is False

    tasks = list_tasks(
        session,
        status=TaskStatus.OPEN,
    )

    assert len(tasks) == 1
    assert tasks[0].title == "Service the generator"

def test_cancel_visitor_requires_confirmation(
    session: Session,
    monkeypatch,
) -> None:
    """Cancelling a visitor should require confirmation."""

    from nexa_api import agent_service

    visitor = create_visitor(
        session,
        VisitorCreate(
            name="Ada Okafor",
            purpose="Electrical repair",
            expected_start=datetime(2030, 1, 1, 10, 0),
            expected_end=datetime(2030, 1, 1, 11, 0),
        ),
    )

    decision = AgentDecision(
        intent=AgentIntent.CANCEL_VISITOR,
        confidence=0.99,
        target_visitor_name="Ada Okafor",
    )

    monkeypatch.setattr(
        agent_service,
        "resolve_agent_intent",
        lambda message: decision,
    )

    response = agent_service.run_agent(
        session,
        "Cancel Ada Okafor's visit.",
    )

    assert response.intent == AgentIntent.CANCEL_VISITOR
    assert response.requires_confirmation is True
    assert response.action_executed is False
    assert response.proposed_action is not None
    assert response.proposed_action["visitor_id"] == visitor.id

    session.refresh(visitor)

    assert visitor.status == VisitorStatus.EXPECTED


def test_confirmed_cancel_visitor_executes(
    session: Session,
    monkeypatch,
) -> None:
    """A confirmed cancellation should update the visitor."""

    from nexa_api import agent_service

    visitor = create_visitor(
        session,
        VisitorCreate(
            name="Ada Okafor",
            purpose="Electrical repair",
            expected_start=datetime(2030, 1, 1, 10, 0),
            expected_end=datetime(2030, 1, 1, 11, 0),
        ),
    )

    decision = AgentDecision(
        intent=AgentIntent.CANCEL_VISITOR,
        confidence=0.99,
        target_visitor_name="Ada Okafor",
    )

    monkeypatch.setattr(
        agent_service,
        "resolve_agent_intent",
        lambda message: decision,
    )

    response = agent_service.run_agent(
        session,
        "Cancel Ada Okafor's visit.",
        confirm=True,
    )

    assert response.intent == AgentIntent.CANCEL_VISITOR
    assert response.requires_confirmation is False
    assert response.action_executed is True
    assert response.data[0]["status"] == "cancelled"

    session.refresh(visitor)

    assert visitor.status == VisitorStatus.CANCELLED


def test_cancel_visitor_missing_name_fails_safely(
    session: Session,
    monkeypatch,
) -> None:
    """Missing visitor name should not mutate anything."""

    from nexa_api import agent_service

    decision = AgentDecision(
        intent=AgentIntent.CANCEL_VISITOR,
        confidence=0.80,
    )

    monkeypatch.setattr(
        agent_service,
        "resolve_agent_intent",
        lambda message: decision,
    )

    response = agent_service.run_agent(
        session,
        "Cancel the visit.",
        confirm=True,
    )

    assert response.intent == AgentIntent.UNKNOWN
    assert response.action_executed is False


def test_cancel_visitor_unknown_name_does_not_execute(
    session: Session,
    monkeypatch,
) -> None:
    """Unknown visitor names should not cancel another visitor."""

    from nexa_api import agent_service

    create_visitor(
        session,
        VisitorCreate(
            name="Ada Okafor",
            purpose="Electrical repair",
            expected_start=datetime(2030, 1, 1, 10, 0),
            expected_end=datetime(2030, 1, 1, 11, 0),
        ),
    )

    decision = AgentDecision(
        intent=AgentIntent.CANCEL_VISITOR,
        confidence=0.95,
        target_visitor_name="John Smith",
    )

    monkeypatch.setattr(
        agent_service,
        "resolve_agent_intent",
        lambda message: decision,
    )

    response = agent_service.run_agent(
        session,
        "Cancel John Smith's visit.",
        confirm=True,
    )

    assert response.intent == AgentIntent.CANCEL_VISITOR
    assert response.action_executed is False

    visitors = list_visitors(
        session,
        status=VisitorStatus.EXPECTED,
    )

    assert len(visitors) == 1
    assert visitors[0].name == "Ada Okafor"

def test_mark_visitor_arrived_requires_confirmation(
    session: Session,
    monkeypatch,
) -> None:
    """Visitor arrival should require confirmation."""

    from nexa_api import agent_service

    visitor = create_visitor(
        session,
        VisitorCreate(
            name="Ada Okafor",
            purpose="Electrical repair",
            expected_start=datetime(2030, 1, 1, 10, 0),
            expected_end=datetime(2030, 1, 1, 11, 0),
        ),
    )

    decision = AgentDecision(
        intent=AgentIntent.MARK_VISITOR_ARRIVED,
        confidence=0.99,
        target_visitor_name="Ada Okafor",
    )

    monkeypatch.setattr(
        agent_service,
        "resolve_agent_intent",
        lambda message: decision,
    )

    response = agent_service.run_agent(
        session,
        "Ada Okafor has arrived.",
    )

    assert response.intent == AgentIntent.MARK_VISITOR_ARRIVED
    assert response.requires_confirmation is True
    assert response.action_executed is False
    assert response.proposed_action is not None
    assert response.proposed_action["visitor_id"] == visitor.id

    session.refresh(visitor)

    assert visitor.status == VisitorStatus.EXPECTED
    assert visitor.arrived_at is None


def test_confirmed_mark_visitor_arrived_executes(
    session: Session,
    monkeypatch,
) -> None:
    """Confirmed visitor arrival should persist."""

    from nexa_api import agent_service

    visitor = create_visitor(
        session,
        VisitorCreate(
            name="Ada Okafor",
            purpose="Electrical repair",
            expected_start=datetime(2030, 1, 1, 10, 0),
            expected_end=datetime(2030, 1, 1, 11, 0),
        ),
    )

    decision = AgentDecision(
        intent=AgentIntent.MARK_VISITOR_ARRIVED,
        confidence=0.99,
        target_visitor_name="Ada Okafor",
    )

    monkeypatch.setattr(
        agent_service,
        "resolve_agent_intent",
        lambda message: decision,
    )

    response = agent_service.run_agent(
        session,
        "Ada Okafor has arrived.",
        confirm=True,
    )

    assert response.intent == AgentIntent.MARK_VISITOR_ARRIVED
    assert response.requires_confirmation is False
    assert response.action_executed is True
    assert response.data[0]["status"] == "arrived"

    session.refresh(visitor)

    assert visitor.status == VisitorStatus.ARRIVED
    assert visitor.arrived_at is not None


def test_mark_visitor_arrived_missing_name_fails_safely(
    session: Session,
    monkeypatch,
) -> None:
    """Missing visitor name should not mutate anything."""

    from nexa_api import agent_service

    decision = AgentDecision(
        intent=AgentIntent.MARK_VISITOR_ARRIVED,
        confidence=0.80,
    )

    monkeypatch.setattr(
        agent_service,
        "resolve_agent_intent",
        lambda message: decision,
    )

    response = agent_service.run_agent(
        session,
        "The visitor has arrived.",
        confirm=True,
    )

    assert response.intent == AgentIntent.UNKNOWN
    assert response.action_executed is False


def test_mark_visitor_arrived_unknown_name_does_not_execute(
    session: Session,
    monkeypatch,
) -> None:
    """Unknown visitor names should not modify another visitor."""

    from nexa_api import agent_service

    create_visitor(
        session,
        VisitorCreate(
            name="Ada Okafor",
            purpose="Electrical repair",
            expected_start=datetime(2030, 1, 1, 10, 0),
            expected_end=datetime(2030, 1, 1, 11, 0),
        ),
    )

    decision = AgentDecision(
        intent=AgentIntent.MARK_VISITOR_ARRIVED,
        confidence=0.95,
        target_visitor_name="John Smith",
    )

    monkeypatch.setattr(
        agent_service,
        "resolve_agent_intent",
        lambda message: decision,
    )

    response = agent_service.run_agent(
        session,
        "John Smith has arrived.",
        confirm=True,
    )

    assert response.intent == AgentIntent.MARK_VISITOR_ARRIVED
    assert response.action_executed is False

    visitors = list_visitors(
        session,
        status=VisitorStatus.EXPECTED,
    )

    assert len(visitors) == 1
    assert visitors[0].name == "Ada Okafor"

def test_mark_visitor_departed_requires_confirmation(
    session: Session,
    monkeypatch,
) -> None:
    """Visitor departure should require confirmation."""

    from nexa_api import agent_service

    visitor = create_visitor(
        session,
        VisitorCreate(
            name="Chinedu Okafor",
            purpose="Generator inspection",
            expected_start=datetime(2030, 1, 2, 10, 0),
            expected_end=datetime(2030, 1, 2, 11, 0),
        ),
    )

    visitor = mark_visitor_arrived(
        session,
        visitor,
    )

    decision = AgentDecision(
        intent=AgentIntent.MARK_VISITOR_DEPARTED,
        confidence=0.99,
        target_visitor_name="Chinedu Okafor",
    )

    monkeypatch.setattr(
        agent_service,
        "resolve_agent_intent",
        lambda message: decision,
    )

    response = agent_service.run_agent(
        session,
        "Chinedu Okafor has left.",
    )

    assert response.intent == AgentIntent.MARK_VISITOR_DEPARTED
    assert response.requires_confirmation is True
    assert response.action_executed is False
    assert response.proposed_action is not None
    assert response.proposed_action["visitor_id"] == visitor.id

    session.refresh(visitor)

    assert visitor.status == VisitorStatus.ARRIVED
    assert visitor.departed_at is None


def test_confirmed_mark_visitor_departed_executes(
    session: Session,
    monkeypatch,
) -> None:
    """Confirmed departure should persist."""

    from nexa_api import agent_service

    visitor = create_visitor(
        session,
        VisitorCreate(
            name="Chinedu Okafor",
            purpose="Generator inspection",
            expected_start=datetime(2030, 1, 2, 10, 0),
            expected_end=datetime(2030, 1, 2, 11, 0),
        ),
    )

    visitor = mark_visitor_arrived(
        session,
        visitor,
    )

    decision = AgentDecision(
        intent=AgentIntent.MARK_VISITOR_DEPARTED,
        confidence=0.99,
        target_visitor_name="Chinedu Okafor",
    )

    monkeypatch.setattr(
        agent_service,
        "resolve_agent_intent",
        lambda message: decision,
    )

    response = agent_service.run_agent(
        session,
        "Chinedu Okafor has left.",
        confirm=True,
    )

    assert response.intent == AgentIntent.MARK_VISITOR_DEPARTED
    assert response.requires_confirmation is False
    assert response.action_executed is True
    assert response.data[0]["status"] == "departed"
    assert response.data[0]["departed_at"] is not None

    session.refresh(visitor)

    assert visitor.status == VisitorStatus.DEPARTED
    assert visitor.departed_at is not None


def test_mark_visitor_departed_missing_name_fails_safely(
    session: Session,
    monkeypatch,
) -> None:
    """Missing visitor name should not mutate anything."""

    from nexa_api import agent_service

    decision = AgentDecision(
        intent=AgentIntent.MARK_VISITOR_DEPARTED,
        confidence=0.80,
    )

    monkeypatch.setattr(
        agent_service,
        "resolve_agent_intent",
        lambda message: decision,
    )

    response = agent_service.run_agent(
        session,
        "The visitor has left.",
        confirm=True,
    )

    assert response.intent == AgentIntent.UNKNOWN
    assert response.action_executed is False


def test_mark_visitor_departed_unknown_name_does_not_execute(
    session: Session,
    monkeypatch,
) -> None:
    """Unknown visitor names should not modify another visitor."""

    from nexa_api import agent_service

    visitor = create_visitor(
        session,
        VisitorCreate(
            name="Chinedu Okafor",
            purpose="Generator inspection",
            expected_start=datetime(2030, 1, 2, 10, 0),
            expected_end=datetime(2030, 1, 2, 11, 0),
        ),
    )

    mark_visitor_arrived(
        session,
        visitor,
    )

    decision = AgentDecision(
        intent=AgentIntent.MARK_VISITOR_DEPARTED,
        confidence=0.95,
        target_visitor_name="John Smith",
    )

    monkeypatch.setattr(
        agent_service,
        "resolve_agent_intent",
        lambda message: decision,
    )

    response = agent_service.run_agent(
        session,
        "John Smith has left.",
        confirm=True,
    )

    assert response.intent == AgentIntent.MARK_VISITOR_DEPARTED
    assert response.action_executed is False

    visitors = list_visitors(
        session,
        status=VisitorStatus.ARRIVED,
    )

    assert len(visitors) == 1
    assert visitors[0].name == "Chinedu Okafor"

def test_mark_delivery_collected_requires_confirmation(
    session: Session,
    monkeypatch,
) -> None:
    """Collecting a delivery should require confirmation."""

    from nexa_api import agent_service

    delivery = create_delivery(
        session,
        DeliveryCreate(
            description="MacBook Pro package",
            carrier="DHL",
            tracking_reference="NEXA-DHL-2030-001",
        ),
    )

    delivery = mark_delivery_delivered(
        session,
        delivery,
    )

    decision = AgentDecision(
        intent=AgentIntent.MARK_DELIVERY_COLLECTED,
        confidence=0.99,
        target_delivery_description="MacBook Pro package",
    )

    monkeypatch.setattr(
        agent_service,
        "resolve_agent_intent",
        lambda message: decision,
    )

    response = agent_service.run_agent(
        session,
        "Mark the MacBook Pro package as collected.",
    )

    assert response.intent == AgentIntent.MARK_DELIVERY_COLLECTED
    assert response.requires_confirmation is True
    assert response.action_executed is False
    assert response.proposed_action is not None
    assert response.proposed_action["delivery_id"] == delivery.id

    session.refresh(delivery)

    assert delivery.status == DeliveryStatus.DELIVERED
    assert delivery.collected_at is None


def test_confirmed_mark_delivery_collected_executes(
    session: Session,
    monkeypatch,
) -> None:
    """Confirmed delivery collection should persist."""

    from nexa_api import agent_service

    delivery = create_delivery(
        session,
        DeliveryCreate(
            description="MacBook Pro package",
            carrier="DHL",
            tracking_reference="NEXA-DHL-2030-001",
        ),
    )

    delivery = mark_delivery_delivered(
        session,
        delivery,
    )

    decision = AgentDecision(
        intent=AgentIntent.MARK_DELIVERY_COLLECTED,
        confidence=0.99,
        target_delivery_description="MacBook Pro package",
    )

    monkeypatch.setattr(
        agent_service,
        "resolve_agent_intent",
        lambda message: decision,
    )

    response = agent_service.run_agent(
        session,
        "Mark the MacBook Pro package as collected.",
        confirm=True,
    )

    assert response.intent == AgentIntent.MARK_DELIVERY_COLLECTED
    assert response.requires_confirmation is False
    assert response.action_executed is True
    assert response.data[0]["status"] == "collected"
    assert response.data[0]["collected_at"] is not None

    session.refresh(delivery)

    assert delivery.status == DeliveryStatus.COLLECTED
    assert delivery.collected_at is not None


def test_mark_delivery_collected_missing_description_fails_safely(
    session: Session,
    monkeypatch,
) -> None:
    """Missing delivery target should not mutate anything."""

    from nexa_api import agent_service

    decision = AgentDecision(
        intent=AgentIntent.MARK_DELIVERY_COLLECTED,
        confidence=0.80,
    )

    monkeypatch.setattr(
        agent_service,
        "resolve_agent_intent",
        lambda message: decision,
    )

    response = agent_service.run_agent(
        session,
        "Mark the package as collected.",
        confirm=True,
    )

    assert response.intent == AgentIntent.UNKNOWN
    assert response.action_executed is False


def test_mark_delivery_collected_unknown_description_does_not_execute(
    session: Session,
    monkeypatch,
) -> None:
    """Unknown delivery targets should not modify another delivery."""

    from nexa_api import agent_service

    delivery = create_delivery(
        session,
        DeliveryCreate(
            description="MacBook Pro package",
            carrier="DHL",
            tracking_reference="NEXA-DHL-2030-001",
        ),
    )

    mark_delivery_delivered(
        session,
        delivery,
    )

    decision = AgentDecision(
        intent=AgentIntent.MARK_DELIVERY_COLLECTED,
        confidence=0.95,
        target_delivery_description="iPhone package",
    )

    monkeypatch.setattr(
        agent_service,
        "resolve_agent_intent",
        lambda message: decision,
    )

    response = agent_service.run_agent(
        session,
        "Mark the iPhone package as collected.",
        confirm=True,
    )

    assert response.intent == AgentIntent.MARK_DELIVERY_COLLECTED
    assert response.action_executed is False

    deliveries = list_deliveries(
        session,
        status=DeliveryStatus.DELIVERED,
    )

    assert len(deliveries) == 1
    assert deliveries[0].description == "MacBook Pro package"


def test_mark_delivery_delivered_requires_confirmation(
    session: Session,
    monkeypatch,
) -> None:
    """Marking a delivery delivered should require confirmation."""

    from nexa_api import agent_service

    delivery = create_delivery(
        session,
        DeliveryCreate(
            description="Laptop automation package",
            carrier="DHL",
            tracking_reference="NEXA-MANUAL-003",
        ),
    )

    decision = AgentDecision(
        intent=AgentIntent.MARK_DELIVERY_DELIVERED,
        confidence=0.99,
        target_delivery_description="Laptop automation package",
    )

    monkeypatch.setattr(
        agent_service,
        "resolve_agent_intent",
        lambda message: decision,
    )

    response = agent_service.run_agent(
        session,
        "The Laptop automation package has arrived.",
    )

    assert response.intent == AgentIntent.MARK_DELIVERY_DELIVERED
    assert response.requires_confirmation is True
    assert response.action_executed is False
    assert response.proposed_action is not None
    assert response.proposed_action["delivery_id"] == delivery.id

    session.refresh(delivery)

    assert delivery.status == DeliveryStatus.EXPECTED
    assert delivery.delivered_at is None


def test_confirmed_mark_delivery_delivered_executes(
    session: Session,
    monkeypatch,
) -> None:
    """Confirmed delivery arrival should persist."""

    from nexa_api import agent_service

    delivery = create_delivery(
        session,
        DeliveryCreate(
            description="Laptop automation package",
            carrier="DHL",
            tracking_reference="NEXA-MANUAL-003",
        ),
    )

    decision = AgentDecision(
        intent=AgentIntent.MARK_DELIVERY_DELIVERED,
        confidence=0.99,
        target_delivery_description="Laptop automation package",
    )

    monkeypatch.setattr(
        agent_service,
        "resolve_agent_intent",
        lambda message: decision,
    )

    response = agent_service.run_agent(
        session,
        "The Laptop automation package has arrived.",
        confirm=True,
    )

    assert response.intent == AgentIntent.MARK_DELIVERY_DELIVERED
    assert response.requires_confirmation is False
    assert response.action_executed is True
    assert response.data[0]["status"] == "delivered"
    assert response.data[0]["delivered_at"] is not None

    session.refresh(delivery)

    assert delivery.status == DeliveryStatus.DELIVERED
    assert delivery.delivered_at is not None


def test_mark_delivery_delivered_missing_description_fails_safely(
    session: Session,
    monkeypatch,
) -> None:
    """Missing delivery target should not mutate anything."""

    from nexa_api import agent_service

    decision = AgentDecision(
        intent=AgentIntent.MARK_DELIVERY_DELIVERED,
        confidence=0.80,
    )

    monkeypatch.setattr(
        agent_service,
        "resolve_agent_intent",
        lambda message: decision,
    )

    response = agent_service.run_agent(
        session,
        "The package has arrived.",
        confirm=True,
    )

    assert response.intent == AgentIntent.UNKNOWN
    assert response.action_executed is False


def test_mark_delivery_delivered_unknown_description_does_not_execute(
    session: Session,
    monkeypatch,
) -> None:
    """Unknown delivery targets should not modify another delivery."""

    from nexa_api import agent_service

    create_delivery(
        session,
        DeliveryCreate(
            description="Laptop automation package",
            carrier="DHL",
            tracking_reference="NEXA-MANUAL-003",
        ),
    )

    decision = AgentDecision(
        intent=AgentIntent.MARK_DELIVERY_DELIVERED,
        confidence=0.95,
        target_delivery_description="Phone package",
    )

    monkeypatch.setattr(
        agent_service,
        "resolve_agent_intent",
        lambda message: decision,
    )

    response = agent_service.run_agent(
        session,
        "The Phone package has arrived.",
        confirm=True,
    )

    assert response.intent == AgentIntent.MARK_DELIVERY_DELIVERED
    assert response.action_executed is False

    deliveries = list_deliveries(
        session,
        status=DeliveryStatus.EXPECTED,
    )

    assert len(deliveries) == 1
    assert deliveries[0].description == "Laptop automation package"

def test_update_presence_requires_confirmation(
    session: Session,
    monkeypatch,
) -> None:
    """Presence updates should require confirmation."""

    from nexa_api import agent_service

    presence = create_presence(
        session,
        PresenceCreate(
            occupant_name="Obumneme",
            status=PresenceStatus.HOME,
            note="At home",
        ),
    )

    decision = AgentDecision(
        intent=AgentIntent.UPDATE_PRESENCE,
        confidence=0.99,
        target_occupant_name="Obumneme",
        target_presence_status="away",
    )

    monkeypatch.setattr(
        agent_service,
        "resolve_agent_intent",
        lambda message: decision,
    )

    response = agent_service.run_agent(
        session,
        "Obumneme is leaving.",
    )

    assert response.intent == AgentIntent.UPDATE_PRESENCE
    assert response.requires_confirmation is True
    assert response.action_executed is False
    assert response.proposed_action is not None
    assert response.proposed_action["presence_id"] == presence.id
    assert response.proposed_action["new_status"] == PresenceStatus.AWAY

    session.refresh(presence)

    assert presence.status == PresenceStatus.HOME


def test_confirmed_update_presence_executes(
    session: Session,
    monkeypatch,
) -> None:
    """Confirmed presence updates should persist."""

    from nexa_api import agent_service

    presence = create_presence(
        session,
        PresenceCreate(
            occupant_name="Obumneme",
            status=PresenceStatus.HOME,
            note="At home",
        ),
    )

    decision = AgentDecision(
        intent=AgentIntent.UPDATE_PRESENCE,
        confidence=0.99,
        target_occupant_name="Obumneme",
        target_presence_status="away",
    )

    monkeypatch.setattr(
        agent_service,
        "resolve_agent_intent",
        lambda message: decision,
    )

    response = agent_service.run_agent(
        session,
        "Obumneme is leaving.",
        confirm=True,
    )

    assert response.intent == AgentIntent.UPDATE_PRESENCE
    assert response.requires_confirmation is False
    assert response.action_executed is True
    assert response.data[0]["status"] == "away"

    session.refresh(presence)

    assert presence.status == PresenceStatus.AWAY


def test_update_presence_missing_occupant_fails_safely(
    session: Session,
    monkeypatch,
) -> None:
    """Missing occupant name should not mutate anything."""

    from nexa_api import agent_service

    decision = AgentDecision(
        intent=AgentIntent.UPDATE_PRESENCE,
        confidence=0.80,
        target_presence_status="away",
    )

    monkeypatch.setattr(
        agent_service,
        "resolve_agent_intent",
        lambda message: decision,
    )

    response = agent_service.run_agent(
        session,
        "I'm leaving.",
        confirm=True,
    )

    assert response.intent == AgentIntent.UNKNOWN
    assert response.action_executed is False


def test_update_presence_invalid_status_fails_safely(
    session: Session,
    monkeypatch,
) -> None:
    """Invalid presence status should not mutate anything."""

    from nexa_api import agent_service

    presence = create_presence(
        session,
        PresenceCreate(
            occupant_name="Obumneme",
            status=PresenceStatus.HOME,
            note="At home",
        ),
    )

    decision = AgentDecision(
        intent=AgentIntent.UPDATE_PRESENCE,
        confidence=0.95,
        target_occupant_name="Obumneme",
        target_presence_status="working",
    )

    monkeypatch.setattr(
        agent_service,
        "resolve_agent_intent",
        lambda message: decision,
    )

    response = agent_service.run_agent(
        session,
        "Obumneme is working.",
        confirm=True,
    )

    assert response.intent == AgentIntent.UNKNOWN
    assert response.action_executed is False

    session.refresh(presence)

    assert presence.status == PresenceStatus.HOME

def test_resolve_agent_intent_passes_history_to_llm(
    monkeypatch,
) -> None:
    """Conversation history should be forwarded to the LLM resolver."""

    from nexa_api import agent_service

    expected = AgentDecision(
        intent=AgentIntent.UNKNOWN,
        confidence=0.5,
    )

    history = [
        {
            "role": "user",
            "content": "Who is coming today?",
        },
        {
            "role": "assistant",
            "content": "Ada Okafor is expected.",
        },
    ]

    captured: dict[str, object] = {}

    def fake_llm_resolver(
        message: str,
        history: list[dict[str, str]] | None = None,
    ) -> AgentDecision:
        captured["message"] = message
        captured["history"] = history
        return expected

    monkeypatch.setattr(
        agent_service,
        "resolve_intent_with_llm",
        fake_llm_resolver,
    )

    decision = agent_service.resolve_agent_intent(
        "Has she arrived?",
        history=history,
    )

    assert decision == expected
    assert captured["message"] == "Has she arrived?"
    assert captured["history"] == history


def test_run_agent_passes_history_to_resolver(
    session: Session,
    monkeypatch,
) -> None:
    """run_agent should forward conversation history to intent resolution."""

    from nexa_api import agent_service

    history = [
        {
            "role": "user",
            "content": "Who is coming today?",
        },
        {
            "role": "assistant",
            "content": "Ada Okafor is expected.",
        },
    ]

    captured: dict[str, object] = {}

    def fake_resolver(
        message: str,
        history: list[dict[str, str]] | None = None,
    ) -> AgentDecision:
        captured["message"] = message
        captured["history"] = history

        return AgentDecision(
            intent=AgentIntent.UNKNOWN,
            confidence=0.0,
        )

    monkeypatch.setattr(
        agent_service,
        "resolve_agent_intent",
        fake_resolver,
    )

    agent_service.run_agent(
        session,
        "Has she arrived?",
        history=history,
    )

    assert captured["message"] == "Has she arrived?"
    assert captured["history"] == history

def test_first_person_presence_update_requires_confirmation(
    session: Session,
    monkeypatch,
) -> None:
    """First-person presence updates should require confirmation."""

    from nexa_api import agent_service

    presence = HouseholdPresence(
        occupant_name="Obumneme",
        status=PresenceStatus.AWAY,
    )

    session.add(presence)
    session.commit()
    session.refresh(presence)

    decision = AgentDecision(
        intent=AgentIntent.UPDATE_PRESENCE,
        confidence=0.99,
        target_occupant_name="Obumneme",
        target_presence_status="home",
    )

    def fake_resolver(
        message: str,
        history: list[dict[str, str]] | None = None,
        speaker_name: str | None = None,
    ) -> AgentDecision:
        assert message == "I'm home."
        assert speaker_name == "Obumneme"
        return decision

    monkeypatch.setattr(
        agent_service,
        "resolve_agent_intent",
        fake_resolver,
    )

    response = agent_service.run_agent(
        session,
        "I'm home.",
        speaker_name="Obumneme",
    )

    assert response.intent == AgentIntent.UPDATE_PRESENCE
    assert response.requires_confirmation is True
    assert response.action_executed is False

    session.refresh(presence)

    assert presence.status == PresenceStatus.AWAY


def test_confirmed_first_person_presence_update_executes(
    session: Session,
    monkeypatch,
) -> None:
    """Confirmed first-person presence updates should execute."""

    from nexa_api import agent_service

    presence = HouseholdPresence(
        occupant_name="Obumneme",
        status=PresenceStatus.AWAY,
    )

    session.add(presence)
    session.commit()
    session.refresh(presence)

    decision = AgentDecision(
        intent=AgentIntent.UPDATE_PRESENCE,
        confidence=0.99,
        target_occupant_name="Obumneme",
        target_presence_status="home",
    )

    def fake_resolver(
        message: str,
        history: list[dict[str, str]] | None = None,
        speaker_name: str | None = None,
    ) -> AgentDecision:
        assert message == "I'm home."
        assert speaker_name == "Obumneme"
        return decision

    monkeypatch.setattr(
        agent_service,
        "resolve_agent_intent",
        fake_resolver,
    )

    response = agent_service.run_agent(
        session,
        "I'm home.",
        confirm=True,
        speaker_name="Obumneme",
    )

    assert response.intent == AgentIntent.UPDATE_PRESENCE
    assert response.requires_confirmation is False
    assert response.action_executed is True

    session.refresh(presence)

    assert presence.status == PresenceStatus.HOME

def test_find_expected_delivery_fuzzy_matches_partial_description(
    session: Session,
) -> None:
    """A clear partial delivery description should match safely."""

    delivery = Delivery(
        description="Dell Laptop package",
        status=DeliveryStatus.EXPECTED,
    )

    session.add(delivery)
    session.commit()
    session.refresh(delivery)

    result = find_expected_delivery_fuzzy(
        session,
        "laptop package",
    )

    assert result is not None
    assert result.id == delivery.id


def test_find_expected_delivery_fuzzy_matches_short_unique_description(
    session: Session,
) -> None:
    """A short but unique delivery description should match."""

    delivery = Delivery(
        description="Office Monitor package",
        status=DeliveryStatus.EXPECTED,
    )

    session.add(delivery)
    session.commit()
    session.refresh(delivery)

    result = find_expected_delivery_fuzzy(
        session,
        "monitor",
    )

    assert result is not None
    assert result.id == delivery.id


def test_find_expected_delivery_fuzzy_rejects_ambiguous_match(
    session: Session,
) -> None:
    """Equally good fuzzy matches should not be guessed."""

    first_delivery = Delivery(
        description="Dell Laptop package",
        status=DeliveryStatus.EXPECTED,
    )

    second_delivery = Delivery(
        description="HP Laptop package",
        status=DeliveryStatus.EXPECTED,
    )

    session.add_all(
        [
            first_delivery,
            second_delivery,
        ]
    )
    session.commit()

    result = find_expected_delivery_fuzzy(
        session,
        "Laptop package",
    )

    assert result is None


def test_find_expected_delivery_fuzzy_returns_none_for_unrelated_description(
    session: Session,
) -> None:
    """An unrelated description should not produce a match."""

    delivery = Delivery(
        description="Dell Laptop package",
        status=DeliveryStatus.EXPECTED,
    )

    session.add(delivery)
    session.commit()

    result = find_expected_delivery_fuzzy(
        session,
        "groceries",
    )

    assert result is None


def test_mark_delivery_delivered_accepts_unique_fuzzy_match(
    session: Session,
    monkeypatch,
) -> None:
    """A unique fuzzy delivery match should produce a safe proposal."""

    from nexa_api import agent_service

    delivery = Delivery(
        description="Dell Laptop package",
        status=DeliveryStatus.EXPECTED,
    )

    session.add(delivery)
    session.commit()
    session.refresh(delivery)

    decision = AgentDecision(
        intent=AgentIntent.MARK_DELIVERY_DELIVERED,
        confidence=0.99,
        target_delivery_description="laptop package",
    )

    monkeypatch.setattr(
        agent_service,
        "resolve_agent_intent",
        lambda message: decision,
    )

    response = agent_service.run_agent(
        session,
        "The laptop package has arrived.",
    )

    assert response.intent == AgentIntent.MARK_DELIVERY_DELIVERED
    assert response.requires_confirmation is True
    assert response.action_executed is False

    session.refresh(delivery)

    assert delivery.status == DeliveryStatus.EXPECTED


def test_mark_delivery_delivered_rejects_ambiguous_fuzzy_match(
    session: Session,
    monkeypatch,
) -> None:
    """Nexa should refuse to guess between similar deliveries."""

    from nexa_api import agent_service

    first_delivery = Delivery(
        description="Dell Laptop package",
        status=DeliveryStatus.EXPECTED,
    )

    second_delivery = Delivery(
        description="HP Laptop package",
        status=DeliveryStatus.EXPECTED,
    )

    session.add_all(
        [
            first_delivery,
            second_delivery,
        ]
    )
    session.commit()

    decision = AgentDecision(
        intent=AgentIntent.MARK_DELIVERY_DELIVERED,
        confidence=0.99,
        target_delivery_description="Laptop package",
    )

    monkeypatch.setattr(
        agent_service,
        "resolve_agent_intent",
        lambda message: decision,
    )

    response = agent_service.run_agent(
        session,
        "The laptop package has arrived.",
    )

    assert response.intent == AgentIntent.MARK_DELIVERY_DELIVERED
    assert response.requires_confirmation is False
    assert response.action_executed is False

    session.refresh(first_delivery)
    session.refresh(second_delivery)

    assert first_delivery.status == DeliveryStatus.EXPECTED
    assert second_delivery.status == DeliveryStatus.EXPECTED

def test_find_delivered_delivery_fuzzy_matches_partial_description(
    session: Session,
) -> None:
    """A clear partial description should match a delivered package."""

    delivery = Delivery(
        description="Dell Laptop package",
        status=DeliveryStatus.DELIVERED,
    )

    session.add(delivery)
    session.commit()
    session.refresh(delivery)

    result = find_delivered_delivery_fuzzy(
        session,
        "laptop package",
    )

    assert result is not None
    assert result.id == delivery.id


def test_find_delivered_delivery_fuzzy_rejects_ambiguous_match(
    session: Session,
) -> None:
    """Ambiguous delivered-package matches should be rejected."""

    first_delivery = Delivery(
        description="Dell Laptop package",
        status=DeliveryStatus.DELIVERED,
    )

    second_delivery = Delivery(
        description="HP Laptop package",
        status=DeliveryStatus.DELIVERED,
    )

    session.add_all(
        [
            first_delivery,
            second_delivery,
        ]
    )
    session.commit()

    result = find_delivered_delivery_fuzzy(
        session,
        "Laptop package",
    )

    assert result is None


def test_mark_delivery_collected_accepts_unique_fuzzy_match(
    session: Session,
    monkeypatch,
) -> None:
    """A unique fuzzy delivered-package match should produce a proposal."""

    from nexa_api import agent_service

    delivery = Delivery(
        description="Dell Laptop package",
        status=DeliveryStatus.DELIVERED,
    )

    session.add(delivery)
    session.commit()
    session.refresh(delivery)

    decision = AgentDecision(
        intent=AgentIntent.MARK_DELIVERY_COLLECTED,
        confidence=0.99,
        target_delivery_description="laptop package",
    )

    monkeypatch.setattr(
        agent_service,
        "resolve_agent_intent",
        lambda message: decision,
    )

    response = agent_service.run_agent(
        session,
        "Mark the laptop package as collected.",
    )

    assert response.intent == AgentIntent.MARK_DELIVERY_COLLECTED
    assert response.requires_confirmation is True
    assert response.action_executed is False

    session.refresh(delivery)

    assert delivery.status == DeliveryStatus.DELIVERED


def test_mark_delivery_collected_rejects_ambiguous_fuzzy_match(
    session: Session,
    monkeypatch,
) -> None:
    """Nexa should refuse ambiguous delivered-package matches."""

    from nexa_api import agent_service

    first_delivery = Delivery(
        description="Dell Laptop package",
        status=DeliveryStatus.DELIVERED,
    )

    second_delivery = Delivery(
        description="HP Laptop package",
        status=DeliveryStatus.DELIVERED,
    )

    session.add_all(
        [
            first_delivery,
            second_delivery,
        ]
    )
    session.commit()

    decision = AgentDecision(
        intent=AgentIntent.MARK_DELIVERY_COLLECTED,
        confidence=0.99,
        target_delivery_description="Laptop package",
    )

    monkeypatch.setattr(
        agent_service,
        "resolve_agent_intent",
        lambda message: decision,
    )

    response = agent_service.run_agent(
        session,
        "Mark the laptop package as collected.",
    )

    assert response.intent == AgentIntent.MARK_DELIVERY_COLLECTED
    assert response.requires_confirmation is False
    assert response.action_executed is False

    session.refresh(first_delivery)
    session.refresh(second_delivery)

    assert first_delivery.status == DeliveryStatus.DELIVERED
    assert second_delivery.status == DeliveryStatus.DELIVERED

def test_find_open_task_fuzzy_matches_partial_title(
    session: Session,
) -> None:
    task = HouseholdTask(
        title="Service the generator",
        status=TaskStatus.OPEN,
    )

    session.add(task)
    session.commit()
    session.refresh(task)

    result = find_open_task_fuzzy(
        session,
        "generator",
    )

    assert result is not None
    assert result.id == task.id


def test_find_open_task_fuzzy_rejects_ambiguous_match(
    session: Session,
) -> None:
    first_task = HouseholdTask(
        title="Service generator one",
        status=TaskStatus.OPEN,
    )

    second_task = HouseholdTask(
        title="Service generator two",
        status=TaskStatus.OPEN,
    )

    session.add_all(
        [
            first_task,
            second_task,
        ]
    )
    session.commit()

    result = find_open_task_fuzzy(
        session,
        "Service generator",
    )

    assert result is None


def test_complete_task_accepts_unique_fuzzy_match(
    session: Session,
    monkeypatch,
) -> None:
    from nexa_api import agent_service

    task = HouseholdTask(
        title="Service the generator",
        status=TaskStatus.OPEN,
    )

    session.add(task)
    session.commit()
    session.refresh(task)

    decision = AgentDecision(
        intent=AgentIntent.COMPLETE_TASK,
        confidence=0.99,
        target_task_title="generator",
    )

    monkeypatch.setattr(
        agent_service,
        "resolve_agent_intent",
        lambda message: decision,
    )

    response = agent_service.run_agent(
        session,
        "Mark the generator task as done.",
    )

    assert response.intent == AgentIntent.COMPLETE_TASK
    assert response.requires_confirmation is True
    assert response.action_executed is False

    session.refresh(task)

    assert task.status == TaskStatus.OPEN


def test_complete_task_rejects_ambiguous_fuzzy_match(
    session: Session,
    monkeypatch,
) -> None:
    from nexa_api import agent_service

    first_task = HouseholdTask(
        title="Service generator one",
        status=TaskStatus.OPEN,
    )

    second_task = HouseholdTask(
        title="Service generator two",
        status=TaskStatus.OPEN,
    )

    session.add_all(
        [
            first_task,
            second_task,
        ]
    )
    session.commit()

    decision = AgentDecision(
        intent=AgentIntent.COMPLETE_TASK,
        confidence=0.99,
        target_task_title="Service generator",
    )

    monkeypatch.setattr(
        agent_service,
        "resolve_agent_intent",
        lambda message: decision,
    )

    response = agent_service.run_agent(
        session,
        "Complete the generator task.",
    )

    assert response.intent == AgentIntent.COMPLETE_TASK
    assert response.requires_confirmation is False
    assert response.action_executed is False

def test_find_expected_visitor_fuzzy_matches_partial_name(
    session: Session,
) -> None:
    visitor = ExpectedVisitor(
        name="Chinedu Okafor",
        purpose="Maintenance",
        expected_start=datetime(2030, 1, 1, 10, 0),
        expected_end=datetime(2030, 1, 1, 11, 0),
        status=VisitorStatus.EXPECTED,
    )

    session.add(visitor)
    session.commit()
    session.refresh(visitor)

    result = find_expected_visitor_fuzzy(
        session,
        "Chinedu",
    )

    assert result is not None
    assert result.id == visitor.id


def test_find_expected_visitor_fuzzy_rejects_ambiguous_match(
    session: Session,
) -> None:
    first_visitor = ExpectedVisitor(
        name="Chinedu Okafor",
        purpose="Maintenance",
        expected_start=datetime(2030, 1, 1, 10, 0),
        expected_end=datetime(2030, 1, 1, 11, 0),
        status=VisitorStatus.EXPECTED,
    )

    second_visitor = ExpectedVisitor(
        name="Chinedu Obi",
        purpose="Inspection",
        expected_start=datetime(2030, 1, 1, 12, 0),
        expected_end=datetime(2030, 1, 1, 13, 0),
        status=VisitorStatus.EXPECTED,
    )

    session.add_all(
        [
            first_visitor,
            second_visitor,
        ]
    )
    session.commit()

    result = find_expected_visitor_fuzzy(
        session,
        "Chinedu",
    )

    assert result is None


def test_mark_visitor_arrived_accepts_unique_fuzzy_match(
    session: Session,
    monkeypatch,
) -> None:
    from nexa_api import agent_service

    visitor = ExpectedVisitor(
        name="Chinedu Okafor",
        purpose="Maintenance",
        expected_start=datetime(2030, 1, 1, 10, 0),
        expected_end=datetime(2030, 1, 1, 11, 0),
        status=VisitorStatus.EXPECTED,
    )

    session.add(visitor)
    session.commit()
    session.refresh(visitor)

    decision = AgentDecision(
        intent=AgentIntent.MARK_VISITOR_ARRIVED,
        confidence=0.99,
        target_visitor_name="Chinedu",
    )

    monkeypatch.setattr(
        agent_service,
        "resolve_agent_intent",
        lambda message: decision,
    )

    response = agent_service.run_agent(
        session,
        "Chinedu has arrived.",
    )

    assert response.intent == AgentIntent.MARK_VISITOR_ARRIVED
    assert response.requires_confirmation is True
    assert response.action_executed is False

    session.refresh(visitor)

    assert visitor.status == VisitorStatus.EXPECTED


def test_mark_visitor_arrived_rejects_ambiguous_fuzzy_match(
    session: Session,
    monkeypatch,
) -> None:
    from nexa_api import agent_service

    first_visitor = ExpectedVisitor(
        name="Chinedu Okafor",
        purpose="Maintenance",
        expected_start=datetime(2030, 1, 1, 10, 0),
        expected_end=datetime(2030, 1, 1, 11, 0),
        status=VisitorStatus.EXPECTED,
    )

    second_visitor = ExpectedVisitor(
        name="Chinedu Obi",
        purpose="Inspection",
        expected_start=datetime(2030, 1, 1, 12, 0),
        expected_end=datetime(2030, 1, 1, 13, 0),
        status=VisitorStatus.EXPECTED,
    )

    session.add_all(
        [
            first_visitor,
            second_visitor,
        ]
    )
    session.commit()

    decision = AgentDecision(
        intent=AgentIntent.MARK_VISITOR_ARRIVED,
        confidence=0.99,
        target_visitor_name="Chinedu",
    )

    monkeypatch.setattr(
        agent_service,
        "resolve_agent_intent",
        lambda message: decision,
    )

    response = agent_service.run_agent(
        session,
        "Chinedu has arrived.",
    )

    assert response.intent == AgentIntent.MARK_VISITOR_ARRIVED
    assert response.requires_confirmation is False
    assert response.action_executed is False

def test_mark_visitor_departed_accepts_unique_fuzzy_match(
    session: Session,
    monkeypatch,
) -> None:
    """A unique fuzzy arrived-visitor match should produce a proposal."""

    from nexa_api import agent_service

    visitor = ExpectedVisitor(
        name="Chinedu Okafor",
        purpose="Maintenance",
        expected_start=datetime(2030, 1, 1, 10, 0),
        expected_end=datetime(2030, 1, 1, 11, 0),
        status=VisitorStatus.ARRIVED,
    )

    session.add(visitor)
    session.commit()
    session.refresh(visitor)

    decision = AgentDecision(
        intent=AgentIntent.MARK_VISITOR_DEPARTED,
        confidence=0.99,
        target_visitor_name="Chinedu",
    )

    monkeypatch.setattr(
        agent_service,
        "resolve_agent_intent",
        lambda message: decision,
    )

    response = agent_service.run_agent(
        session,
        "Chinedu has left.",
    )

    assert response.intent == AgentIntent.MARK_VISITOR_DEPARTED
    assert response.requires_confirmation is True
    assert response.action_executed is False

    session.refresh(visitor)

    assert visitor.status == VisitorStatus.ARRIVED

def test_mark_visitor_departed_rejects_ambiguous_fuzzy_match(
    session: Session,
    monkeypatch,
) -> None:
    """Nexa should refuse ambiguous arrived-visitor matches."""

    from nexa_api import agent_service

    first_visitor = ExpectedVisitor(
        name="Chinedu Okafor",
        purpose="Maintenance",
        expected_start=datetime(2030, 1, 1, 10, 0),
        expected_end=datetime(2030, 1, 1, 11, 0),
        status=VisitorStatus.ARRIVED,
    )

    second_visitor = ExpectedVisitor(
        name="Chinedu Obi",
        purpose="Inspection",
        expected_start=datetime(2030, 1, 1, 12, 0),
        expected_end=datetime(2030, 1, 1, 13, 0),
        status=VisitorStatus.ARRIVED,
    )

    session.add_all(
        [
            first_visitor,
            second_visitor,
        ]
    )
    session.commit()

    decision = AgentDecision(
        intent=AgentIntent.MARK_VISITOR_DEPARTED,
        confidence=0.99,
        target_visitor_name="Chinedu",
    )

    monkeypatch.setattr(
        agent_service,
        "resolve_agent_intent",
        lambda message: decision,
    )

    response = agent_service.run_agent(
        session,
        "Chinedu has left.",
    )

    assert response.intent == AgentIntent.MARK_VISITOR_DEPARTED
    assert response.requires_confirmation is False
    assert response.action_executed is False

    session.refresh(first_visitor)
    session.refresh(second_visitor)

    assert first_visitor.status == VisitorStatus.ARRIVED
    assert second_visitor.status == VisitorStatus.ARRIVED

def test_resolve_agent_intent_passes_selected_skill_context(
    monkeypatch,
) -> None:
    """Unknown requests should pass selected skill context to the LLM."""

    from nexa_api import agent_service

    received_skill_context = None

    def fake_llm_resolver(
        message: str,
        skill_context: str | None = None,
    ) -> AgentDecision:
        nonlocal received_skill_context

        received_skill_context = skill_context

        return AgentDecision(
            intent=AgentIntent.GET_OPEN_TASKS,
            confidence=0.95,
        )

    monkeypatch.setattr(
        agent_service,
        "resolve_intent_with_llm",
        fake_llm_resolver,
    )

    decision = agent_service.resolve_agent_intent(
        "Could you check my tasks for me?"
    )

    assert decision.intent == AgentIntent.GET_OPEN_TASKS
    assert received_skill_context is not None
    assert "task-management" in received_skill_context

def test_resolve_agent_intent_supports_legacy_one_argument_llm_mock(
    monkeypatch,
) -> None:
    """Skill integration should preserve older one-argument test mocks."""

    from nexa_api import agent_service

    expected = AgentDecision(
        intent=AgentIntent.GET_OPEN_TASKS,
        confidence=0.95,
    )

    monkeypatch.setattr(
        agent_service,
        "resolve_intent_with_llm",
        lambda message: expected,
    )

    decision = agent_service.resolve_agent_intent(
        "Could you check my tasks for me?"
    )

    assert decision == expected