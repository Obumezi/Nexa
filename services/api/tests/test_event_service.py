from collections.abc import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from nexa_api.database import Base
from nexa_api.enums import EventSource, EventType
from nexa_api.event_service import (
    create_event,
    get_event,
    list_events,
)
from nexa_api.schemas import EventCreate


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


def test_create_and_get_event(session: Session) -> None:
    payload = EventCreate(
        event_type=EventType.VISITOR_DETECTED,
        source=EventSource.RING_SIMULATOR,
        location="front_door",
        summary="Visitor detected at the front door",
        confidence=92,
    )

    created_event = create_event(session, payload)
    stored_event = get_event(
        session,
        created_event.id,
    )

    assert stored_event is not None
    assert stored_event.id == created_event.id
    assert stored_event.event_type == EventType.VISITOR_DETECTED
    assert stored_event.source == EventSource.RING_SIMULATOR
    assert stored_event.confidence == 92
    assert stored_event.occurred_at is not None


def test_list_events_can_filter_by_type(
    session: Session,
) -> None:
    create_event(
        session,
        EventCreate(
            event_type=EventType.VISITOR_DETECTED,
            summary="Visitor detected",
        ),
    )

    create_event(
        session,
        EventCreate(
            event_type=EventType.PACKAGE_DELIVERED,
            summary="Package delivered",
        ),
    )

    visitor_events = list_events(
        session,
        event_type=EventType.VISITOR_DETECTED,
    )

    assert len(visitor_events) == 1
    assert (
        visitor_events[0].event_type
        == EventType.VISITOR_DETECTED
    )


def test_list_events_can_filter_by_source(
    session: Session,
) -> None:
    create_event(
        session,
        EventCreate(
            event_type=EventType.SYSTEM,
            source=EventSource.SYSTEM,
            summary="System event",
        ),
    )

    create_event(
        session,
        EventCreate(
            event_type=EventType.DOORBELL_PRESSED,
            source=EventSource.RING_SIMULATOR,
            summary="Doorbell pressed",
        ),
    )

    system_events = list_events(
        session,
        source=EventSource.SYSTEM,
    )

    assert len(system_events) == 1
    assert system_events[0].source == EventSource.SYSTEM


def test_event_uses_database_timestamp_when_omitted(
    session: Session,
) -> None:
    event = create_event(
        session,
        EventCreate(
            event_type=EventType.MOTION_DETECTED,
            summary="Motion detected",
        ),
    )

    assert event.occurred_at is not None
    assert event.created_at is not None