from datetime import datetime
from enum import StrEnum
from typing import Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from nexa_api.enums import (
    DeliveryStatus,
    EventSource,
    EventType,
    PresenceStatus,
    TaskPriority,
    TaskStatus,
    VisitorStatus,
)


class TaskCreate(BaseModel):
    """Data accepted when creating a household task."""

    title: str = Field(
        min_length=1,
        max_length=150,
    )
    description: str | None = Field(
        default=None,
        max_length=2000,
    )
    priority: TaskPriority = TaskPriority.MEDIUM
    requires_confirmation: bool = False
    due_at: datetime | None = None

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        """Remove surrounding spaces and reject blank titles."""

        cleaned_value = value.strip()

        if not cleaned_value:
            raise ValueError("title must not be blank")

        return cleaned_value


class TaskUpdate(BaseModel):
    """Data accepted when updating a household task."""

    title: str | None = Field(
        default=None,
        min_length=1,
        max_length=150,
    )
    description: str | None = Field(
        default=None,
        max_length=2000,
    )
    priority: TaskPriority | None = None
    requires_confirmation: bool | None = None
    due_at: datetime | None = None

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str | None) -> str | None:
        """Reject blank titles when a new title is supplied."""

        if value is None:
            return None

        cleaned_value = value.strip()

        if not cleaned_value:
            raise ValueError("title must not be blank")

        return cleaned_value


class TaskRead(BaseModel):
    """Household task data returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    description: str | None
    status: TaskStatus
    priority: TaskPriority
    requires_confirmation: bool
    due_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class VisitorCreate(BaseModel):
    """Data accepted when scheduling an expected visitor."""

    name: str = Field(
        min_length=1,
        max_length=150,
    )
    purpose: str = Field(
        min_length=1,
        max_length=255,
    )
    expected_start: datetime
    expected_end: datetime
    related_task_id: str | None = None
    notes: str | None = Field(
        default=None,
        max_length=2000,
    )

    @field_validator("name", "purpose")
    @classmethod
    def clean_required_text(cls, value: str) -> str:
        """Clean and validate required visitor text."""

        cleaned_value = value.strip()

        if not cleaned_value:
            raise ValueError("value must not be blank")

        return cleaned_value

    @model_validator(mode="after")
    def validate_time_window(self) -> Self:
        """Ensure the visit ends after it begins."""

        if self.expected_end <= self.expected_start:
            raise ValueError(
                "expected_end must be later than expected_start"
            )

        return self


class VisitorRead(BaseModel):
    """Expected visitor information returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    purpose: str
    expected_start: datetime
    expected_end: datetime
    status: VisitorStatus
    related_task_id: str | None
    arrived_at: datetime | None
    departed_at: datetime | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class DeliveryCreate(BaseModel):
    """Data accepted when registering an expected delivery."""

    description: str = Field(
        min_length=1,
        max_length=255,
    )
    carrier: str | None = Field(
        default=None,
        max_length=100,
    )
    tracking_reference: str | None = Field(
        default=None,
        max_length=150,
    )
    expected_at: datetime | None = None
    delivery_location: str | None = Field(
        default=None,
        max_length=100,
    )
    notes: str | None = Field(
        default=None,
        max_length=2000,
    )

    @field_validator("description")
    @classmethod
    def clean_description(cls, value: str) -> str:
        """Clean and validate the required delivery description."""

        cleaned_value = value.strip()

        if not cleaned_value:
            raise ValueError("description must not be blank")

        return cleaned_value

    @field_validator(
        "carrier",
        "tracking_reference",
        "delivery_location",
        "notes",
    )
    @classmethod
    def clean_optional_text(
        cls,
        value: str | None,
    ) -> str | None:
        """Clean optional delivery text."""

        if value is None:
            return None

        cleaned_value = value.strip()

        return cleaned_value or None

