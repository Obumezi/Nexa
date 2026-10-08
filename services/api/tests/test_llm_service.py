from unittest.mock import Mock

from nexa_api.llm_service import resolve_intent_with_llm
from nexa_api.schemas import AgentDecision, AgentIntent


def test_llm_resolver_returns_structured_decision(
    monkeypatch,
) -> None:
    """The LLM resolver should return parsed AgentDecision data."""

    monkeypatch.setenv(
        "NEXA_OPENAI_API_KEY",
        "test-key",
    )

    from nexa_api.config import get_settings

    get_settings.cache_clear()

    parsed_decision = AgentDecision(
        intent=AgentIntent.GET_OPEN_TASKS,
        confidence=0.96,
    )

    mock_response = Mock()
    mock_response.output_parsed = parsed_decision

    mock_client = Mock()
    mock_client.responses.parse.return_value = mock_response

    decision = resolve_intent_with_llm(
        "Is there anything I still need to sort out?",
        client=mock_client,
    )

    assert decision.intent == AgentIntent.GET_OPEN_TASKS
    assert decision.confidence == 0.96

    mock_client.responses.parse.assert_called_once()

    get_settings.cache_clear()


def test_llm_resolver_handles_missing_parsed_output(
    monkeypatch,
) -> None:
    """Missing structured output should safely become unknown."""

    monkeypatch.setenv(
        "NEXA_OPENAI_API_KEY",
        "test-key",
    )

    from nexa_api.config import get_settings

    get_settings.cache_clear()

    mock_response = Mock()
    mock_response.output_parsed = None

    mock_client = Mock()
    mock_client.responses.parse.return_value = mock_response

    decision = resolve_intent_with_llm(
        "Something ambiguous",
        client=mock_client,
    )

    assert decision.intent == AgentIntent.UNKNOWN
    assert decision.confidence == 0.0

    get_settings.cache_clear()

def test_llm_resolver_uses_history_to_resolve_visitor_reference() -> None:
    """The LLM resolver should support visitor references from history."""

    decision = AgentDecision(
        intent=AgentIntent.MARK_VISITOR_ARRIVED,
        confidence=0.97,
        target_visitor_name="Ada Okafor",
    )

    parsed_response = Mock()
    parsed_response.output_parsed = decision

    client = Mock()
    client.responses.parse.return_value = parsed_response

    history = [
        {
            "role": "user",
            "content": "Who is coming today?",
        },
        {
            "role": "assistant",
            "content": "Ada Okafor is expected today.",
        },
    ]

    result = resolve_intent_with_llm(
        "Has she arrived?",
        history=history,
        client=client,
    )

    assert result.intent == AgentIntent.MARK_VISITOR_ARRIVED
    assert result.target_visitor_name == "Ada Okafor"


def test_llm_resolver_uses_history_to_resolve_departed_visitor() -> None:
    """The LLM resolver should resolve a departing visitor from context."""

    decision = AgentDecision(
        intent=AgentIntent.MARK_VISITOR_DEPARTED,
        confidence=0.98,
        target_visitor_name="Chinedu Okafor",
    )

    parsed_response = Mock()
    parsed_response.output_parsed = decision

    client = Mock()
    client.responses.parse.return_value = parsed_response

    history = [
        {
            "role": "assistant",
            "content": "Chinedu Okafor has arrived.",
        },
    ]

    result = resolve_intent_with_llm(
        "He has left.",
        history=history,
        client=client,
    )

    assert result.intent == AgentIntent.MARK_VISITOR_DEPARTED
    assert result.target_visitor_name == "Chinedu Okafor"


def test_llm_resolver_uses_history_to_resolve_delivery_reference() -> None:
    """The LLM resolver should resolve delivery references from context."""

    decision = AgentDecision(
        intent=AgentIntent.MARK_DELIVERY_COLLECTED,
        confidence=0.99,
        target_delivery_description="Dell Laptop package",
    )

    parsed_response = Mock()
    parsed_response.output_parsed = decision

    client = Mock()
    client.responses.parse.return_value = parsed_response

    history = [
        {
            "role": "user",
            "content": "What deliveries are pending?",
        },
        {
            "role": "assistant",
            "content": "The Dell Laptop package is pending.",
        },
    ]

    result = resolve_intent_with_llm(
        "Mark it as collected.",
        history=history,
        client=client,
    )

    assert result.intent == AgentIntent.MARK_DELIVERY_COLLECTED
    assert result.target_delivery_description == "Dell Laptop package"


