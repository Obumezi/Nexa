from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from nexa_api.automation_service import process_event
from nexa_api.database import get_db
from nexa_api.enums import EventSource, EventType
from nexa_api.event_service import (
    create_event,
    get_event,
    list_events,
)
from nexa_api.models import HomeEvent
from nexa_api.schemas import EventCreate, EventRead

router = APIRouter(
    prefix="/api/v1/events",
    tags=["events"],
)

DatabaseSession = Annotated[Session, Depends(get_db)]


def require_event(
    session: Session,
    event_id: str,
) -> HomeEvent:
    """Return an event or raise an API 404 response."""

    event = get_event(session, event_id)

    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )

    return event


@router.post(
    "",
    response_model=EventRead,
    status_code=status.HTTP_201_CREATED,
)
def create_event_endpoint(
    payload: EventCreate,
    session: DatabaseSession,
) -> HomeEvent:
    """Record a home event and process supported automation."""

    event = create_event(session, payload)

    process_event(
        session,
        event,
    )

    session.refresh(event)

    return event

@router.get(
    "",
    response_model=list[EventRead],
)
def list_events_endpoint(
    session: DatabaseSession,
    event_type_filter: Annotated[
        EventType | None,
        Query(alias="event_type"),
    ] = None,
    source_filter: Annotated[
        EventSource | None,
        Query(alias="source"),
    ] = None,
) -> list[HomeEvent]:
    """Return home events, optionally filtered by type and source."""

    return list_events(
        session,
        event_type=event_type_filter,
        source=source_filter,
    )


@router.get(
    "/{event_id}",
    response_model=EventRead,
)
def get_event_endpoint(
    event_id: str,
    session: DatabaseSession,
) -> HomeEvent:
    """Return one home event."""

    return require_event(
        session,
        event_id,
    )