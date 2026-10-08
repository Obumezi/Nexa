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


def delivery_payload(
    description: str = "Laptop package",
) -> dict[str, object]:
    """Return valid JSON data for an expected delivery."""

    return {
        "description": description,
        "carrier": "DHL",
        "tracking_reference": "NEXA-12345",
        "expected_at": "2030-01-01T10:00:00Z",
        "delivery_location": "Front entrance",
        "notes": "Expected package for the household",
    }


@pytest.mark.anyio
async def test_create_and_list_deliveries(
    test_app: FastAPI,
) -> None:
    """The API should create and list deliveries."""

    transport = ASGITransport(app=test_app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        create_response = await client.post(
            "/api/v1/deliveries",
            json=delivery_payload(),
        )

        list_response = await client.get(
            "/api/v1/deliveries"
        )

    assert create_response.status_code == 201

    created_delivery = create_response.json()

    assert created_delivery["description"] == "Laptop package"
    assert created_delivery["status"] == "expected"
    assert created_delivery["id"]

    assert list_response.status_code == 200

    deliveries = list_response.json()

    assert len(deliveries) == 1
    assert deliveries[0]["id"] == created_delivery["id"]


@pytest.mark.anyio
async def test_filter_deliveries_by_status(
    test_app: FastAPI,
) -> None:
    """The API should filter deliveries by workflow status."""

    transport = ASGITransport(app=test_app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        first_response = await client.post(
            "/api/v1/deliveries",
            json=delivery_payload("Laptop package"),
        )

        second_response = await client.post(
            "/api/v1/deliveries",
            json=delivery_payload("Phone package"),
        )

        delivery_id = second_response.json()["id"]

        await client.post(
            f"/api/v1/deliveries/{delivery_id}/deliver",
        )

        list_response = await client.get(
            "/api/v1/deliveries",
            params={"status": "expected"},
        )

    assert first_response.status_code == 201
    assert second_response.status_code == 201
    assert list_response.status_code == 200

    deliveries = list_response.json()

    assert len(deliveries) == 1
    assert deliveries[0]["description"] == "Laptop package"


@pytest.mark.anyio
async def test_get_delivery(
    test_app: FastAPI,
) -> None:
    """The API should return one delivery."""

    transport = ASGITransport(app=test_app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        create_response = await client.post(
            "/api/v1/deliveries",
            json=delivery_payload("Book package"),
        )

        delivery_id = create_response.json()["id"]

        get_response = await client.get(
            f"/api/v1/deliveries/{delivery_id}",
        )

    assert get_response.status_code == 200
    assert get_response.json()["description"] == "Book package"


@pytest.mark.anyio
async def test_get_missing_delivery_returns_404(
    test_app: FastAPI,
) -> None:
    """Unknown delivery IDs should return a clear 404 response."""

    transport = ASGITransport(app=test_app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.get(
            "/api/v1/deliveries/missing-delivery",
        )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Delivery not found"
    }


@pytest.mark.anyio
async def test_delivery_and_collection_workflow(
    test_app: FastAPI,
) -> None:
    """The API should record delivery and collection."""

    transport = ASGITransport(app=test_app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        create_response = await client.post(
            "/api/v1/deliveries",
            json=delivery_payload("Kitchen appliance"),
        )

        delivery_id = create_response.json()["id"]

        delivery_response = await client.post(
            f"/api/v1/deliveries/{delivery_id}/deliver",
        )

        collection_response = await client.post(
            f"/api/v1/deliveries/{delivery_id}/collect",
        )

    assert delivery_response.status_code == 200
    assert delivery_response.json()["status"] == "delivered"
    assert delivery_response.json()["delivered_at"] is not None

    assert collection_response.status_code == 200
    assert collection_response.json()["status"] == "collected"
    assert collection_response.json()["collected_at"] is not None