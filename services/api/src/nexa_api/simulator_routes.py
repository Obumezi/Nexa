"""Alexa+ style simulator routes for Nexa."""

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from nexa_api.mcp_orchestrator import run_mcp_conversation_turn
from nexa_api.skill_selector import select_skill

router = APIRouter(
    prefix="/api/v1/simulator",
    tags=["simulator"],
)


class SimulatorRequest(BaseModel):
    """Request sent by the Nexa Alexa+ simulator."""

    message: str = Field(
        min_length=1,
        max_length=1000,
    )
    speaker_name: str | None = None
    confirm: bool = False


class SimulatorResponse(BaseModel):
    """Response returned to the Alexa+ simulator."""

    message: str
    skill: str | None = None
    result: Any | None = None
    requires_confirmation: bool = False
    action_executed: bool = False


def _extract_agent_flags(
    result: object,
) -> tuple[bool, bool]:
    """Extract confirmation and execution flags from MCP results."""

    if not isinstance(result, dict):
        return False, False

    requires_confirmation = bool(
        result.get("requires_confirmation", False)
    )

    action_executed = bool(
        result.get("action_executed", False)
    )

    return requires_confirmation, action_executed


def _build_spoken_message(
    result: object,
) -> str:
    """Create a simple assistant-friendly message from an MCP result."""

    if result is None:
        return (
            "I couldn't find a Nexa capability for that request yet."
        )

    if isinstance(result, dict):
        message = result.get("message")

        if isinstance(message, str) and message.strip():
            return message

        records = result.get("result")

        if isinstance(records, list):
            if not records:
                return "I don't have any matching household records."

            return (
                f"I found {len(records)} matching "
                "household record"
                f"{'' if len(records) == 1 else 's'}."
            )

    return "Nexa completed the request."


@router.post(
    "",
    response_model=SimulatorResponse,
)
async def simulator_request(
    request: SimulatorRequest,
) -> SimulatorResponse:
    """Process one Alexa+ style conversational turn."""

    skill = select_skill(request.message)

    result = await run_mcp_conversation_turn(
        request.message,
        speaker_name=request.speaker_name,
        confirm=request.confirm,
    )

    requires_confirmation, action_executed = (
        _extract_agent_flags(result)
    )

    return SimulatorResponse(
        message=_build_spoken_message(result),
        skill=skill.name if skill else None,
        result=result,
        requires_confirmation=requires_confirmation,
        action_executed=action_executed,
    )