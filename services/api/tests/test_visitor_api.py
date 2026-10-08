from collections.abc import Generator

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from nexa_api.database import Base, get_db
from nexa_api.main import app


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


def visitor_payload(
    name: str = "Ada Okafor",
) -> dict[str, object]:
    """Return valid JSON data for an expected visitor."""

    return {
        "name": name,
        "purpose": "Scheduled home visit",
        "expected_start": "2030-01-01T10:00:00Z",
        "expected_end": "2030-01-01T11:00:00Z",
        "notes": "Expected through the front entrance",
    }


@pytest.mark.anyio
async def test_create_and_list_visitors(
    test_app: FastAPI,
) -> None:
    """The API should create and list expected visitors."""

    transport = ASGITransport(app=test_app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        create_response = await client.post(
            "/api/v1/visitors",
            json=visitor_payload(),
        )

        list_response = await client.get("/api/v1/visitors")

    assert create_response.status_code == 201

    created_visitor = create_response.json()

    assert created_visitor["name"] == "Ada Okafor"
    assert created_visitor["status"] == "expected"
    assert created_visitor["id"]

    assert list_response.status_code == 200

    visitors = list_response.json()

    assert len(visitors) == 1
    assert visitors[0]["id"] == created_visitor["id"]


@pytest.mark.anyio
async def test_filter_visitors_by_status(
    test_app: FastAPI,
) -> None:
    """The API should filter visitors by workflow status."""

    transport = ASGITransport(app=test_app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        first_response = await client.post(
            "/api/v1/visitors",
            json=visitor_payload("Ada Okafor"),
        )
        second_response = await client.post(
            "/api/v1/visitors",
            json=visitor_payload("Chidi Eze"),
        )

        visitor_id = second_response.json()["id"]

        await client.post(
            f"/api/v1/visitors/{visitor_id}/arrive",
        )

        list_response = await client.get(
            "/api/v1/visitors",
            params={"status": "expected"},
        )

    assert first_response.status_code == 201
    assert second_response.status_code == 201
    assert list_response.status_code == 200

    visitors = list_response.json()

    assert len(visitors) == 1
    assert visitors[0]["name"] == "Ada Okafor"


@pytest.mark.anyio
async def test_get_visitor(
    test_app: FastAPI,
) -> None:
    """The API should return one expected visitor."""

    transport = ASGITransport(app=test_app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        create_response = await client.post(
            "/api/v1/visitors",
            json=visitor_payload("Ngozi Umeh"),
        )

        visitor_id = create_response.json()["id"]

        get_response = await client.get(
            f"/api/v1/visitors/{visitor_id}",
        )

    assert get_response.status_code == 200
    assert get_response.json()["name"] == "Ngozi Umeh"


@pytest.mark.anyio
async def test_get_missing_visitor_returns_404(
    test_app: FastAPI,
) -> None:
    """Unknown visitor IDs should return a clear 404 response."""

    transport = ASGITransport(app=test_app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.get(
            "/api/v1/visitors/missing-visitor",
        )

    assert response.status_code == 404
    assert response.json() == {"detail": "Visitor not found"}


@pytest.mark.anyio
async def test_visitor_arrival_and_departure(
    test_app: FastAPI,
) -> None:
    """The API should record visitor arrival and departure."""

    transport = ASGITransport(app=test_app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        create_response = await client.post(
            "/api/v1/visitors",
            json=visitor_payload("Tunde Bello"),
        )

        visitor_id = create_response.json()["id"]

        arrival_response = await client.post(
            f"/api/v1/visitors/{visitor_id}/arrive",
        )
        departure_response = await client.post(
            f"/api/v1/visitors/{visitor_id}/depart",
        )

    assert arrival_response.status_code == 200
    assert arrival_response.json()["status"] == "arrived"
    assert arrival_response.json()["arrived_at"] is not None

    assert departure_response.status_code == 200
    assert departure_response.json()["status"] == "departed"
    assert departure_response.json()["departed_at"] is not None


@pytest.mark.anyio
async def test_cancel_visitor(
    test_app: FastAPI,
) -> None:
    """The API should cancel an expected visitor."""

    transport = ASGITransport(app=test_app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        create_response = await client.post(
            "/api/v1/visitors",
            json=visitor_payload("Ibrahim Musa"),
        )

        visitor_id = create_response.json()["id"]

        cancel_response = await client.post(
            f"/api/v1/visitors/{visitor_id}/cancel",
        )

    assert cancel_response.status_code == 200
    assert cancel_response.json()["status"] == "cancelled"