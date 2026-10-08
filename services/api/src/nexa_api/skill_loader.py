"""Load and validate Nexa Agent Skills."""

from dataclasses import dataclass
from pathlib import Path

DEFAULT_SKILLS_DIRECTORY = (
    Path(__file__).resolve().parents[2]
    / ".agents"
    / "skills"
)


@dataclass(frozen=True)
class AgentSkill:
    """A validated Agent Skill loaded from a SKILL.md file."""

    name: str
    description: str
    instructions: str
    path: Path


def _parse_frontmatter(
    content: str,
) -> tuple[dict[str, str], str]:
    """Parse simple YAML frontmatter from a SKILL.md file."""

    if not content.startswith("---\n"):
        raise ValueError(
            "SKILL.md must begin with YAML frontmatter."
        )

    closing_marker = content.find("\n---\n", 4)

    if closing_marker == -1:
        raise ValueError(
            "SKILL.md frontmatter is missing a closing marker."
        )

    raw_frontmatter = content[4:closing_marker]
    instructions = content[closing_marker + 5 :].strip()

    metadata: dict[str, str] = {}

    for line in raw_frontmatter.splitlines():
        stripped = line.strip()

        if not stripped:
            continue

        if ":" not in stripped:
            raise ValueError(
                f"Invalid frontmatter line: {line}"
            )

        key, value = stripped.split(":", 1)

        metadata[key.strip()] = value.strip()

    return metadata, instructions


def load_skill(
    skill_file: Path,
) -> AgentSkill:
    """Load and validate a single Agent Skill."""

    content = skill_file.read_text(encoding="utf-8")

    metadata, instructions = _parse_frontmatter(content)

    name = metadata.get("name", "").strip()
    description = metadata.get("description", "").strip()

    if not name:
        raise ValueError(
            f"{skill_file} is missing required field 'name'."
        )

    if not description:
        raise ValueError(
            f"{skill_file} is missing required field 'description'."
        )

    if not instructions:
        raise ValueError(
            f"{skill_file} contains no skill instructions."
        )

    return AgentSkill(
        name=name,
        description=description,
        instructions=instructions,
        path=skill_file,
    )


def discover_skills(
    skills_directory: Path = DEFAULT_SKILLS_DIRECTORY,
) -> list[AgentSkill]:
    """Discover and validate all Agent Skills in a directory."""

    if not skills_directory.exists():
        return []

    skill_files = sorted(
        skills_directory.glob("*/SKILL.md")
    )

    skills = [
        load_skill(skill_file)
        for skill_file in skill_files
    ]

    names = [skill.name for skill in skills]

    if len(names) != len(set(names)):
        raise ValueError(
            "Duplicate Agent Skill names were found."
        )

    return skills


def get_skill_by_name(
    name: str,
    skills_directory: Path = DEFAULT_SKILLS_DIRECTORY,
) -> AgentSkill | None:
    """Return a discovered Agent Skill by name."""

    normalized_name = name.strip().casefold()

    for skill in discover_skills(skills_directory):
        if skill.name.casefold() == normalized_name:
            return skill

    return None