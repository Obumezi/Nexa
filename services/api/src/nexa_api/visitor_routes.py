from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from nexa_api.database import get_db
from nexa_api.enums import VisitorStatus
from nexa_api.models import ExpectedVisitor
from nexa_api.schemas import VisitorCreate, VisitorRead
from nexa_api.visitor_service import (
    cancel_visitor,
    create_visitor,
    get_visitor,
    list_visitors,
    mark_visitor_arrived,
    mark_visitor_departed,
)

router = APIRouter(
    prefix="/api/v1/visitors",
    tags=["visitors"],
)

DatabaseSession = Annotated[Session, Depends(get_db)]


def require_visitor(
    session: Session,
    visitor_id: str,
) -> ExpectedVisitor:
    """Return a visitor or raise an API 404 response."""

    visitor = get_visitor(session, visitor_id)

    if visitor is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Visitor not found",
        )

    return visitor


@router.post(
    "",
    response_model=VisitorRead,
    status_code=status.HTTP_201_CREATED,
)
def create_visitor_endpoint(
    payload: VisitorCreate,
    session: DatabaseSession,
) -> ExpectedVisitor:
    """Create an expected visitor."""

    return create_visitor(session, payload)


@router.get(
    "",
    response_model=list[VisitorRead],
)
def list_visitors_endpoint(
    session: DatabaseSession,
    status_filter: Annotated[
        VisitorStatus | None,
        Query(alias="status"),
    ] = None,
) -> list[ExpectedVisitor]:
    """Return expected visitors, optionally filtered by status."""

    return list_visitors(session, status=status_filter)


@router.get(
    "/{visitor_id}",
    response_model=VisitorRead,
)
def get_visitor_endpoint(
    visitor_id: str,
    session: DatabaseSession,
) -> ExpectedVisitor:
    """Return one expected visitor."""

    return require_visitor(session, visitor_id)


@router.post(
    "/{visitor_id}/arrive",
    response_model=VisitorRead,
)
def mark_visitor_arrived_endpoint(
    visitor_id: str,
    session: DatabaseSession,
) -> ExpectedVisitor:
    """Mark an expected visitor as arrived."""

    visitor = require_visitor(session, visitor_id)

    return mark_visitor_arrived(session, visitor)


@router.post(
    "/{visitor_id}/depart",
    response_model=VisitorRead,
)
def mark_visitor_departed_endpoint(
    visitor_id: str,
    session: DatabaseSession,
) -> ExpectedVisitor:
    """Mark a visitor as departed."""

    visitor = require_visitor(session, visitor_id)

    return mark_visitor_departed(session, visitor)


@router.post(
    "/{visitor_id}/cancel",
    response_model=VisitorRead,
)
def cancel_visitor_endpoint(
    visitor_id: str,
    session: DatabaseSession,
) -> ExpectedVisitor:
    """Cancel an expected visitor."""

    visitor = require_visitor(session, visitor_id)

    return cancel_visitor(session, visitor)