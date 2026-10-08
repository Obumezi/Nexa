"""Select the most relevant Nexa Agent Skill for a user request."""

from pathlib import Path

from nexa_api.skill_loader import (
    DEFAULT_SKILLS_DIRECTORY,
    AgentSkill,
    get_skill_by_name,
)

HOUSEHOLD_STATUS_PHRASES = (
    "household update",
    "household status",
    "home update",
    "what's happening at home",
    "whats happening at home",
    "give me an update",
)

PRESENCE_KEYWORDS = (
    "home",
    "away",
    "leaving",
    "sleeping",
    "sleep",
    "who is home",
    "who's home",
    "whos home",
    "who is away",
)

VISITOR_KEYWORDS = (
    "visitor",
    "visit",
    "guest",
    "arrived",
    "has arrived",
    "has left",
    "coming over",
    "expected visitor",
)

DELIVERY_KEYWORDS = (
    "delivery",
    "deliveries",
    "package",
    "packages",
    "parcel",
    "courier",
    "collected",
)

TASK_KEYWORDS = (
    "task",
    "tasks",
    "to do",
    "todo",
    "complete",
    "completed",
    "mark as done",
    "done",
)


def _contains_any(
    message: str,
    phrases: tuple[str, ...],
) -> bool:
    """Return whether a normalized message contains any phrase."""

    return any(
        phrase in message
        for phrase in phrases
    )


def select_skill(
    message: str,
    skills_directory: Path = DEFAULT_SKILLS_DIRECTORY,
) -> AgentSkill | None:
    """Select the most appropriate Nexa Agent Skill for a message."""

    normalized = message.strip().casefold()

    if not normalized:
        return None

    if _contains_any(
        normalized,
        HOUSEHOLD_STATUS_PHRASES,
    ):
        return get_skill_by_name(
            "household-status",
            skills_directory,
        )

    if _contains_any(
        normalized,
        DELIVERY_KEYWORDS,
    ):
        return get_skill_by_name(
            "delivery-management",
            skills_directory,
        )

    if _contains_any(
        normalized,
        VISITOR_KEYWORDS,
    ):
        return get_skill_by_name(
            "visitor-management",
            skills_directory,
        )

    if _contains_any(
        normalized,
        TASK_KEYWORDS,
    ):
        return get_skill_by_name(
            "task-management",
            skills_directory,
        )

    if _contains_any(
        normalized,
        PRESENCE_KEYWORDS,
    ):
        return get_skill_by_name(
            "presence-management",
            skills_directory,
        )

    return None