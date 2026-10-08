from sqlalchemy import select
from sqlalchemy.orm import Session

from nexa_api.enums import EventSource, EventType
from nexa_api.models import HomeEvent
from nexa_api.schemas import EventCreate


def create_event(
    session: Session,
    payload: EventCreate,
) -> HomeEvent:
    """Create and save a home event."""

    event_data = payload.model_dump(exclude_none=True)
    event = HomeEvent(**event_data)

    session.add(event)
    session.commit()
    session.refresh(event)

    return event


def get_event(
    session: Session,
    event_id: str,
) -> HomeEvent | None:
    """Return one home event or None when it does not exist."""

    return session.get(HomeEvent, event_id)


def list_events(
    session: Session,
    event_type: EventType | None = None,
    source: EventSource | None = None,
) -> list[HomeEvent]:
    """Return home events, optionally filtered by type and source."""

    statement = select(HomeEvent).order_by(
        HomeEvent.occurred_at.desc()
    )

    if event_type is not None:
        statement = statement.where(
            HomeEvent.event_type == event_type
        )

    if source is not None:
        statement = statement.where(
            HomeEvent.source == source
        )

    return list(session.scalars(statement))