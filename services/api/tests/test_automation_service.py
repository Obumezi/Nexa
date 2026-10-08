from collections.abc import Generator
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from nexa_api.automation_service import (
    process_delivery_event,
    process_event,
    process_visitor_event,
)
from nexa_api.database import Base
from nexa_api.delivery_service import create_delivery
from nexa_api.enums import (
    DeliveryStatus,
    EventType,
    TaskPriority,
    TaskStatus,
    VisitorStatus,
)
from nexa_api.event_service import create_event
from nexa_api.schemas import DeliveryCreate, EventCreate, VisitorCreate
from nexa_api.visitor_service import create_visitor


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


def test_visitor_event_matches_expected_visitor(
    session: Session,
) -> None:
    """A visitor event should match an active expected visitor."""

    now = datetime.now(UTC)

    visitor = create_visitor(
        session,
        VisitorCreate(
            name="Ada Okafor",
            purpose="Electrical repair appointment",
            expected_start=now - timedelta(minutes=15),
            expected_end=now + timedelta(minutes=45),
        ),
    )

    event = create_event(
        session,
        EventCreate(
            event_type=EventType.VISITOR_DETECTED,
            summary="Visitor detected",
            occurred_at=now,
            confidence=96,
        ),
    )

    result = process_visitor_event(
        session,
        event,
    )

    assert result is not None
    assert result.id == visitor.id
    assert visitor.status == VisitorStatus.ARRIVED
    assert visitor.arrived_at is not None
    assert event.related_visitor_id == visitor.id
    assert event.related_task_id is None


def test_unmatched_visitor_creates_task(
    session: Session,
) -> None:
    """An unexpected visitor should create a review task."""

    event = create_event(
        session,
        EventCreate(
            event_type=EventType.VISITOR_DETECTED,
            summary="Unknown visitor detected",
            occurred_at=datetime.now(UTC),
            confidence=88,
        ),
    )

    result = process_visitor_event(
        session,
        event,
    )

    assert result is not None
    assert result.title == "Review unexpected visitor"
    assert result.status == TaskStatus.OPEN
    assert result.priority == TaskPriority.HIGH
    assert result.requires_confirmation is True
    assert event.related_task_id == result.id
    assert event.related_visitor_id is None


def test_non_visitor_event_is_ignored(
    session: Session,
) -> None:
    """Other event types should not trigger visitor processing."""

    event = create_event(
        session,
        EventCreate(
            event_type=EventType.MOTION_DETECTED,
            summary="Motion detected",
        ),
    )

    result = process_visitor_event(
        session,
        event,
    )

    assert result is None
    assert event.related_visitor_id is None
    assert event.related_task_id is None


def test_processing_matched_event_is_idempotent(
    session: Session,
) -> None:
    """Processing the same matched event twice should not duplicate work."""

    now = datetime.now(UTC)

    visitor = create_visitor(
        session,
        VisitorCreate(
            name="Chidi Eze",
            purpose="Scheduled visit",
            expected_start=now - timedelta(minutes=10),
            expected_end=now + timedelta(minutes=30),
        ),
    )

    event = create_event(
        session,
        EventCreate(
            event_type=EventType.VISITOR_DETECTED,
            summary="Visitor detected",
            occurred_at=now,
        ),
    )

    first_result = process_visitor_event(
        session,
        event,
    )

    first_arrived_at = visitor.arrived_at

    second_result = process_visitor_event(
        session,
        event,
    )

    assert first_result is not None
    assert second_result is not None
    assert second_result.id == visitor.id
    assert visitor.arrived_at == first_arrived_at
    assert event.related_visitor_id == visitor.id


def test_processing_unmatched_event_is_idempotent(
    session: Session,
) -> None:
    """Repeated processing should not create duplicate review tasks."""

    event = create_event(
        session,
        EventCreate(
            event_type=EventType.VISITOR_DETECTED,
            summary="Unexpected visitor",
            occurred_at=datetime.now(UTC),
        ),
    )

    first_result = process_visitor_event(
        session,
        event,
    )

    second_result = process_visitor_event(
        session,
        event,
    )

    assert first_result is not None
    assert second_result is not None
    assert second_result.id == first_result.id
    assert event.related_task_id == first_result.id

def test_package_event_matches_expected_delivery(
    session: Session,
) -> None:
    """A package event should match an expected delivery."""

    delivery = create_delivery(
        session,
        DeliveryCreate(
            description="Laptop package",
            carrier="DHL",
            tracking_reference="NEXA-1001",
        ),
    )

    event = create_event(
        session,
        EventCreate(
            event_type=EventType.PACKAGE_DELIVERED,
            summary="Package delivered at front door",
        ),
    )

    result = process_delivery_event(
        session,
        event,
    )

    assert result is not None
    assert result.id == delivery.id
    assert delivery.status == DeliveryStatus.DELIVERED
    assert delivery.delivered_at is not None
    assert event.related_delivery_id == delivery.id
    assert event.related_task_id is None


