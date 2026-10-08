from nexa_api.enums import (
    DeliveryStatus,
    EventSource,
    EventType,
    PresenceStatus,
    TaskPriority,
    TaskStatus,
    VisitorStatus,
)


def test_event_enum_values() -> None:
    """Home events should use stable machine-readable values."""

    assert EventType.VISITOR_DETECTED == "visitor_detected"
    assert EventType.PACKAGE_DELIVERED == "package_delivered"
    assert EventSource.RING_SIMULATOR == "ring_simulator"


def test_household_workflow_statuses() -> None:
    """Household workflow states should remain consistent."""

    assert TaskStatus.OPEN == "open"
    assert TaskStatus.COMPLETED == "completed"
    assert VisitorStatus.EXPECTED == "expected"
    assert DeliveryStatus.DELIVERED == "delivered"


def test_priority_and_presence_values() -> None:
    """Task priority and household presence should serialize as strings."""

    assert TaskPriority.CRITICAL == "critical"
    assert PresenceStatus.HOME == "home"
    assert str(PresenceStatus.AWAY) == "away"