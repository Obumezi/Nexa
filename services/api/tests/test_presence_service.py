from collections.abc import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from nexa_api.database import Base
from nexa_api.enums import PresenceStatus
from nexa_api.presence_service import (
    create_presence,
    get_presence,
    list_presence,
    update_presence,
)
from nexa_api.schemas import PresenceCreate, PresenceUpdate


@pytest.fixture
def session() -> Generator[Session, None, None]:
    """Provide an isolated in-memory database session."""

    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    Base.metadata.create_all(engine)

    session_factory = sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )

    with session_factory() as database_session:
        yield database_session

    Base.metadata.drop_all(engine)
    engine.dispose()


def test_create_and_get_presence(session: Session) -> None:
    payload = PresenceCreate(
        occupant_name="Obumneme",
        status=PresenceStatus.HOME,
        note="Working from home",
    )

    created_presence = create_presence(session, payload)
    stored_presence = get_presence(
        session,
        created_presence.id,
    )

    assert stored_presence is not None
    assert stored_presence.id == created_presence.id
    assert stored_presence.occupant_name == "Obumneme"
    assert stored_presence.status == PresenceStatus.HOME


def test_list_presence_can_filter_by_status(
    session: Session,
) -> None:
    create_presence(
        session,
        PresenceCreate(
            occupant_name="Ada",
            status=PresenceStatus.HOME,
        ),
    )

    create_presence(
        session,
        PresenceCreate(
            occupant_name="Chidi",
            status=PresenceStatus.AWAY,
        ),
    )

    home_occupants = list_presence(
        session,
        status=PresenceStatus.HOME,
    )

    assert len(home_occupants) == 1
    assert home_occupants[0].occupant_name == "Ada"


def test_update_presence_status(session: Session) -> None:
    presence = create_presence(
        session,
        PresenceCreate(
            occupant_name="Ngozi",
            status=PresenceStatus.HOME,
        ),
    )

    previous_since = presence.since

    updated_presence = update_presence(
        session,
        presence,
        PresenceUpdate(
            status=PresenceStatus.AWAY,
            note="At work",
        ),
    )

    assert updated_presence.status == PresenceStatus.AWAY
    assert updated_presence.note == "At work"
    assert updated_presence.since >= previous_since


def test_update_presence_note_without_status_change(
    session: Session,
) -> None:
    presence = create_presence(
        session,
        PresenceCreate(
            occupant_name="Tunde",
            status=PresenceStatus.SLEEPING,
        ),
    )

    previous_since = presence.since

    updated_presence = update_presence(
        session,
        presence,
        PresenceUpdate(
            status=PresenceStatus.SLEEPING,
            note="Sleeping upstairs",
        ),
    )

    assert updated_presence.status == PresenceStatus.SLEEPING
    assert updated_presence.note == "Sleeping upstairs"
    assert updated_presence.since == previous_since