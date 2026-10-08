from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from nexa_api.enums import VisitorStatus
from nexa_api.models import ExpectedVisitor
from nexa_api.schemas import VisitorCreate


def create_visitor(
    session: Session,
    payload: VisitorCreate,
) -> ExpectedVisitor:
    """Create and save an expected visitor."""

    visitor = ExpectedVisitor(**payload.model_dump())

    session.add(visitor)
    session.commit()
    session.refresh(visitor)

    return visitor


def get_visitor(
    session: Session,
    visitor_id: str,
) -> ExpectedVisitor | None:
    """Return one expected visitor or None when it does not exist."""

    return session.get(ExpectedVisitor, visitor_id)


def list_visitors(
    session: Session,
    status: VisitorStatus | None = None,
) -> list[ExpectedVisitor]:
    """Return expected visitors, optionally filtered by status."""

    statement = select(ExpectedVisitor).order_by(
        ExpectedVisitor.expected_start.asc()
    )

    if status is not None:
        statement = statement.where(
            ExpectedVisitor.status == status
        )

    return list(session.scalars(statement))


def mark_visitor_arrived(
    session: Session,
    visitor: ExpectedVisitor,
) -> ExpectedVisitor:
    """Mark an expected visitor as arrived."""

    if visitor.status == VisitorStatus.ARRIVED:
        return visitor

    visitor.status = VisitorStatus.ARRIVED
    visitor.arrived_at = datetime.now(UTC)

    session.add(visitor)
    session.commit()
    session.refresh(visitor)

    return visitor


def mark_visitor_departed(
    session: Session,
    visitor: ExpectedVisitor,
) -> ExpectedVisitor:
    """Mark an arrived visitor as departed."""

    if visitor.status == VisitorStatus.DEPARTED:
        return visitor

    visitor.status = VisitorStatus.DEPARTED
    visitor.departed_at = datetime.now(UTC)

    session.add(visitor)
    session.commit()
    session.refresh(visitor)

    return visitor


def cancel_visitor(
    session: Session,
    visitor: ExpectedVisitor,
) -> ExpectedVisitor:
    """Cancel an expected visitor."""

    if visitor.status == VisitorStatus.CANCELLED:
        return visitor

    visitor.status = VisitorStatus.CANCELLED

    session.add(visitor)
    session.commit()
    session.refresh(visitor)

    return visitor