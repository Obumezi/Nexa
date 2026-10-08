from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from nexa_api.enums import (
    TaskPriority,
    TaskStatus,
    VisitorStatus,
)
from nexa_api.schemas import (
    AgentRequest,
    TaskCreate,
    TaskRead,
    TaskUpdate,
    VisitorCreate,
    VisitorRead,
)


def test_task_create_uses_safe_defaults() -> None:
    """New tasks should use medium priority and no confirmation."""

    payload = TaskCreate(title="Check front door")

    assert payload.title == "Check front door"
    assert payload.priority == TaskPriority.MEDIUM
    assert payload.requires_confirmation is False
    assert payload.due_at is None


def test_task_create_cleans_title() -> None:
    """Task titles should have surrounding whitespace removed."""

    payload = TaskCreate(title="  Repair kitchen socket  ")

    assert payload.title == "Repair kitchen socket"


def test_task_create_rejects_blank_title() -> None:
    """Whitespace-only titles should be rejected."""

    with pytest.raises(ValidationError):
        TaskCreate(title="   ")


def test_task_update_rejects_blank_title() -> None:
    """Updates should not replace a task title with whitespace."""

    with pytest.raises(ValidationError):
        TaskUpdate(title="   ")


def test_task_read_serializes_api_response() -> None:
    """Stored task information should validate as an API response."""

    timestamp = datetime.now(UTC)

    response = TaskRead.model_validate(
        {
            "id": "task-001",
            "title": "Repair kitchen socket",
            "description": None,
            "status": TaskStatus.OPEN,
            "priority": TaskPriority.HIGH,
            "requires_confirmation": True,
            "due_at": None,
            "completed_at": None,
            "created_at": timestamp,
            "updated_at": timestamp,
        }
    )

    assert response.id == "task-001"
    assert response.status == TaskStatus.OPEN
    assert response.priority == TaskPriority.HIGH

def test_visitor_create_accepts_valid_window() -> None:
    """A valid visitor schedule should pass validation."""

    start_time = datetime.now(UTC)
    end_time = start_time + timedelta(hours=2)

    payload = VisitorCreate(
        name="Electrician",
        purpose="Repair kitchen socket",
        expected_start=start_time,
        expected_end=end_time,
        related_task_id="task-001",
    )

    assert payload.name == "Electrician"
    assert payload.purpose == "Repair kitchen socket"
    assert payload.related_task_id == "task-001"


def test_visitor_create_cleans_text() -> None:
    """Visitor names and purposes should be cleaned."""

    start_time = datetime.now(UTC)
    end_time = start_time + timedelta(hours=1)

    payload = VisitorCreate(
        name="  Electrician  ",
        purpose="  Repair socket  ",
        expected_start=start_time,
        expected_end=end_time,
    )

    assert payload.name == "Electrician"
    assert payload.purpose == "Repair socket"


def test_visitor_create_rejects_invalid_window() -> None:
    """A visit cannot end before or when it starts."""

    start_time = datetime.now(UTC)

    with pytest.raises(ValidationError):
        VisitorCreate(
            name="Electrician",
            purpose="Repair socket",
            expected_start=start_time,
            expected_end=start_time,
        )


def test_visitor_read_serializes_api_response() -> None:
    """Stored visitor information should validate for API output."""

    start_time = datetime.now(UTC)
    end_time = start_time + timedelta(hours=2)

    response = VisitorRead.model_validate(
        {
            "id": "visitor-001",
            "name": "Electrician",
            "purpose": "Repair kitchen socket",
            "expected_start": start_time,
            "expected_end": end_time,
            "status": VisitorStatus.EXPECTED,
            "related_task_id": "task-001",
            "arrived_at": None,
            "departed_at": None,
            "notes": None,
            "created_at": start_time,
            "updated_at": start_time,
        }
    )

    assert response.id == "visitor-001"
    assert response.status == VisitorStatus.EXPECTED

def test_agent_request_accepts_speaker_identity() -> None:
    request = AgentRequest(
        message="I'm home.",
        speaker_name="Obumneme",
    )

    assert request.message == "I'm home."
    assert request.speaker_name == "Obumneme"


def test_agent_request_speaker_identity_is_optional() -> None:
    request = AgentRequest(
        message="Who is home?",
    )

    assert request.speaker_name is None