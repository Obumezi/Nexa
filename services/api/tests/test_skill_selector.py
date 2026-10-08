"""Tests for Nexa Agent Skill selection."""

from pathlib import Path

from nexa_api.skill_selector import select_skill


def test_select_skill_routes_presence_request() -> None:
    """Presence requests should use the presence skill."""

    skill = select_skill(
        "Who is home?",
    )

    assert skill is not None
    assert skill.name == "presence-management"


def test_select_skill_routes_task_request() -> None:
    """Task requests should use the task skill."""

    skill = select_skill(
        "What tasks are still open?",
    )

    assert skill is not None
    assert skill.name == "task-management"


def test_select_skill_routes_visitor_request() -> None:
    """Visitor requests should use the visitor skill."""

    skill = select_skill(
        "Chinedu has arrived.",
    )

    assert skill is not None
    assert skill.name == "visitor-management"


def test_select_skill_routes_delivery_request() -> None:
    """Delivery requests should use the delivery skill."""

    skill = select_skill(
        "The laptop package has arrived.",
    )

    assert skill is not None
    assert skill.name == "delivery-management"


def test_select_skill_routes_household_summary() -> None:
    """Broad household summaries should use household-status."""

    skill = select_skill(
        "Give me a household update.",
    )

    assert skill is not None
    assert skill.name == "household-status"


def test_select_skill_returns_none_for_unrelated_request(
    tmp_path: Path,
) -> None:
    """Unrelated requests should not force a skill selection."""

    skill = select_skill(
        "Tell me a joke.",
        tmp_path,
    )

    assert skill is None