from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from nexa_api.agent_service import run_agent
from nexa_api.conversation_service import (
    add_message,
    create_conversation,
    get_conversation,
    list_recent_messages,
)
from nexa_api.database import get_db
from nexa_api.schemas import AgentRequest, AgentResponse

router = APIRouter(
    prefix="/api/v1/agent",
    tags=["agent"],
)

DbSession = Annotated[
    Session,
    Depends(get_db),
]


@router.post(
    "",
    response_model=AgentResponse,
)
def agent_request(
    request: AgentRequest,
    session: DbSession,
) -> AgentResponse:
    """Process a Nexa agent request with conversation persistence."""

    # ---------------------------------------------------------
    # GET OR CREATE CONVERSATION
    # ---------------------------------------------------------

    if request.session_id:
        conversation = get_conversation(
            session,
            request.session_id,
        )

        if conversation is None:
            raise HTTPException(
                status_code=404,
                detail="Conversation session not found.",
            )
    else:
        conversation = create_conversation(session)

    # ---------------------------------------------------------
    # LOAD PREVIOUS CONVERSATION HISTORY
    # ---------------------------------------------------------

    recent_messages = list_recent_messages(
        session,
        conversation.id,
        limit=10,
    )

    history = [
        {
            "role": message.role,
            "content": message.content,
        }
        for message in recent_messages
    ]

    # ---------------------------------------------------------
    # SAVE CURRENT USER MESSAGE
    # ---------------------------------------------------------

    add_message(
        session,
        conversation.id,
        "user",
        request.message,
    )

    # ---------------------------------------------------------
    # RUN NEXA AGENT WITH PREVIOUS HISTORY
    # ---------------------------------------------------------

    response = run_agent(
    session,
    request.message,
    confirm=request.confirm,
    history=history,
    speaker_name=request.speaker_name,
)

    response.session_id = conversation.id

    # ---------------------------------------------------------
    # SAVE NEXA RESPONSE
    # ---------------------------------------------------------

    add_message(
        session,
        conversation.id,
        "assistant",
        response.message,
    )

    return response