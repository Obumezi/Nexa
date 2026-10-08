from collections.abc import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from nexa_api.database import Base
from nexa_api.enums import TaskPriority, TaskStatus
from nexa_api.schemas import TaskCreate, TaskUpdate
from nexa_api.task_service import (
    complete_task,
    create_task,
    get_task,
    list_tasks,
    update_task,
)


@pytest.fixture
def session() -> Generator[Session, None, None]:
    """Provide a clean in-memory database session."""

    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    Base.metadata.create_all(test_engine)

    with Session(test_engine) as database_session:
        yield database_session

    Base.metadata.drop_all(test_engine)


def test_create_and_get_task(session: Session) -> None:
    """A task should be created and retrieved by its ID."""

    task = create_task(
        session,
        TaskCreate(
            title="Repair kitchen socket",
            priority=TaskPriority.HIGH,
            requires_confirmation=True,
        ),
    )

    saved_task = get_task(session, task.id)

    assert saved_task is not None
    assert saved_task.title == "Repair kitchen socket"
    assert saved_task.priority == TaskPriority.HIGH
    assert saved_task.status == TaskStatus.OPEN


def test_list_tasks_can_filter_by_status(
    session: Session,
) -> None:
    """Task listing should support status filters."""

    first_task = create_task(
        session,
        TaskCreate(title="First task"),
    )
    create_task(
        session,
        TaskCreate(title="Second task"),
    )

    complete_task(session, first_task)

    open_tasks = list_tasks(session, status=TaskStatus.OPEN)
    completed_tasks = list_tasks(
        session,
        status=TaskStatus.COMPLETED,
    )

    assert len(open_tasks) == 1
    assert open_tasks[0].title == "Second task"

    assert len(completed_tasks) == 1
    assert completed_tasks[0].title == "First task"


def test_update_task(session: Session) -> None:
    """Supplied task fields should be updated."""

    task = create_task(
        session,
        TaskCreate(title="Old task title"),
    )

    updated_task = update_task(
        session,
        task,
        TaskUpdate(
            title="New task title",
            priority=TaskPriority.CRITICAL,
        ),
    )

    assert updated_task.title == "New task title"
    assert updated_task.priority == TaskPriority.CRITICAL


def test_complete_task_is_idempotent(
    session: Session,
) -> None:
    """Completing an already completed task should remain safe."""

    task = create_task(
        session,
        TaskCreate(title="Bring package inside"),
    )

    completed_task = complete_task(session, task)
    first_completion_time = completed_task.completed_at

    completed_again = complete_task(session, completed_task)

    assert completed_again.status == TaskStatus.COMPLETED
    assert completed_again.completed_at == first_completion_time