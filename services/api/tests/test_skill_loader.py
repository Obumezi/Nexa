"""Tests for the Nexa Agent Skill loader."""

from pathlib import Path

import pytest

from nexa_api.skill_loader import (
    discover_skills,
    get_skill_by_name,
    load_skill,
)


def _write_skill(
    directory: Path,
    folder_name: str,
    name: str,
    description: str,
    instructions: str = "# Instructions\n\nUse Nexa safely.",
) -> Path:
    """Create a temporary Agent Skill for testing."""

    skill_directory = directory / folder_name
    skill_directory.mkdir(parents=True)

    skill_file = skill_directory / "SKILL.md"

    skill_file.write_text(
        (
            "---\n"
            f"name: {name}\n"
            f"description: {description}\n"
            "---\n"
            f"{instructions}\n"
        ),
        encoding="utf-8",
    )

    return skill_file


def test_load_skill_reads_metadata_and_instructions(
    tmp_path: Path,
) -> None:
    """A valid SKILL.md should load successfully."""

    skill_file = _write_skill(
        tmp_path,
        "task-management",
        "task-management",
        "Manage household tasks.",
    )

    skill = load_skill(skill_file)

    assert skill.name == "task-management"
    assert skill.description == "Manage household tasks."
    assert "Use Nexa safely." in skill.instructions
    assert skill.path == skill_file


def test_discover_skills_loads_multiple_skills(
    tmp_path: Path,
) -> None:
    """Skill discovery should find all valid skill folders."""

    _write_skill(
        tmp_path,
        "task-management",
        "task-management",
        "Manage household tasks.",
    )

    _write_skill(
        tmp_path,
        "visitor-management",
        "visitor-management",
        "Manage household visitors.",
    )

    skills = discover_skills(tmp_path)

    assert len(skills) == 2

    assert {
        skill.name
        for skill in skills
    } == {
        "task-management",
        "visitor-management",
    }


def test_get_skill_by_name_returns_matching_skill(
    tmp_path: Path,
) -> None:
    """A discovered skill should be retrievable by name."""

    _write_skill(
        tmp_path,
        "presence-management",
        "presence-management",
        "Manage household presence.",
    )

    skill = get_skill_by_name(
        "presence-management",
        tmp_path,
    )

    assert skill is not None
    assert skill.name == "presence-management"


def test_load_skill_rejects_missing_description(
    tmp_path: Path,
) -> None:
    """Skills without required metadata should be rejected."""

    skill_file = _write_skill(
        tmp_path,
        "invalid-skill",
        "invalid-skill",
        "",
    )

    with pytest.raises(
        ValueError,
        match="missing required field 'description'",
    ):
        load_skill(skill_file)


def test_discover_skills_rejects_duplicate_names(
    tmp_path: Path,
) -> None:
    """Two Agent Skills must not use the same name."""

    _write_skill(
        tmp_path,
        "first",
        "duplicate-skill",
        "First skill.",
    )

    _write_skill(
        tmp_path,
        "second",
        "duplicate-skill",
        "Second skill.",
    )

    with pytest.raises(
        ValueError,
        match="Duplicate Agent Skill names",
    ):
        discover_skills(tmp_path)