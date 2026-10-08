from collections.abc import Generator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from nexa_api.database import Base, get_db
from nexa_api.enums import DeliveryStatus, TaskStatus, VisitorStatus
from nexa_api.main import app
from nexa_api.models import (
    Delivery,
    ExpectedVisitor,
    HouseholdTask,
)


@pytest.fixture
def anyio_backend() -> str:
    """Run asynchronous tests using asyncio."""

    return "asyncio"


@pytest.fixture
def session() -> Generator[Session, None, None]:
    """Provide an isolated SQLite session."""

    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    Base.metadata.create_all(test_engine)

    with Session(test_engine) as database_session:
        yield database_session

    Base.metadata.drop_all(test_engine)


@pytest.fixture
def test_app(
    session: Session,
) -> Generator[FastAPI, None, None]:
    """Override the production database dependency."""

    def override_get_db() -> Generator[Session, None, None]:
        yield session

    app.dependency_overrides[get_db] = override_get_db

    yield app

    app.dependency_overrides.clear()


def event_payload(
    event_type: str = "visitor_detected",
) -> dict[str, object]:
    """Return valid JSON for a home event."""

    return {
        "event_type": event_type,
        "source": "ring_simulator",
        "location": "front_door",
        "summary": "Activity detected at the front door",
        "confidence": 94,
        "is_simulated": True,
    }


@pytest.mark.anyio
async def test_create_and_list_events(
    test_app: FastAPI,
) -> None:
    transport = ASGITransport(app=test_app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        create_response = await client.post(
            "/api/v1/events",
            json=event_payload(),
        )

        list_response = await client.get(
            "/api/v1/events"
        )

    assert create_response.status_code == 201

    created_event = create_response.json()

    assert created_event["event_type"] == "visitor_detected"
    assert created_event["source"] == "ring_simulator"
    assert created_event["id"]

    assert list_response.status_code == 200

    events = list_response.json()

    assert len(events) == 1
    assert events[0]["id"] == created_event["id"]


@pytest.mark.anyio
async def test_filter_events_by_type(
    test_app: FastAPI,
) -> None:
    transport = ASGITransport(app=test_app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        await client.post(
            "/api/v1/events",
            json=event_payload("visitor_detected"),
        )

        await client.post(
            "/api/v1/events",
            json=event_payload("package_delivered"),
        )

        response = await client.get(
            "/api/v1/events",
            params={"event_type": "visitor_detected"},
        )

    assert response.status_code == 200

    events = response.json()

    assert len(events) == 1
    assert events[0]["event_type"] == "visitor_detected"


@pytest.mark.anyio
async def test_filter_events_by_source(
    test_app: FastAPI,
) -> None:
    transport = ASGITransport(app=test_app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        await client.post(
            "/api/v1/events",
            json=event_payload(),
        )

        system_payload = event_payload("system")
        system_payload["source"] = "system"

        await client.post(
            "/api/v1/events",
            json=system_payload,
        )

        response = await client.get(
            "/api/v1/events",
            params={"source": "system"},
        )

    assert response.status_code == 200

    events = response.json()

    assert len(events) == 1
    assert events[0]["source"] == "system"


@pytest.mark.anyio
async def test_get_event(
    test_app: FastAPI,
) -> None:
    transport = ASGITransport(app=test_app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        create_response = await client.post(
            "/api/v1/events",
            json=event_payload("doorbell_pressed"),
        )

        event_id = create_response.json()["id"]

        response = await client.get(
            f"/api/v1/events/{event_id}",
        )

    assert response.status_code == 200
    assert response.json()["event_type"] == "doorbell_pressed"


@pytest.mark.anyio
async def test_get_missing_event_returns_404(
    test_app: FastAPI,
) -> None:
    transport = ASGITransport(app=test_app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.get(
            "/api/v1/events/missing-event",
        )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Event not found"
    }


@pytest.mark.anyio
async def test_event_confidence_validation(
    test_app: FastAPI,
) -> None:
    transport = ASGITransport(app=test_app)

    payload = event_payload()
    payload["confidence"] = 101

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/events",
            json=payload,
        )

    assert response.status_code == 422

@pytest.mark.anyio
async def test_visitor_event_marks_matching_visitor_arrived(
    test_app: FastAPI,
    session: Session,
) -> None:
    """Posting a visitor event should update a matching visitor."""

    now = datetime.now(UTC)

    visitor = ExpectedVisitor(
        name="Ada Okafor",
        purpose="Electrical repair appointment",
        expected_start=now - timedelta(minutes=15),
        expected_end=now + timedelta(minutes=45),
    )

    session.add(visitor)
    session.commit()
    session.refresh(visitor)

    transport = ASGITransport(app=test_app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/events",
            json={
                "event_type": "visitor_detected",
                "source": "ring_simulator",
                "location": "front_door",
                "summary": "Visitor detected",
                "confidence": 96,
                "occurred_at": now.isoformat(),
            },
        )

    assert response.status_code == 201

    session.refresh(visitor)

    event = response.json()

    assert visitor.status == VisitorStatus.ARRIVED
    assert visitor.arrived_at is not None
    assert event["related_visitor_id"] == visitor.id
    assert event["related_task_id"] is None


@pytest.mark.anyio
async def test_unmatched_visitor_event_creates_review_task(
    test_app: FastAPI,
    session: Session,
) -> None:
    """An unmatched visitor event should create a review task."""

    transport = ASGITransport(app=test_app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/events",
            json={
                "event_type": "visitor_detected",
                "source": "ring_simulator",
                "location": "front_door",
                "summary": "Unexpected visitor detected",
                "confidence": 88,
            },
        )

    assert response.status_code == 201

    event = response.json()

    assert event["related_visitor_id"] is None
    assert event["related_task_id"] is not None

    task = session.get(
        HouseholdTask,
        event["related_task_id"],
    )

    assert task is not None
    assert task.title == "Review unexpected visitor"
    assert task.status == TaskStatus.OPEN
    assert task.requires_confirmation is True

@pytest.mark.anyio
async def test_package_event_marks_matching_delivery_delivered(
    test_app: FastAPI,
    session: Session,
) -> None:
    """Posting a package event should update a matching delivery."""

    delivery = Delivery(
        description="Laptop package",
        carrier="DHL",
        tracking_reference="NEXA-2001",
    )

    session.add(delivery)
    session.commit()
    session.refresh(delivery)

    transport = ASGITransport(app=test_app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/events",
            json={
                "event_type": "package_delivered",
                "source": "ring_simulator",
                "location": "front_door",
                "summary": "Package delivered",
                "confidence": 95,
            },
        )

    assert response.status_code == 201

    session.refresh(delivery)

    event = response.json()

    assert delivery.status == DeliveryStatus.DELIVERED
    assert delivery.delivered_at is not None
    assert event["related_delivery_id"] == delivery.id
    assert event["related_task_id"] is None


@pytest.mark.anyio
async def test_unmatched_package_event_creates_review_task(
    test_app: FastAPI,
    session: Session,
) -> None:
    """An unmatched package event should create a review task."""

    transport = ASGITransport(app=test_app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/events",
            json={
                "event_type": "package_delivered",
                "source": "ring_simulator",
                "location": "front_door",
                "summary": "Unexpected package delivered",
                "confidence": 90,
            },
        )

    assert response.status_code == 201

    event = response.json()

    assert event["related_delivery_id"] is None
    assert event["related_task_id"] is not None

    task = session.get(
        HouseholdTask,
        event["related_task_id"],
    )

    assert task is not None
    assert task.title == "Review unexpected delivery"
    assert task.status == TaskStatus.OPEN
    assert task.requires_confirmation is True