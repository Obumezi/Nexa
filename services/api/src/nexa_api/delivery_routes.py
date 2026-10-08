from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from nexa_api.database import get_db
from nexa_api.delivery_service import (
    create_delivery,
    get_delivery,
    list_deliveries,
    mark_delivery_collected,
    mark_delivery_delivered,
)
from nexa_api.enums import DeliveryStatus
from nexa_api.models import Delivery
from nexa_api.schemas import DeliveryCreate, DeliveryRead

router = APIRouter(
    prefix="/api/v1/deliveries",
    tags=["deliveries"],
)

DatabaseSession = Annotated[Session, Depends(get_db)]


def require_delivery(
    session: Session,
    delivery_id: str,
) -> Delivery:
    """Return a delivery or raise an API 404 response."""

    delivery = get_delivery(session, delivery_id)

    if delivery is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Delivery not found",
        )

    return delivery


@router.post(
    "",
    response_model=DeliveryRead,
    status_code=status.HTTP_201_CREATED,
)
def create_delivery_endpoint(
    payload: DeliveryCreate,
    session: DatabaseSession,
) -> Delivery:
    """Create an expected delivery."""

    return create_delivery(session, payload)


@router.get(
    "",
    response_model=list[DeliveryRead],
)
def list_deliveries_endpoint(
    session: DatabaseSession,
    status_filter: Annotated[
        DeliveryStatus | None,
        Query(alias="status"),
    ] = None,
) -> list[Delivery]:
    """Return deliveries, optionally filtered by status."""

    return list_deliveries(
        session,
        status=status_filter,
    )


@router.get(
    "/{delivery_id}",
    response_model=DeliveryRead,
)
def get_delivery_endpoint(
    delivery_id: str,
    session: DatabaseSession,
) -> Delivery:
    """Return one delivery."""

    return require_delivery(session, delivery_id)


@router.post(
    "/{delivery_id}/deliver",
    response_model=DeliveryRead,
)
def mark_delivery_delivered_endpoint(
    delivery_id: str,
    session: DatabaseSession,
) -> Delivery:
    """Mark an expected delivery as delivered."""

    delivery = require_delivery(
        session,
        delivery_id,
    )

    return mark_delivery_delivered(
        session,
        delivery,
    )


@router.post(
    "/{delivery_id}/collect",
    response_model=DeliveryRead,
)
def mark_delivery_collected_endpoint(
    delivery_id: str,
    session: DatabaseSession,
) -> Delivery:
    """Mark a delivered package as collected."""

    delivery = require_delivery(
        session,
        delivery_id,
    )

    return mark_delivery_collected(
        session,
        delivery,
    )