def test_unmatched_package_event_creates_task(
    session: Session,
) -> None:
    """An unexpected package should create a review task."""

    event = create_event(
        session,
        EventCreate(
            event_type=EventType.PACKAGE_DELIVERED,
            summary="Unexpected package delivered",
        ),
    )

    result = process_delivery_event(
        session,
        event,
    )

    assert result is not None
    assert result.title == "Review unexpected delivery"
    assert result.status == TaskStatus.OPEN
    assert result.priority == TaskPriority.HIGH
    assert result.requires_confirmation is True
    assert event.related_task_id == result.id
    assert event.related_delivery_id is None


def test_non_package_event_is_ignored_by_delivery_processor(
    session: Session,
) -> None:
    """Non-package events should not trigger delivery processing."""

    event = create_event(
        session,
        EventCreate(
            event_type=EventType.MOTION_DETECTED,
            summary="Motion detected",
        ),
    )

    result = process_delivery_event(
        session,
        event,
    )

    assert result is None
    assert event.related_delivery_id is None
    assert event.related_task_id is None


def test_processing_matched_package_event_is_idempotent(
    session: Session,
) -> None:
    """Processing the same package event twice should not duplicate work."""

    delivery = create_delivery(
        session,
        DeliveryCreate(
            description="Phone package",
            carrier="FedEx",
        ),
    )

    event = create_event(
        session,
        EventCreate(
            event_type=EventType.PACKAGE_DELIVERED,
            summary="Package delivered",
        ),
    )

    first_result = process_delivery_event(
        session,
        event,
    )

    first_delivered_at = delivery.delivered_at

    second_result = process_delivery_event(
        session,
        event,
    )

    assert first_result is not None
    assert second_result is not None
    assert second_result.id == delivery.id
    assert delivery.delivered_at == first_delivered_at
    assert event.related_delivery_id == delivery.id


def test_processing_unmatched_package_event_is_idempotent(
    session: Session,
) -> None:
    """Repeated processing should not create duplicate review tasks."""

    event = create_event(
        session,
        EventCreate(
            event_type=EventType.PACKAGE_DELIVERED,
            summary="Unexpected delivery",
        ),
    )

    first_result = process_delivery_event(
        session,
        event,
    )

    second_result = process_delivery_event(
        session,
        event,
    )

    assert first_result is not None
    assert second_result is not None
    assert second_result.id == first_result.id
    assert event.related_task_id == first_result.id


def test_process_event_routes_visitor_detection(
    session: Session,
) -> None:
    """The orchestrator should route visitor events correctly."""

    now = datetime.now(UTC)

    visitor = create_visitor(
        session,
        VisitorCreate(
            name="Ada Okafor",
            purpose="Scheduled visit",
            expected_start=now - timedelta(minutes=10),
            expected_end=now + timedelta(minutes=30),
        ),
    )

    event = create_event(
        session,
        EventCreate(
            event_type=EventType.VISITOR_DETECTED,
            summary="Visitor detected",
            occurred_at=now,
        ),
    )

    result = process_event(
        session,
        event,
    )

    assert result is not None
    assert result.id == visitor.id
    assert visitor.status == VisitorStatus.ARRIVED
    assert event.related_visitor_id == visitor.id


def test_process_event_routes_package_delivery(
    session: Session,
) -> None:
    """The orchestrator should route package events correctly."""

    delivery = create_delivery(
        session,
        DeliveryCreate(
            description="Laptop package",
            carrier="DHL",
        ),
    )

    event = create_event(
        session,
        EventCreate(
            event_type=EventType.PACKAGE_DELIVERED,
            summary="Package delivered",
        ),
    )

    result = process_event(
        session,
        event,
    )

    assert result is not None
    assert result.id == delivery.id
    assert delivery.status == DeliveryStatus.DELIVERED
    assert event.related_delivery_id == delivery.id


def test_process_event_ignores_unsupported_event(
    session: Session,
) -> None:
    """Unsupported event types should currently require no action."""

    event = create_event(
        session,
        EventCreate(
            event_type=EventType.DOORBELL_PRESSED,
            summary="Doorbell pressed",
        ),
    )

    result = process_event(
        session,
        event,
    )

    assert result is None
    assert event.related_visitor_id is None
    assert event.related_delivery_id is None
    assert event.related_task_id is None