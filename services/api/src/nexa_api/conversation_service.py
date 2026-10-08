from sqlalchemy import select
from sqlalchemy.orm import Session

from nexa_api.models import (
    ConversationMessage,
    ConversationSession,
)


def create_conversation(
    session: Session,
) -> ConversationSession:
    """Create a new persistent Nexa conversation."""

    conversation = ConversationSession()

    session.add(conversation)
    session.commit()
    session.refresh(conversation)

    return conversation


def get_conversation(
    session: Session,
    session_id: str,
) -> ConversationSession | None:
    """Get a conversation by ID."""

    return session.get(
        ConversationSession,
        session_id,
    )


def add_message(
    session: Session,
    session_id: str,
    role: str,
    content: str,
) -> ConversationMessage:
    """Add a message to an existing conversation."""

    normalized_role = role.strip().lower()
    normalized_content = content.strip()

    if normalized_role not in {"user", "assistant"}:
        raise ValueError(
            "Conversation role must be 'user' or 'assistant'."
        )

    if not normalized_content:
        raise ValueError(
            "Conversation message content cannot be blank."
        )

    conversation = get_conversation(
        session,
        session_id,
    )

    if conversation is None:
        raise ValueError(
            f"Conversation '{session_id}' does not exist."
        )

    message = ConversationMessage(
        session_id=session_id,
        role=normalized_role,
        content=normalized_content,
    )

    session.add(message)
    session.commit()
    session.refresh(message)

    return message


def list_recent_messages(
    session: Session,
    session_id: str,
    limit: int = 10,
) -> list[ConversationMessage]:
    """Return recent conversation messages oldest to newest."""

    if limit < 1:
        raise ValueError(
            "Conversation message limit must be at least 1."
        )

    statement = (
        select(ConversationMessage)
        .where(
            ConversationMessage.session_id == session_id,
        )
        .order_by(
            ConversationMessage.created_at.desc(),
        )
        .limit(limit)
    )

    messages = list(
        session.scalars(statement)
    )

    messages.reverse()

    return messages