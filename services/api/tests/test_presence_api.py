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


def presence_payload(
    occupant_name: str = "Obumneme",
) -> dict[str, object]:
    """Return valid JSON for a household presence record."""

    return {
        "occupant_name": occupant_name,
        "status": "home",
        "note": "Currently at home",
    }


@pytest.mark.anyio
async def test_create_and_list_presence(
    test_app: FastAPI,
) -> None:
    """The API should create and list presence records."""

    transport = ASGITransport(app=test_app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        create_response = await client.post(
            "/api/v1/presence",
            json=presence_payload(),
        )

        list_response = await client.get(
            "/api/v1/presence"
        )

    assert create_response.status_code == 201

    created_presence = create_response.json()

    assert created_presence["occupant_name"] == "Obumneme"
    assert created_presence["status"] == "home"
    assert created_presence["id"]

    assert list_response.status_code == 200

    records = list_response.json()

    assert len(records) == 1
    assert records[0]["id"] == created_presence["id"]


@pytest.mark.anyio
async def test_filter_presence_by_status(
    test_app: FastAPI,
) -> None:
    """The API should filter presence records by status."""

    transport = ASGITransport(app=test_app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        await client.post(
            "/api/v1/presence",
            json=presence_payload("Ada"),
        )

        second_response = await client.post(
            "/api/v1/presence",
            json=presence_payload("Chidi"),
        )

        presence_id = second_response.json()["id"]

        await client.patch(
            f"/api/v1/presence/{presence_id}",
            json={
                "status": "away",
                "note": "At work",
            },
        )

        list_response = await client.get(
            "/api/v1/presence",
            params={"status": "home"},
        )

    assert list_response.status_code == 200

    records = list_response.json()

    assert len(records) == 1
    assert records[0]["occupant_name"] == "Ada"


@pytest.mark.anyio
async def test_get_presence(
    test_app: FastAPI,
) -> None:
    """The API should return one presence record."""

    transport = ASGITransport(app=test_app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        create_response = await client.post(
            "/api/v1/presence",
            json=presence_payload("Ngozi"),
        )

        presence_id = create_response.json()["id"]

        get_response = await client.get(
            f"/api/v1/presence/{presence_id}",
        )

    assert get_response.status_code == 200
    assert get_response.json()["occupant_name"] == "Ngozi"


@pytest.mark.anyio
async def test_get_missing_presence_returns_404(
    test_app: FastAPI,
) -> None:
    """Unknown presence IDs should return a clear 404 response."""

    transport = ASGITransport(app=test_app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.get(
            "/api/v1/presence/missing-presence",
        )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Presence record not found"
    }


@pytest.mark.anyio
async def test_update_presence(
    test_app: FastAPI,
) -> None:
    """The API should update occupant presence."""

    transport = ASGITransport(app=test_app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        create_response = await client.post(
            "/api/v1/presence",
            json=presence_payload("Tunde"),
        )

        presence_id = create_response.json()["id"]

        update_response = await client.patch(
            f"/api/v1/presence/{presence_id}",
            json={
                "status": "sleeping",
                "note": "Sleeping upstairs",
            },
        )

    assert update_response.status_code == 200

    updated_presence = update_response.json()

    assert updated_presence["status"] == "sleeping"
    assert updated_presence["note"] == "Sleeping upstairs"
    assert updated_presence["since"] is not None