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


def _format_presence(
    records: list[dict[str, Any]],
) -> str:
    """Create a natural spoken response for household presence."""

    if not records:
        return (
            "I don't have any household presence information right now."
        )

    if len(records) == 1:
        record = records[0]

        name = str(
            record.get(
                "occupant_name",
                "Someone",
            )
        )

        status = str(
            record.get(
                "status",
                "unknown",
            )
        ).replace("_", " ")

        if status == "home":
            return f"{name} is currently at home."

        if status == "away":
            return f"{name} is currently away."

        if status == "sleeping":
            return f"{name} is currently sleeping."

        return f"{name}'s current status is {status}."

    home_names = [
        str(record.get("occupant_name"))
        for record in records
        if str(record.get("status")) == "home"
        and record.get("occupant_name")
    ]

    if home_names:
        names = ", ".join(home_names)

        return (
            f"{len(home_names)} household members are currently "
            f"at home: {names}."
        )

    return (
        f"I have presence information for "
        f"{len(records)} household members."
    )


def _format_tasks(
    records: list[dict[str, Any]],
) -> str:
    """Create a natural spoken response for open household tasks."""

    if not records:
        return "You don't have any open household tasks."

    if len(records) == 1:
        title = str(
            records[0].get(
                "title",
                "an unnamed task",
            )
        )

        return f"You have one open task: {title}."

    titles = [
        str(record.get("title"))
        for record in records
        if record.get("title")
    ]

    if len(titles) <= 3:
        return (
            f"You have {len(records)} open tasks: "
            f"{', '.join(titles)}."
        )

    first_three = ", ".join(titles[:3])

    return (
        f"You have {len(records)} open tasks. "
        f"The first three are {first_three}."
    )


def _format_visitors(
    records: list[dict[str, Any]],
) -> str:
    """Create a natural spoken response for expected visitors."""

    if not records:
        return "No visitors are currently expected."

    if len(records) == 1:
        record = records[0]

        name = str(
            record.get(
                "name",
                "A visitor",
            )
        )

        purpose = record.get("purpose")

        if purpose:
            return (
                f"{name} is expected for "
                f"{str(purpose).lower()}."
            )

        return f"{name} is currently expected."

    names = [
        str(record.get("name"))
        for record in records
        if record.get("name")
    ]

    if names:
        return (
            f"{len(records)} visitors are expected: "
            f"{', '.join(names)}."
        )

    return f"{len(records)} visitors are currently expected."


def _format_deliveries(
    records: list[dict[str, Any]],
) -> str:
    """Create a natural spoken response for pending deliveries."""

    if not records:
        return "You don't have any pending deliveries."

    if len(records) == 1:
        record = records[0]

        description = str(
            record.get(
                "description",
                "package",
            )
        )

        carrier = record.get("carrier")

        if carrier:
            return (
                f"You have one pending {carrier} delivery: "
                f"{description}."
            )

        return (
            f"You have one pending delivery: "
            f"{description}."
        )

    descriptions = []

    for record in records:
        description = record.get("description")
        carrier = record.get("carrier")

        if not description:
            continue

        if carrier:
            descriptions.append(
                f"{carrier} {description}"
            )
        else:
            descriptions.append(
                str(description)
            )

    if descriptions:
        return (
            f"You have {len(records)} pending deliveries: "
            f"{', '.join(descriptions)}."
        )

    return f"You have {len(records)} pending deliveries."


def _format_household_records(
    records: list[object],
) -> str:
    """Determine the household record type and format it naturally."""

    dict_records = [
        record
        for record in records
        if isinstance(record, dict)
    ]

    if not dict_records:
        return "I don't have any matching household records."

    first = dict_records[0]

    if "occupant_name" in first:
        return _format_presence(dict_records)

    if "title" in first:
        return _format_tasks(dict_records)

    if "name" in first and "expected_start" in first:
        return _format_visitors(dict_records)

    if "description" in first and (
        "carrier" in first
        or "tracking_reference" in first
    ):
        return _format_deliveries(dict_records)

    return (
        f"I found {len(dict_records)} matching "
        "household record"
        f"{'' if len(dict_records) == 1 else 's'}."
    )


def _build_spoken_message(
    result: object,
) -> str:
    """Create an assistant-friendly spoken message from an MCP result."""

    if result is None:
        return (
            "I couldn't find a Nexa capability for that request yet."
        )

    if isinstance(result, dict):
        briefing = result.get("briefing")

        if isinstance(briefing, str) and briefing.strip():
            return briefing.strip()

        message = result.get("message")

        if isinstance(message, str) and message.strip():
            return message.strip()

        records = result.get("result")

        if isinstance(records, list):
            return _format_household_records(records)

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