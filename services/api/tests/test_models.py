from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from nexa_api.database import Base
from nexa_api.enums import (
    EventSource,
    EventType,
    PresenceStatus,
)
from nexa_api.models import (
    ConversationMessage,
    ConversationSession,
    Delivery,
    ExpectedVisitor,
    HomeEvent,
    HouseholdPresence,
    HouseholdTask,
)


def create_test_session() -> Session:
    """Create an isolated in-memory SQLite session."""

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )

    Base.metadata.create_all(bind=engine)

    test_session = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
    )

    return test_session()


def test_household_task_table_registered() -> None:
    """HouseholdTask should be registered with SQLAlchemy."""

    assert HouseholdTask.__tablename__ == "household_tasks"


def test_household_task_database_round_trip() -> None:
    """Household tasks should persist correctly."""

    session = create_test_session()

    try:
        task = HouseholdTask(
            title="Repair kitchen socket",
        )

        session.add(task)
        session.commit()
        session.refresh(task)

        assert task.id is not None
        assert task.title == "Repair kitchen socket"
        assert task.created_at is not None
    finally:
        session.close()


def test_expected_visitor_table_registered() -> None:
    """ExpectedVisitor should be registered with SQLAlchemy."""

    assert ExpectedVisitor.__tablename__ == "expected_visitors"


def test_expected_visitor_database_round_trip() -> None:
    """Expected visitors should persist correctly."""

    session = create_test_session()

    try:
        visitor = ExpectedVisitor(
            name="Ada Okafor",
            purpose="Electrical repair",
            expected_start=datetime(
                2030,
                1,
                1,
                10,
                0,
            ),
            expected_end=datetime(
                2030,
                1,
                1,
                11,
                0,
            ),
        )

        session.add(visitor)
        session.commit()
        session.refresh(visitor)

        assert visitor.id is not None
        assert visitor.name == "Ada Okafor"
        assert visitor.purpose == "Electrical repair"
        assert visitor.created_at is not None
    finally:
        session.close()


def test_home_event_table_registered() -> None:
    """HomeEvent should be registered with SQLAlchemy."""

    assert HomeEvent.__tablename__ == "home_events"


def test_home_event_database_round_trip() -> None:
    """Home events should persist correctly."""

    session = create_test_session()

    try:
        event = HomeEvent(
            event_type=EventType.VISITOR_DETECTED,
            source=EventSource.MANUAL,
            summary="Visitor detected at the front door",
            confidence=95,
        )

        session.add(event)
        session.commit()
        session.refresh(event)

        assert event.id is not None
        assert event.event_type == EventType.VISITOR_DETECTED
        assert event.source == EventSource.MANUAL
        assert event.summary == (
            "Visitor detected at the front door"
        )
        assert event.created_at is not None
    finally:
        session.close()


def test_delivery_table_registered() -> None:
    """Delivery should be registered with SQLAlchemy."""

    assert Delivery.__tablename__ == "deliveries"


def test_delivery_database_round_trip() -> None:
    """Deliveries should persist correctly."""

    session = create_test_session()

    try:
        delivery = Delivery(
            description="MacBook Pro package",
            carrier="DHL",
            tracking_reference="NEXA-DHL-2030-001",
        )

        session.add(delivery)
        session.commit()
        session.refresh(delivery)

        assert delivery.id is not None
        assert delivery.description == "MacBook Pro package"
        assert delivery.carrier == "DHL"
        assert delivery.created_at is not None
    finally:
        session.close()


def test_household_presence_table_registered() -> None:
    """HouseholdPresence should be registered with SQLAlchemy."""

    assert HouseholdPresence.__tablename__ == "household_presence"


def test_household_presence_database_round_trip() -> None:
    """Household presence records should persist correctly."""

    session = create_test_session()

    try:
        presence = HouseholdPresence(
            occupant_name="Obumneme",
            status=PresenceStatus.HOME,
            note="At home",
        )

        session.add(presence)
        session.commit()
        session.refresh(presence)

        assert presence.id is not None
        assert presence.occupant_name == "Obumneme"
        assert presence.status == PresenceStatus.HOME
        assert presence.created_at is not None
    finally:
        session.close()


def test_conversation_session_table_registered() -> None:
    """ConversationSession should be registered with SQLAlchemy."""

    assert (
        ConversationSession.__tablename__
        == "conversation_sessions"
    )


def test_conversation_message_table_registered() -> None:
    """ConversationMessage should be registered with SQLAlchemy."""

    assert (
        ConversationMessage.__tablename__
        == "conversation_messages"
    )


def test_conversation_session_database_round_trip() -> None:
    """Conversation sessions should persist correctly."""

    session = create_test_session()

    try:
        conversation = ConversationSession()

        session.add(conversation)
        session.commit()
        session.refresh(conversation)

        assert conversation.id is not None
        assert conversation.created_at is not None
        assert conversation.updated_at is not None
    finally:
        session.close()


def test_conversation_message_database_round_trip() -> None:
    """Conversation messages should persist against a session."""

    session = create_test_session()

    try:
        conversation = ConversationSession()

        session.add(conversation)
        session.commit()
        session.refresh(conversation)

        message = ConversationMessage(
            session_id=conversation.id,
            role="user",
            content="Who is home?",
        )

        session.add(message)
        session.commit()
        session.refresh(message)

        assert message.id is not None
        assert message.session_id == conversation.id
        assert message.role == "user"
        assert message.content == "Who is home?"
        assert message.created_at is not None
    finally:
        session.close()