"""Tests for the Nexa Alexa+ simulator route."""

from fastapi.testclient import TestClient

from nexa_api.main import app

client = TestClient(app)


def test_simulator_returns_skill_and_result(
    monkeypatch,
) -> None:
    """Simulator requests should expose selected skill and MCP result."""

    from nexa_api import simulator_routes

    async def fake_run_mcp_conversation_turn(
        message: str,
        *,
        history=None,
        speaker_name=None,
        confirm=False,
        mcp_url="http://127.0.0.1:8001/mcp",
    ) -> object:
        return {
            "result": [
                {
                    "occupant_name": "Obumneme",
                    "status": "home",
                }
            ]
        }

    monkeypatch.setattr(
        simulator_routes,
        "run_mcp_conversation_turn",
        fake_run_mcp_conversation_turn,
    )

    response = client.post(
        "/api/v1/simulator",
        json={
            "message": "Who is home?",
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["skill"] == "presence-management"
    assert body["requires_confirmation"] is False
    assert body["action_executed"] is False
    assert body["result"]["result"][0]["occupant_name"] == "Obumneme"


def test_simulator_exposes_confirmation(
    monkeypatch,
) -> None:
    """Simulator should surface confirmation requirements."""

    from nexa_api import simulator_routes

    async def fake_run_mcp_conversation_turn(
        message: str,
        *,
        history=None,
        speaker_name=None,
        confirm=False,
        mcp_url="http://127.0.0.1:8001/mcp",
    ) -> object:
        return {
            "intent": "complete_task",
            "message": "Mark the task as completed?",
            "requires_confirmation": True,
            "action_executed": False,
        }

    monkeypatch.setattr(
        simulator_routes,
        "run_mcp_conversation_turn",
        fake_run_mcp_conversation_turn,
    )

    response = client.post(
        "/api/v1/simulator",
        json={
            "message": "Mark the generator task done.",
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["skill"] == "task-management"
    assert body["message"] == "Mark the task as completed?"
    assert body["requires_confirmation"] is True
    assert body["action_executed"] is False


def test_simulator_handles_unknown_request(
    monkeypatch,
) -> None:
    """Unsupported requests should fail gracefully."""

    from nexa_api import simulator_routes

    async def fake_run_mcp_conversation_turn(
        message: str,
        *,
        history=None,
        speaker_name=None,
        confirm=False,
        mcp_url="http://127.0.0.1:8001/mcp",
    ) -> object | None:
        return None

    monkeypatch.setattr(
        simulator_routes,
        "run_mcp_conversation_turn",
        fake_run_mcp_conversation_turn,
    )

    response = client.post(
        "/api/v1/simulator",
        json={
            "message": "Tell me a joke.",
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["skill"] is None
    assert body["result"] is None