class DeliveryRead(BaseModel):
    """Delivery information returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    description: str
    carrier: str | None
    tracking_reference: str | None
    status: DeliveryStatus
    expected_at: datetime | None
    delivered_at: datetime | None
    collected_at: datetime | None
    delivery_location: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class PresenceCreate(BaseModel):
    """Data accepted when creating a household presence record."""

    occupant_name: str = Field(
        min_length=1,
        max_length=150,
    )
    status: PresenceStatus = PresenceStatus.HOME
    note: str | None = Field(
        default=None,
        max_length=2000,
    )

    @field_validator("occupant_name")
    @classmethod
    def clean_occupant_name(cls, value: str) -> str:
        """Clean and validate the household occupant name."""

        cleaned_value = value.strip()

        if not cleaned_value:
            raise ValueError("occupant_name must not be blank")

        return cleaned_value

    @field_validator("note")
    @classmethod
    def clean_presence_note(
        cls,
        value: str | None,
    ) -> str | None:
        """Clean optional presence notes."""

        if value is None:
            return None

        cleaned_value = value.strip()

        return cleaned_value or None


class PresenceUpdate(BaseModel):
    """Data accepted when updating household presence."""

    status: PresenceStatus
    note: str | None = Field(
        default=None,
        max_length=2000,
    )

    @field_validator("note")
    @classmethod
    def clean_presence_note(
        cls,
        value: str | None,
    ) -> str | None:
        """Clean optional presence notes."""

        if value is None:
            return None

        cleaned_value = value.strip()

        return cleaned_value or None


class PresenceRead(BaseModel):
    """Household presence information returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    occupant_name: str
    status: PresenceStatus
    since: datetime
    note: str | None
    created_at: datetime
    updated_at: datetime


class EventCreate(BaseModel):
    """Data accepted when recording a home event."""

    event_type: EventType
    source: EventSource = EventSource.RING_SIMULATOR
    location: str = Field(
        default="front_door",
        min_length=1,
        max_length=100,
    )
    summary: str = Field(
        min_length=1,
        max_length=255,
    )
    details: str | None = Field(
        default=None,
        max_length=2000,
    )
    confidence: int | None = Field(
        default=None,
        ge=0,
        le=100,
    )
    is_simulated: bool = True
    occurred_at: datetime | None = None
    related_visitor_id: str | None = None
    related_delivery_id: str | None = None
    related_task_id: str | None = None

    @field_validator("location", "summary")
    @classmethod
    def clean_required_event_text(cls, value: str) -> str:
        """Clean and validate required event text."""

        cleaned_value = value.strip()

        if not cleaned_value:
            raise ValueError("value must not be blank")

        return cleaned_value

    @field_validator("details")
    @classmethod
    def clean_event_details(
        cls,
        value: str | None,
    ) -> str | None:
        """Clean optional event details."""

        if value is None:
            return None

        cleaned_value = value.strip()

        return cleaned_value or None


class EventRead(BaseModel):
    """Home event information returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    event_type: EventType
    source: EventSource
    location: str
    summary: str
    details: str | None
    confidence: int | None
    is_simulated: bool
    occurred_at: datetime
    related_visitor_id: str | None
    related_delivery_id: str | None
    related_task_id: str | None
    created_at: datetime

class AgentIntent(StrEnum):
    """Supported intents for the Nexa agent."""

    GET_EXPECTED_VISITORS = "get_expected_visitors"
    GET_PENDING_DELIVERIES = "get_pending_deliveries"
    GET_HOUSEHOLD_PRESENCE = "get_household_presence"
    GET_OPEN_TASKS = "get_open_tasks"
    CREATE_TASK = "create_task"
    COMPLETE_TASK = "complete_task"
    CANCEL_VISITOR = "cancel_visitor"
    MARK_VISITOR_ARRIVED = "mark_visitor_arrived"
    MARK_VISITOR_DEPARTED = "mark_visitor_departed"
    MARK_DELIVERY_COLLECTED = "mark_delivery_collected"
    MARK_DELIVERY_DELIVERED = "mark_delivery_delivered"
    UPDATE_PRESENCE = "update_presence"
    UNKNOWN = "unknown"

class AgentRequest(BaseModel):
    """Natural-language request sent to the Nexa agent."""

    message: str
    confirm: bool = False
    session_id: str | None = None
    speaker_name: str | None = None
    
    @field_validator("message")
    @classmethod
    def clean_message(cls, value: str) -> str:
        """Clean and validate an agent request."""

        cleaned_value = value.strip()

        if not cleaned_value:
            raise ValueError("message must not be blank")

        return cleaned_value


class AgentDecision(BaseModel):
    """Structured decision produced by the Nexa agent."""

    intent: AgentIntent
    confidence: float = Field(
        ge=0,
        le=1,
    )
    task_title: str | None = None
    task_description: str | None = None
    target_task_title: str | None = None
    target_visitor_name: str | None = None
    target_delivery_description: str | None = None
    target_occupant_name: str | None = None
    target_presence_status: str | None = None

class AgentResponse(BaseModel):
    """Response returned by the Nexa agent."""

    intent: AgentIntent
    message: str
    data: list[dict[str, object]] = Field(
        default_factory=list,
    )
    requires_confirmation: bool = False
    action_executed: bool = False
    proposed_action: dict[str, object] | None = None
    session_id: str | None = None