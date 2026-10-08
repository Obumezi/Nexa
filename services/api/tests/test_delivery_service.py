from collections.abc import Generator
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from nexa_api.database import Base
from nexa_api.delivery_service import (
    create_delivery,
    get_delivery,
    list_deliveries,
    mark_delivery_collected,
    mark_delivery_delivered,
)
from nexa_api.enums import DeliveryStatus
from nexa_api.schemas import DeliveryCreate


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


def build_delivery_payload(
    description: str,
    expected_in_hours: int = 1,
) -> DeliveryCreate:
    """Build valid delivery data for service tests."""

    return DeliveryCreate(
        description=description,
        carrier="DHL",
        tracking_reference="NEXA-12345",
        expected_at=(
            datetime.now(UTC)
            + timedelta(hours=expected_in_hours)
        ),
        delivery_location="Front entrance",
        notes="Created during delivery service testing",
    )


def test_create_and_get_delivery(session: Session) -> None:
    payload = build_delivery_payload("Laptop package")

    created_delivery = create_delivery(session, payload)
    stored_delivery = get_delivery(
        session,
        created_delivery.id,
    )

    assert stored_delivery is not None
    assert stored_delivery.id == created_delivery.id
    assert stored_delivery.description == "Laptop package"
    assert stored_delivery.status == DeliveryStatus.EXPECTED


def test_list_deliveries_can_filter_by_status(
    session: Session,
) -> None:
    expected_delivery = create_delivery(
        session,
        build_delivery_payload(
            "Groceries",
            expected_in_hours=1,
        ),
    )

    delivered_delivery = create_delivery(
        session,
        build_delivery_payload(
            "Phone package",
            expected_in_hours=2,
        ),
    )

    mark_delivery_delivered(
        session,
        delivered_delivery,
    )

    expected_deliveries = list_deliveries(
        session,
        status=DeliveryStatus.EXPECTED,
    )

    assert [
        delivery.id for delivery in expected_deliveries
    ] == [expected_delivery.id]


def test_mark_delivery_delivered(
    session: Session,
) -> None:
    delivery = create_delivery(
        session,
        build_delivery_payload("Kitchen appliance"),
    )

    updated_delivery = mark_delivery_delivered(
        session,
        delivery,
    )

    assert updated_delivery.status == DeliveryStatus.DELIVERED
    assert updated_delivery.delivered_at is not None


def test_mark_delivery_collected(
    session: Session,
) -> None:
    delivery = create_delivery(
        session,
        build_delivery_payload("Book package"),
    )

    mark_delivery_delivered(session, delivery)

    updated_delivery = mark_delivery_collected(
        session,
        delivery,
    )

    assert updated_delivery.status == DeliveryStatus.COLLECTED
    assert updated_delivery.delivered_at is not None
    assert updated_delivery.collected_at is not None


def test_collecting_delivery_records_delivery_time(
    session: Session,
) -> None:
    delivery = create_delivery(
        session,
        build_delivery_payload("Emergency package"),
    )

    updated_delivery = mark_delivery_collected(
        session,
        delivery,
    )

    assert updated_delivery.status == DeliveryStatus.COLLECTED
    assert updated_delivery.delivered_at is not None
    assert updated_delivery.collected_at is not None