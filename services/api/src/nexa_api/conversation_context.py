"""Build Agent Skill context for Nexa conversations."""

from dataclasses import dataclass
from pathlib import Path

from nexa_api.skill_loader import (
    DEFAULT_SKILLS_DIRECTORY,
    AgentSkill,
)
from nexa_api.skill_selector import select_skill


@dataclass(frozen=True)
class ConversationSkillContext:
    """Skill context selected for a conversational request."""

    skill_name: str
    skill_description: str
    instructions: str


def build_skill_context(
    message: str,
    skills_directory: Path = DEFAULT_SKILLS_DIRECTORY,
) -> ConversationSkillContext | None:
    """Select and prepare Agent Skill context for a message."""

    skill: AgentSkill | None = select_skill(
        message,
        skills_directory,
    )

    if skill is None:
        return None

    return ConversationSkillContext(
        skill_name=skill.name,
        skill_description=skill.description,
        instructions=skill.instructions,
    )


def format_skill_context(
    context: ConversationSkillContext | None,
) -> str | None:
    """Format Agent Skill context for use by a conversational model."""

    if context is None:
        return None

    return (
        "ACTIVE AGENT SKILL\n"
        f"Name: {context.skill_name}\n"
        f"Description: {context.skill_description}\n\n"
        "Follow these skill instructions for this request:\n\n"
        f"{context.instructions}"
    )