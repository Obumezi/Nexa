from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from nexa_api.enums import PresenceStatus
from nexa_api.models import HouseholdPresence
from nexa_api.schemas import PresenceCreate, PresenceUpdate


def create_presence(
    session: Session,
    payload: PresenceCreate,
) -> HouseholdPresence:
    """Create and save a household presence record."""

    presence = HouseholdPresence(**payload.model_dump())

    session.add(presence)
    session.commit()
    session.refresh(presence)

    return presence


def get_presence(
    session: Session,
    presence_id: str,
) -> HouseholdPresence | None:
    """Return one presence record or None when it does not exist."""

    return session.get(HouseholdPresence, presence_id)


def list_presence(
    session: Session,
    status: PresenceStatus | None = None,
) -> list[HouseholdPresence]:
    """Return household presence records, optionally filtered by status."""

    statement = select(HouseholdPresence).order_by(
        HouseholdPresence.occupant_name.asc()
    )

    if status is not None:
        statement = statement.where(
            HouseholdPresence.status == status
        )

    return list(session.scalars(statement))


def update_presence(
    session: Session,
    presence: HouseholdPresence,
    payload: PresenceUpdate,
) -> HouseholdPresence:
    """Update an occupant's current presence state."""

    status_changed = presence.status != payload.status

    presence.status = payload.status
    presence.note = payload.note

    if status_changed:
        presence.since = datetime.now(UTC)

    session.add(presence)
    session.commit()
    session.refresh(presence)

    return presence