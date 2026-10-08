"""Tests for Nexa skill-aware conversation context."""

from pathlib import Path

from nexa_api.conversation_context import (
    build_skill_context,
    format_skill_context,
)


def test_build_skill_context_selects_presence_skill() -> None:
    """Presence requests should load presence skill context."""

    context = build_skill_context(
        "Who is home?",
    )

    assert context is not None
    assert context.skill_name == "presence-management"
    assert "household presence" in context.skill_description.casefold()
    assert "update_presence" in context.instructions


def test_build_skill_context_selects_visitor_skill() -> None:
    """Visitor requests should load visitor skill context."""

    context = build_skill_context(
        "Chinedu has arrived.",
    )

    assert context is not None
    assert context.skill_name == "visitor-management"
    assert "mark_visitor_arrived" in context.instructions


def test_build_skill_context_selects_delivery_skill() -> None:
    """Delivery requests should load delivery skill context."""

    context = build_skill_context(
        "The laptop package has arrived.",
    )

    assert context is not None
    assert context.skill_name == "delivery-management"
    assert "mark_delivery_delivered" in context.instructions


def test_build_skill_context_returns_none_for_unrelated_message(
    tmp_path: Path,
) -> None:
    """Unrelated messages should not force Agent Skill context."""

    context = build_skill_context(
        "Tell me a joke.",
        tmp_path,
    )

    assert context is None


def test_format_skill_context_contains_skill_metadata() -> None:
    """Formatted context should contain selected skill information."""

    context = build_skill_context(
        "What tasks are open?",
    )

    formatted = format_skill_context(context)

    assert formatted is not None
    assert "ACTIVE AGENT SKILL" in formatted
    assert "task-management" in formatted
    assert "get_open_tasks" in formatted


def test_format_skill_context_handles_missing_context() -> None:
    """Formatting should safely handle requests with no selected skill."""

    assert format_skill_context(None) is None