from enum import StrEnum


class EventType(StrEnum):
    """Types of events Nexa can record."""

    VISITOR_DETECTED = "visitor_detected"
    PACKAGE_DELIVERED = "package_delivered"
    MOTION_DETECTED = "motion_detected"
    DOORBELL_PRESSED = "doorbell_pressed"
    DOOR_OPENED = "door_opened"
    SYSTEM = "system"


class EventSource(StrEnum):
    """Sources that can produce home events."""

    RING_SIMULATOR = "ring_simulator"
    MANUAL = "manual"
    SYSTEM = "system"


class TaskStatus(StrEnum):
    """Lifecycle states for household tasks."""

    OPEN = "open"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TaskPriority(StrEnum):
    """Priority levels for household tasks."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class VisitorStatus(StrEnum):
    """Lifecycle states for an expected visitor."""

    EXPECTED = "expected"
    ARRIVED = "arrived"
    DEPARTED = "departed"
    MISSED = "missed"
    CANCELLED = "cancelled"


class DeliveryStatus(StrEnum):
    """Lifecycle states for deliveries."""

    EXPECTED = "expected"
    DELIVERED = "delivered"
    COLLECTED = "collected"


class PresenceStatus(StrEnum):
    """Supported household presence states."""

    HOME = "home"
    AWAY = "away"
    SLEEPING = "sleeping"