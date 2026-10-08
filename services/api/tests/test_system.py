import pytest
from httpx import ASGITransport, AsyncClient

from nexa_api.main import app


@pytest.fixture
def anyio_backend() -> str:
    """Run asynchronous tests using asyncio only."""

    return "asyncio"


@pytest.mark.anyio
async def test_health_endpoint() -> None:
    """The health endpoint should report a healthy Nexa API."""

    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.get("/health")

    assert response.status_code == 200

    payload = response.json()

    assert payload["status"] == "ok"
    assert payload["service"] == "Nexa Core API"
    assert payload["version"] == "0.1.0"
    assert payload["environment"] == "development"
    assert payload["timestamp"]


@pytest.mark.anyio
async def test_openapi_schema() -> None:
    """Nexa should expose valid API documentation."""

    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.get("/openapi.json")

    assert response.status_code == 200

    schema = response.json()

    assert schema["info"]["title"] == "Nexa Core API"
    assert schema["info"]["version"] == "0.1.0"
    assert "/health" in schema["paths"]