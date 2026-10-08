"""Tests for the Nexa Alexa+ simulator interface."""

from fastapi.testclient import TestClient

from nexa_api.main import app

client = TestClient(app)


def test_simulator_page_loads() -> None:
    """The Alexa+ simulator page should be available."""

    response = client.get(
        "/simulator",
    )

    assert response.status_code == 200
    assert "Nexa" in response.text
    assert "Alexa+ Experience Simulator" in response.text


def test_simulator_page_contains_agent_features() -> None:
    """The simulator should expose key demo controls."""

    response = client.get(
        "/simulator",
    )

    assert response.status_code == 200

    assert "Active Agent Skill" in response.text
    assert "Last MCP Result" in response.text
    assert "speakerName" in response.text
    assert "confirmButton" in response.text