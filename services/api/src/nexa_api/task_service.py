from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from nexa_api.enums import TaskStatus
from nexa_api.models import HouseholdTask
from nexa_api.schemas import TaskCreate, TaskUpdate


def create_task(
    session: Session,
    payload: TaskCreate,
) -> HouseholdTask:
    """Create and save a household task."""

    task = HouseholdTask(**payload.model_dump())

    session.add(task)
    session.commit()
    session.refresh(task)

    return task


def get_task(
    session: Session,
    task_id: str,
) -> HouseholdTask | None:
    """Return one household task or None when it does not exist."""

    return session.get(HouseholdTask, task_id)


def list_tasks(
    session: Session,
    status: TaskStatus | None = None,
) -> list[HouseholdTask]:
    """Return household tasks, optionally filtered by status."""

    statement = select(HouseholdTask).order_by(
        HouseholdTask.created_at.desc()
    )

    if status is not None:
        statement = statement.where(
            HouseholdTask.status == status
        )

    return list(session.scalars(statement))


def update_task(
    session: Session,
    task: HouseholdTask,
    payload: TaskUpdate,
) -> HouseholdTask:
    """Apply supplied changes to an existing household task."""

    changes = payload.model_dump(exclude_unset=True)

    for field_name, value in changes.items():
        setattr(task, field_name, value)

    session.add(task)
    session.commit()
    session.refresh(task)

    return task


def complete_task(
    session: Session,
    task: HouseholdTask,
) -> HouseholdTask:
    """Mark an open household task as completed."""

    if task.status == TaskStatus.COMPLETED:
        return task

    task.status = TaskStatus.COMPLETED
    task.completed_at = datetime.now(UTC)

    session.add(task)
    session.commit()
    session.refresh(task)

    return task