from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import Mapped, mapped_column

from nexa_api.database import Base
from nexa_api.enums import (
    DeliveryStatus,
    EventSource,
    EventType,
    PresenceStatus,
    TaskPriority,
    TaskStatus,
    VisitorStatus,
)


def new_id() -> str:
    """Generate a UUID string for a Nexa record."""

    return str(uuid4())


def utc_now() -> datetime:
    """Return the current timezone-aware UTC time."""

    return datetime.now(UTC)


class HouseholdTask(Base):
    """A task that needs to be handled around the home."""

    __tablename__ = "household_tasks"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=new_id,
    )
    title: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    status: Mapped[TaskStatus] = mapped_column(
        SqlEnum(
            TaskStatus,
            values_callable=lambda enum_class: [
                member.value for member in enum_class
            ],
            native_enum=False,
        ),
        default=TaskStatus.OPEN,
        nullable=False,
        index=True,
    )
    priority: Mapped[TaskPriority] = mapped_column(
        SqlEnum(
            TaskPriority,
            values_callable=lambda enum_class: [
                member.value for member in enum_class
            ],
            native_enum=False,
        ),
        default=TaskPriority.MEDIUM,
        nullable=False,
        index=True,
    )
    requires_confirmation: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    due_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )



class ExpectedVisitor(Base):
    """A visitor expected at the home during a defined time window."""

    __tablename__ = "expected_visitors"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=new_id,
    )
    name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )
    purpose: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    expected_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    expected_end: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    status: Mapped[VisitorStatus] = mapped_column(
        SqlEnum(
            VisitorStatus,
            values_callable=lambda enum_class: [
                member.value for member in enum_class
            ],
            native_enum=False,
        ),
        default=VisitorStatus.EXPECTED,
        nullable=False,
        index=True,
    )
    related_task_id: Mapped[str | None] = mapped_column(
        ForeignKey(
            "household_tasks.id",
            ondelete="SET NULL",
        ),
        nullable=True,
    )
    arrived_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    departed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )


class HomeEvent(Base):
        """An event detected or recorded around the home."""

        __tablename__ = "home_events"

        __table_args__ = (
        CheckConstraint(
            "confidence IS NULL OR "
            "(confidence >= 0 AND confidence <= 100)",
            name="ck_home_events_confidence",
        ),
    )

        id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=new_id,
    )
        event_type: Mapped[EventType] = mapped_column(
        SqlEnum(
            EventType,
            values_callable=lambda enum_class: [
                member.value for member in enum_class
            ],
            native_enum=False,
        ),
        nullable=False,
        index=True,
    )
        source: Mapped[EventSource] = mapped_column(
        SqlEnum(
            EventSource,
            values_callable=lambda enum_class: [
                member.value for member in enum_class
            ],
            native_enum=False,
        ),
        default=EventSource.RING_SIMULATOR,
        nullable=False,
        index=True,
    )
        location: Mapped[str] = mapped_column(
        String(100),
        default="front_door",
        nullable=False,
    )
        summary: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
        details: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
        confidence: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
        is_simulated: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
        occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
        index=True,
    )
        related_visitor_id: Mapped[str | None] = mapped_column(
        ForeignKey(
            "expected_visitors.id",
            ondelete="SET NULL",
        ),
        nullable=True,

    )
        related_delivery_id: Mapped[str | None] = mapped_column(
        ForeignKey(
            "deliveries.id",
            ondelete="SET NULL",
        ),
        nullable=True,
    )
        related_task_id: Mapped[str | None] = mapped_column(
        ForeignKey(
            "household_tasks.id",
            ondelete="SET NULL",
        ),
        nullable=True,
    )
        created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

class Delivery(Base):
    """A package expected at or delivered to the home."""

    __tablename__ = "deliveries"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=new_id,
    )
    description: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    carrier: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    tracking_reference: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
        index=True,
    )
    status: Mapped[DeliveryStatus] = mapped_column(
        SqlEnum(
            DeliveryStatus,
            values_callable=lambda enum_class: [
                member.value for member in enum_class
            ],
            native_enum=False,
        ),
        default=DeliveryStatus.EXPECTED,
        nullable=False,
        index=True,
    )
    expected_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    delivered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    collected_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    delivery_location: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )


class HouseholdPresence(Base):
    """The current presence state of a household occupant."""

    __tablename__ = "household_presence"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=new_id,
    )
    occupant_name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
        unique=True,
        index=True,
    )
    status: Mapped[PresenceStatus] = mapped_column(
        SqlEnum(
            PresenceStatus,
            values_callable=lambda enum_class: [
                member.value for member in enum_class
            ],
            native_enum=False,
        ),
        default=PresenceStatus.HOME,
        nullable=False,
        index=True,
    )
    since: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    note: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

class ConversationSession(Base):
    """A persistent Nexa conversation."""

    __tablename__ = "conversation_sessions"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )


class ConversationMessage(Base):
    """One user or assistant message in a conversation."""

    __tablename__ = "conversation_messages"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    session_id: Mapped[str] = mapped_column(
        ForeignKey(
            "conversation_sessions.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(UTC),
        nullable=False,
        index=True,
    )