def test_llm_resolver_uses_history_to_resolve_task_reference() -> None:
    """The LLM resolver should resolve task references from context."""

    decision = AgentDecision(
        intent=AgentIntent.COMPLETE_TASK,
        confidence=0.99,
        target_task_title="Service the generator",
    )

    parsed_response = Mock()
    parsed_response.output_parsed = decision

    client = Mock()
    client.responses.parse.return_value = parsed_response

    history = [
        {
            "role": "assistant",
            "content": "The open task is Service the generator.",
        },
    ]

    result = resolve_intent_with_llm(
        "Mark that task as done.",
        history=history,
        client=client,
    )

    assert result.intent == AgentIntent.COMPLETE_TASK
    assert result.target_task_title == "Service the generator"

def test_llm_resolver_maps_im_home_to_current_speaker() -> None:
    """First-person home updates should resolve to the current speaker."""

    decision = AgentDecision(
        intent=AgentIntent.UPDATE_PRESENCE,
        confidence=0.99,
        target_occupant_name="Obumneme",
        target_presence_status="home",
    )

    parsed_response = Mock()
    parsed_response.output_parsed = decision

    client = Mock()
    client.responses.parse.return_value = parsed_response

    result = resolve_intent_with_llm(
        "I'm home.",
        speaker_name="Obumneme",
        client=client,
    )

    assert result.intent == AgentIntent.UPDATE_PRESENCE
    assert result.target_occupant_name == "Obumneme"
    assert result.target_presence_status == "home"


def test_llm_resolver_maps_im_leaving_to_current_speaker() -> None:
    """First-person away updates should resolve to the current speaker."""

    decision = AgentDecision(
        intent=AgentIntent.UPDATE_PRESENCE,
        confidence=0.99,
        target_occupant_name="Obumneme",
        target_presence_status="away",
    )

    parsed_response = Mock()
    parsed_response.output_parsed = decision

    client = Mock()
    client.responses.parse.return_value = parsed_response

    result = resolve_intent_with_llm(
        "I'm leaving.",
        speaker_name="Obumneme",
        client=client,
    )

    assert result.intent == AgentIntent.UPDATE_PRESENCE
    assert result.target_occupant_name == "Obumneme"
    assert result.target_presence_status == "away"


def test_llm_resolver_maps_im_sleeping_to_current_speaker() -> None:
    """First-person sleeping updates should resolve to the current speaker."""

    decision = AgentDecision(
        intent=AgentIntent.UPDATE_PRESENCE,
        confidence=0.99,
        target_occupant_name="Obumneme",
        target_presence_status="sleeping",
    )

    parsed_response = Mock()
    parsed_response.output_parsed = decision

    client = Mock()
    client.responses.parse.return_value = parsed_response

    result = resolve_intent_with_llm(
        "I'm going to sleep.",
        speaker_name="Obumneme",
        client=client,
    )

    assert result.intent == AgentIntent.UPDATE_PRESENCE
    assert result.target_occupant_name == "Obumneme"
    assert result.target_presence_status == "sleeping"

    def test_llm_resolver_includes_agent_skill_context() -> None:
     """The LLM resolver should include selected Agent Skill context."""

    captured_instructions = None

    class FakeParsedResponse:
        output_parsed = AgentDecision(
            intent=AgentIntent.GET_OPEN_TASKS,
            confidence=0.95,
        )

    class FakeResponses:
        def parse(self, **kwargs):
            nonlocal captured_instructions

            captured_instructions = kwargs["instructions"]

            return FakeParsedResponse()

    class FakeClient:
        responses = FakeResponses()

    resolve_intent_with_llm(
        "What tasks are open?",
        skill_context=(
            "ACTIVE AGENT SKILL\n"
            "Name: task-management\n"
            "Use get_open_tasks."
        ),
        client=FakeClient(),
    )

    assert captured_instructions is not None
    assert "AGENT SKILL CONTEXT" in captured_instructions
    assert "task-management" in captured_instructions
    assert "get_open_tasks" in captured_instructions

def test_llm_resolver_includes_agent_skill_context() -> None:
    """The LLM resolver should include selected Agent Skill context."""

    captured_instructions = None

    class FakeParsedResponse:
        output_parsed = AgentDecision(
            intent=AgentIntent.GET_OPEN_TASKS,
            confidence=0.95,
        )

    class FakeResponses:
        def parse(self, **kwargs):
            nonlocal captured_instructions

            captured_instructions = kwargs["instructions"]

            return FakeParsedResponse()

    class FakeClient:
        responses = FakeResponses()

    resolve_intent_with_llm(
        "What tasks are open?",
        skill_context=(
            "ACTIVE AGENT SKILL\n"
            "Name: task-management\n"
            "Use get_open_tasks."
        ),
        client=FakeClient(),
    )

    assert captured_instructions is not None
    assert "AGENT SKILL CONTEXT" in captured_instructions
    assert "task-management" in captured_instructions
    assert "get_open_tasks" in captured_instructions