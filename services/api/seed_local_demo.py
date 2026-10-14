from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select

from nexa_api.database import SessionLocal
from nexa_api.enums import (
    DeliveryStatus,
    PresenceStatus,
    TaskPriority,
    TaskStatus,
    VisitorStatus,
)
from nexa_api.models import (
    Delivery,
    ExpectedVisitor,
    HouseholdPresence,
    HouseholdTask,
)
from nexa_api.schemas import (
    DeliveryCreate,
    PresenceCreate,
    TaskCreate,
    VisitorCreate,
)
from nexa_api.delivery_service import create_delivery
from nexa_api.presence_service import create_presence
from nexa_api.task_service import create_task
from nexa_api.visitor_service import create_visitor


def clear_demo_data() -> None:
    """Remove local demo/test records so the simulator starts clean."""

    with SessionLocal() as session:
        session.execute(delete(HouseholdTask))
        session.execute(delete(ExpectedVisitor))
        session.execute(delete(Delivery))
        session.execute(delete(HouseholdPresence))
        session.commit()


def seed_presence() -> None:
    """Create one household presence record."""

    with SessionLocal() as session:
        create_presence(
            session,
            PresenceCreate(
                occupant_name="Obumneme",
                status=PresenceStatus.HOME,
                note="Home and available.",
            ),
        )


def seed_visitor() -> None:
    """Create one expected visitor."""

    now = datetime.now(UTC)

    create_payload = VisitorCreate(
        name="Ada Okafor",
        purpose="Family visit",
        expected_start=now + timedelta(hours=2),
        expected_end=now + timedelta(hours=3),
        notes="Expected through the front entrance.",
    )

    with SessionLocal() as session:
        create_visitor(
            session,
            create_payload,
        )


def seed_delivery() -> None:
    """Create one expected delivery."""

    with SessionLocal() as session:
        create_delivery(
            session,
            DeliveryCreate(
                description="MacBook Pro",
                carrier="DHL",
                tracking_reference="NEXA-LOCAL-DEMO-001",
                expected_at=datetime.now(UTC) + timedelta(hours=4),
                delivery_location="Front door",
                notes="Local Nexa demo delivery.",
            ),
        )


def seed_task() -> None:
    """Create one open household task."""

    with SessionLocal() as session:
        create_task(
            session,
            TaskCreate(
                title="Call the electrician tomorrow",
                description="Arrange repair of the kitchen socket.",
                priority=TaskPriority.MEDIUM,
            ),
        )


def verify_demo_data() -> None:
    """Print the clean local demo state."""

    with SessionLocal() as session:
        presence = list(
            session.scalars(
                select(HouseholdPresence)
            )
        )

        visitors = list(
            session.scalars(
                select(ExpectedVisitor).where(
                    ExpectedVisitor.status == VisitorStatus.EXPECTED
                )
            )
        )

        deliveries = list(
            session.scalars(
                select(Delivery).where(
                    Delivery.status == DeliveryStatus.EXPECTED
                )
            )
        )

        tasks = list(
            session.scalars(
                select(HouseholdTask).where(
                    HouseholdTask.status == TaskStatus.OPEN
                )
            )
        )

        print("\n" + "=" * 60)
        print("LOCAL NEXA DEMO STATE")
        print("=" * 60)

        for record in presence:
            print(
                f"Presence: {record.occupant_name} -> "
                f"{record.status.value}"
            )

        for visitor in visitors:
            print(
                f"Visitor: {visitor.name} -> "
                f"{visitor.status.value}"
            )

        for delivery in deliveries:
            print(
                f"Delivery: {delivery.carrier} "
                f"{delivery.description} -> "
                f"{delivery.status.value}"
            )

        for task in tasks:
            print(
                f"Task: {task.title} -> "
                f"{task.status.value}"
            )

        print("=" * 60)


def main() -> None:
    print("=" * 60)
    print("RESETTING LOCAL NEXA DEMO")
    print("=" * 60)

    print("\nClearing local test/demo data...")
    clear_demo_data()

    print("Creating household presence...")
    seed_presence()

    print("Creating expected visitor...")
    seed_visitor()

    print("Creating pending delivery...")
    seed_delivery()

    print("Creating open task...")
    seed_task()

    verify_demo_data()

    print("\nLOCAL DEMO SEEDED SUCCESSFULLY")


if __name__ == "__main__":
    main()