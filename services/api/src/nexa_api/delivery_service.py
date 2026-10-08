from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from nexa_api.enums import DeliveryStatus
from nexa_api.models import Delivery
from nexa_api.schemas import DeliveryCreate


def create_delivery(
    session: Session,
    payload: DeliveryCreate,
) -> Delivery:
    """Create and save an expected delivery."""

    delivery = Delivery(**payload.model_dump())

    session.add(delivery)
    session.commit()
    session.refresh(delivery)

    return delivery


def get_delivery(
    session: Session,
    delivery_id: str,
) -> Delivery | None:
    """Return one delivery or None when it does not exist."""

    return session.get(Delivery, delivery_id)


def list_deliveries(
    session: Session,
    status: DeliveryStatus | None = None,
) -> list[Delivery]:
    """Return deliveries, optionally filtered by status."""

    statement = select(Delivery).order_by(
        Delivery.created_at.desc()
    )

    if status is not None:
        statement = statement.where(
            Delivery.status == status
        )

    return list(session.scalars(statement))


def mark_delivery_delivered(
    session: Session,
    delivery: Delivery,
) -> Delivery:
    """Mark an expected delivery as delivered."""

    if delivery.status == DeliveryStatus.DELIVERED:
        return delivery

    delivery.status = DeliveryStatus.DELIVERED
    delivery.delivered_at = datetime.now(UTC)

    session.add(delivery)
    session.commit()
    session.refresh(delivery)

    return delivery


def mark_delivery_collected(
    session: Session,
    delivery: Delivery,
) -> Delivery:
    """Mark a delivered package as collected."""

    if delivery.status == DeliveryStatus.COLLECTED:
        return delivery

    delivery.status = DeliveryStatus.COLLECTED

    if delivery.delivered_at is None:
        delivery.delivered_at = datetime.now(UTC)

    delivery.collected_at = datetime.now(UTC)

    session.add(delivery)
    session.commit()
    session.refresh(delivery)

    return delivery