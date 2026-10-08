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


@pytest.mark.anyio
async def test_create_and_list_tasks(
    test_app: FastAPI,
) -> None:
    """The API should create and list household tasks."""

    transport = ASGITransport(app=test_app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        create_response = await client.post(
            "/api/v1/tasks",
            json={
                "title": "Repair kitchen socket",
                "priority": "high",
                "requires_confirmation": True,
            },
        )

        list_response = await client.get("/api/v1/tasks")

    assert create_response.status_code == 201

    created_task = create_response.json()

    assert created_task["title"] == "Repair kitchen socket"
    assert created_task["status"] == "open"
    assert created_task["priority"] == "high"
    assert created_task["requires_confirmation"] is True
    assert created_task["id"]

    assert list_response.status_code == 200

    tasks = list_response.json()

    assert len(tasks) == 1
    assert tasks[0]["id"] == created_task["id"]


@pytest.mark.anyio
async def test_create_task_rejects_blank_title(
    test_app: FastAPI,
) -> None:
    """The API should reject whitespace-only task titles."""

    transport = ASGITransport(app=test_app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/tasks",
            json={"title": "   "},
        )

    assert response.status_code == 422


@pytest.mark.anyio
async def test_get_missing_task_returns_404(
    test_app: FastAPI,
) -> None:
    """Unknown task IDs should return a clear 404 response."""

    transport = ASGITransport(app=test_app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.get(
            "/api/v1/tasks/missing-task",
        )

    assert response.status_code == 404
    assert response.json() == {"detail": "Task not found"}


@pytest.mark.anyio
async def test_update_task(
    test_app: FastAPI,
) -> None:
    """The API should update supplied task fields."""

    transport = ASGITransport(app=test_app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        create_response = await client.post(
            "/api/v1/tasks",
            json={"title": "Old task title"},
        )

        task_id = create_response.json()["id"]

        update_response = await client.patch(
            f"/api/v1/tasks/{task_id}",
            json={
                "title": "New task title",
                "priority": "critical",
            },
        )

    assert update_response.status_code == 200

    updated_task = update_response.json()

    assert updated_task["title"] == "New task title"
    assert updated_task["priority"] == "critical"


@pytest.mark.anyio
async def test_complete_task_is_idempotent(
    test_app: FastAPI,
) -> None:
    """Completing a task more than once should remain safe."""

    transport = ASGITransport(app=test_app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        create_response = await client.post(
            "/api/v1/tasks",
            json={"title": "Bring package inside"},
        )

        task_id = create_response.json()["id"]

        first_response = await client.post(
            f"/api/v1/tasks/{task_id}/complete",
        )
        second_response = await client.post(
            f"/api/v1/tasks/{task_id}/complete",
        )

    assert first_response.status_code == 200
    assert second_response.status_code == 200

    first_result = first_response.json()
    second_result = second_response.json()

    assert first_result["status"] == "completed"
    assert first_result["completed_at"] is not None
    assert second_result["completed_at"] == first_result["completed_at"]