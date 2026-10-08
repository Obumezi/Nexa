from sqlalchemy import select
from sqlalchemy.orm import Session

from nexa_api.delivery_service import mark_delivery_delivered
from nexa_api.enums import (
    DeliveryStatus,
    EventType,
    TaskPriority,
    VisitorStatus,
)
from nexa_api.models import (
    Delivery,
    ExpectedVisitor,
    HomeEvent,
    HouseholdTask,
)
from nexa_api.schemas import TaskCreate
from nexa_api.task_service import create_task
from nexa_api.visitor_service import mark_visitor_arrived


def find_matching_visitor(
    session: Session,
    event: HomeEvent,
) -> ExpectedVisitor | None:
    """Find an expected visitor whose window contains the event."""

    statement = (
        select(ExpectedVisitor)
        .where(
            ExpectedVisitor.status == VisitorStatus.EXPECTED,
            ExpectedVisitor.expected_start <= event.occurred_at,
            ExpectedVisitor.expected_end >= event.occurred_at,
        )
        .order_by(ExpectedVisitor.expected_start.asc())
    )

    return session.scalar(statement)


def create_unmatched_visitor_task(
    session: Session,
    event: HomeEvent,
) -> HouseholdTask:
    """Create a confirmation task for an unmatched visitor event."""

    task = create_task(
        session,
        TaskCreate(
            title="Review unexpected visitor",
            description=(
                f"Visitor activity was detected at "
                f"{event.location}, but no expected visitor "
                f"matched the event."
            ),
            priority=TaskPriority.HIGH,
            requires_confirmation=True,
        ),
    )

    event.related_task_id = task.id

    session.add(event)
    session.commit()
    session.refresh(event)

    return task


def process_visitor_event(
    session: Session,
    event: HomeEvent,
) -> ExpectedVisitor | HouseholdTask | None:
    """Process a visitor-detected home event."""

    if event.event_type != EventType.VISITOR_DETECTED:
        return None

    if event.related_visitor_id is not None:
        return session.get(
            ExpectedVisitor,
            event.related_visitor_id,
        )

    if event.related_task_id is not None:
        return session.get(
            HouseholdTask,
            event.related_task_id,
        )

    visitor = find_matching_visitor(
        session,
        event,
    )

    if visitor is None:
        return create_unmatched_visitor_task(
            session,
            event,
        )

    mark_visitor_arrived(
        session,
        visitor,
    )

    event.related_visitor_id = visitor.id

    session.add(event)
    session.commit()
    session.refresh(event)

    return visitor

def find_matching_delivery(
    session: Session,
    event: HomeEvent,
) -> Delivery | None:
    """Find the best expected delivery for a package event."""

    statement = (
        select(Delivery)
        .where(
            Delivery.status == DeliveryStatus.EXPECTED,
        )
        .order_by(
            Delivery.expected_at.asc().nulls_last(),
            Delivery.created_at.asc(),
        )
    )

    return session.scalar(statement)

def process_delivery_event(
    session: Session,
    event: HomeEvent,
) -> Delivery | HouseholdTask | None:
    """Process a package-delivered home event."""

    if event.event_type != EventType.PACKAGE_DELIVERED:
        return None

    if event.related_delivery_id is not None:
        return session.get(
            Delivery,
            event.related_delivery_id,
        )

    if event.related_task_id is not None:
        return session.get(
            HouseholdTask,
            event.related_task_id,
        )

    delivery = find_matching_delivery(
        session,
        event,
    )

    if delivery is None:
        task = create_task(
            session,
            TaskCreate(
                title="Review unexpected delivery",
                description=(
                    f"A package was detected at {event.location}, "
                    f"but Nexa could not match it to an expected delivery."
                ),
                priority=TaskPriority.HIGH,
                requires_confirmation=True,
            ),
        )

        event.related_task_id = task.id

        session.add(event)
        session.commit()
        session.refresh(event)

        return task

    mark_delivery_delivered(
        session,
        delivery,
    )

    event.related_delivery_id = delivery.id

    session.add(event)
    session.commit()
    session.refresh(event)

    return delivery


def process_event(
    session: Session,
    event: HomeEvent,
) -> ExpectedVisitor | Delivery | HouseholdTask | None:
    """Route a home event to the appropriate automation processor."""

    if event.event_type == EventType.VISITOR_DETECTED:
        return process_visitor_event(
            session,
            event,
        )

    if event.event_type == EventType.PACKAGE_DELIVERED:
        return process_delivery_event(
            session,
            event,
        )

    return None