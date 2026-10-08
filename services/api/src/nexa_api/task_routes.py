from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from nexa_api.database import get_db
from nexa_api.enums import TaskStatus
from nexa_api.models import HouseholdTask
from nexa_api.schemas import TaskCreate, TaskRead, TaskUpdate
from nexa_api.task_service import (
    complete_task,
    create_task,
    get_task,
    list_tasks,
    update_task,
)

router = APIRouter(
    prefix="/api/v1/tasks",
    tags=["tasks"],
)

DatabaseSession = Annotated[Session, Depends(get_db)]


def require_task(
    session: Session,
    task_id: str,
) -> HouseholdTask:
    """Return a task or raise an API 404 response."""

    task = get_task(session, task_id)

    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    return task


@router.post(
    "",
    response_model=TaskRead,
    status_code=status.HTTP_201_CREATED,
)
def create_task_endpoint(
    payload: TaskCreate,
    session: DatabaseSession,
) -> HouseholdTask:
    """Create a new household task."""

    return create_task(session, payload)


@router.get(
    "",
    response_model=list[TaskRead],
)
def list_tasks_endpoint(
    session: DatabaseSession,
    status_filter: Annotated[
        TaskStatus | None,
        Query(alias="status"),
    ] = None,
) -> list[HouseholdTask]:
    """Return household tasks, optionally filtered by status."""

    return list_tasks(session, status=status_filter)


@router.get(
    "/{task_id}",
    response_model=TaskRead,
)
def get_task_endpoint(
    task_id: str,
    session: DatabaseSession,
) -> HouseholdTask:
    """Return one household task."""

    return require_task(session, task_id)


@router.patch(
    "/{task_id}",
    response_model=TaskRead,
)
def update_task_endpoint(
    task_id: str,
    payload: TaskUpdate,
    session: DatabaseSession,
) -> HouseholdTask:
    """Update selected fields on a household task."""

    task = require_task(session, task_id)

    return update_task(session, task, payload)


@router.post(
    "/{task_id}/complete",
    response_model=TaskRead,
)
def complete_task_endpoint(
    task_id: str,
    session: DatabaseSession,
) -> HouseholdTask:
    """Mark a household task as completed."""

    task = require_task(session, task_id)

    return complete_task(session, task)