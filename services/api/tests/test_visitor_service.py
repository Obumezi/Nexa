from collections.abc import Generator
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from nexa_api.database import Base
from nexa_api.enums import VisitorStatus
from nexa_api.schemas import VisitorCreate
from nexa_api.visitor_service import (
    cancel_visitor,
    create_visitor,
    get_visitor,
    list_visitors,
    mark_visitor_arrived,
    mark_visitor_departed,
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


def build_visitor_payload(
    name: str,
    starts_in_hours: int = 1,
) -> VisitorCreate:
    """Build valid visitor data for service tests."""

    expected_start = datetime.now(UTC) + timedelta(
        hours=starts_in_hours
    )

    return VisitorCreate(
        name=name,
        purpose="Scheduled home visit",
        expected_start=expected_start,
        expected_end=expected_start + timedelta(hours=1),
        notes="Created during visitor service testing",
    )


def test_create_and_get_visitor(session: Session) -> None:
    payload = build_visitor_payload("Ada Okafor")

    created_visitor = create_visitor(session, payload)
    stored_visitor = get_visitor(session, created_visitor.id)

    assert stored_visitor is not None
    assert stored_visitor.id == created_visitor.id
    assert stored_visitor.name == "Ada Okafor"
    assert stored_visitor.status == VisitorStatus.EXPECTED


def test_list_visitors_can_filter_by_status(
    session: Session,
) -> None:
    expected_visitor = create_visitor(
        session,
        build_visitor_payload("Chidi Eze", starts_in_hours=1),
    )
    arrived_visitor = create_visitor(
        session,
        build_visitor_payload("Amaka Obi", starts_in_hours=2),
    )

    mark_visitor_arrived(session, arrived_visitor)

    expected_visitors = list_visitors(
        session,
        status=VisitorStatus.EXPECTED,
    )

    assert [visitor.id for visitor in expected_visitors] == [
        expected_visitor.id
    ]


def test_mark_visitor_arrived(session: Session) -> None:
    visitor = create_visitor(
        session,
        build_visitor_payload("Tunde Bello"),
    )

    updated_visitor = mark_visitor_arrived(session, visitor)

    assert updated_visitor.status == VisitorStatus.ARRIVED
    assert updated_visitor.arrived_at is not None


def test_mark_visitor_departed(session: Session) -> None:
    visitor = create_visitor(
        session,
        build_visitor_payload("Ngozi Umeh"),
    )

    mark_visitor_arrived(session, visitor)
    updated_visitor = mark_visitor_departed(session, visitor)

    assert updated_visitor.status == VisitorStatus.DEPARTED
    assert updated_visitor.departed_at is not None


def test_cancel_visitor(session: Session) -> None:
    visitor = create_visitor(
        session,
        build_visitor_payload("Ibrahim Musa"),
    )

    updated_visitor = cancel_visitor(session, visitor)

    assert updated_visitor.status == VisitorStatus.CANCELLED