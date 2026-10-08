from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from nexa_api.database import get_db
from nexa_api.enums import PresenceStatus
from nexa_api.models import HouseholdPresence
from nexa_api.presence_service import (
    create_presence,
    get_presence,
    list_presence,
    update_presence,
)
from nexa_api.schemas import (
    PresenceCreate,
    PresenceRead,
    PresenceUpdate,
)

router = APIRouter(
    prefix="/api/v1/presence",
    tags=["presence"],
)

DatabaseSession = Annotated[Session, Depends(get_db)]


def require_presence(
    session: Session,
    presence_id: str,
) -> HouseholdPresence:
    """Return a presence record or raise an API 404 response."""

    presence = get_presence(session, presence_id)

    if presence is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Presence record not found",
        )

    return presence


@router.post(
    "",
    response_model=PresenceRead,
    status_code=status.HTTP_201_CREATED,
)
def create_presence_endpoint(
    payload: PresenceCreate,
    session: DatabaseSession,
) -> HouseholdPresence:
    """Create a household presence record."""

    return create_presence(session, payload)


@router.get(
    "",
    response_model=list[PresenceRead],
)
def list_presence_endpoint(
    session: DatabaseSession,
    status_filter: Annotated[
        PresenceStatus | None,
        Query(alias="status"),
    ] = None,
) -> list[HouseholdPresence]:
    """Return presence records, optionally filtered by status."""

    return list_presence(
        session,
        status=status_filter,
    )


@router.get(
    "/{presence_id}",
    response_model=PresenceRead,
)
def get_presence_endpoint(
    presence_id: str,
    session: DatabaseSession,
) -> HouseholdPresence:
    """Return one household presence record."""

    return require_presence(
        session,
        presence_id,
    )


@router.patch(
    "/{presence_id}",
    response_model=PresenceRead,
)
def update_presence_endpoint(
    presence_id: str,
    payload: PresenceUpdate,
    session: DatabaseSession,
) -> HouseholdPresence:
    """Update an occupant's presence status."""

    presence = require_presence(
        session,
        presence_id,
    )

    return update_presence(
        session,
        presence,
        payload,
    )