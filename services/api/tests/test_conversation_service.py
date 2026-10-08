import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from nexa_api.conversation_service import (
    add_message,
    create_conversation,
    get_conversation,
    list_recent_messages,
)
from nexa_api.database import Base


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


def test_create_conversation() -> None:
    """A new conversation should persist."""

    session = create_test_session()

    try:
        conversation = create_conversation(session)

        assert conversation.id is not None
        assert conversation.created_at is not None
        assert conversation.updated_at is not None

        stored = get_conversation(
            session,
            conversation.id,
        )

        assert stored is not None
        assert stored.id == conversation.id
    finally:
        session.close()


def test_get_missing_conversation_returns_none() -> None:
    """Unknown conversation IDs should return None."""

    session = create_test_session()

    try:
        conversation = get_conversation(
            session,
            "missing-session",
        )

        assert conversation is None
    finally:
        session.close()


def test_add_message_to_conversation() -> None:
    """Messages should persist against a conversation."""

    session = create_test_session()

    try:
        conversation = create_conversation(session)

        message = add_message(
            session,
            conversation.id,
            "user",
            "Who is home?",
        )

        assert message.id is not None
        assert message.session_id == conversation.id
        assert message.role == "user"
        assert message.content == "Who is home?"
        assert message.created_at is not None
    finally:
        session.close()


def test_add_message_normalizes_role_and_content() -> None:
    """Role casing and surrounding whitespace should be cleaned."""

    session = create_test_session()

    try:
        conversation = create_conversation(session)

        message = add_message(
            session,
            conversation.id,
            " USER ",
            "  Who is home?  ",
        )

        assert message.role == "user"
        assert message.content == "Who is home?"
    finally:
        session.close()


def test_add_message_rejects_invalid_role() -> None:
    """Unsupported conversation roles should fail."""

    session = create_test_session()

    try:
        conversation = create_conversation(session)

        with pytest.raises(
            ValueError,
            match="Conversation role",
        ):
            add_message(
                session,
                conversation.id,
                "system",
                "Internal instruction",
            )
    finally:
        session.close()


def test_add_message_rejects_blank_content() -> None:
    """Blank messages should not be stored."""

    session = create_test_session()

    try:
        conversation = create_conversation(session)

        with pytest.raises(
            ValueError,
            match="cannot be blank",
        ):
            add_message(
                session,
                conversation.id,
                "user",
                "   ",
            )
    finally:
        session.close()


def test_add_message_rejects_missing_conversation() -> None:
    """Messages cannot be added to unknown conversations."""

    session = create_test_session()

    try:
        with pytest.raises(
            ValueError,
            match="does not exist",
        ):
            add_message(
                session,
                "missing-session",
                "user",
                "Who is home?",
            )
    finally:
        session.close()


def test_list_recent_messages_returns_oldest_to_newest() -> None:
    """Recent messages should be returned in conversation order."""

    session = create_test_session()

    try:
        conversation = create_conversation(session)

        add_message(
            session,
            conversation.id,
            "user",
            "Who is home?",
        )

        add_message(
            session,
            conversation.id,
            "assistant",
            "Obumneme is home.",
        )

        add_message(
            session,
            conversation.id,
            "user",
            "Any deliveries?",
        )

        messages = list_recent_messages(
            session,
            conversation.id,
        )

        assert len(messages) == 3
        assert messages[0].content == "Who is home?"
        assert messages[1].content == "Obumneme is home."
        assert messages[2].content == "Any deliveries?"
    finally:
        session.close()


def test_list_recent_messages_respects_limit() -> None:
    """Only the requested number of recent messages should return."""

    session = create_test_session()

    try:
        conversation = create_conversation(session)

        add_message(
            session,
            conversation.id,
            "user",
            "Message one",
        )

        add_message(
            session,
            conversation.id,
            "assistant",
            "Message two",
        )

        add_message(
            session,
            conversation.id,
            "user",
            "Message three",
        )

        messages = list_recent_messages(
            session,
            conversation.id,
            limit=2,
        )

        assert len(messages) == 2
        assert messages[0].content == "Message two"
        assert messages[1].content == "Message three"
    finally:
        session.close()


def test_list_recent_messages_rejects_invalid_limit() -> None:
    """History limits below one should fail."""

    session = create_test_session()

    try:
        conversation = create_conversation(session)

        with pytest.raises(
            ValueError,
            match="at least 1",
        ):
            list_recent_messages(
                session,
                conversation.id,
                limit=0,
            )
    finally:
        session.close()