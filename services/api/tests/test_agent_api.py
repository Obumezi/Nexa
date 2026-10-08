from collections.abc import Generator
from datetime import datetime

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from nexa_api.database import Base, get_db
from nexa_api.delivery_service import (
    create_delivery,
    mark_delivery_delivered,
)
from nexa_api.enums import (
    DeliveryStatus,
    PresenceStatus,
    TaskStatus,
    VisitorStatus,
)
from nexa_api.main import app
from nexa_api.models import HouseholdPresence
from nexa_api.presence_service import create_presence
from nexa_api.schemas import (
    AgentDecision,
    AgentIntent,
    DeliveryCreate,
    PresenceCreate,
    TaskCreate,
    VisitorCreate,
)
from nexa_api.task_service import (
    create_task,
    list_tasks,
)
from nexa_api.visitor_service import (
    create_visitor,
    mark_visitor_arrived,
)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def session() -> Generator[Session, None, None]:
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    Base.metadata.create_all(test_engine)

    with Session(test_engine) as database_session:
        yield database_session

    Base.metadata.drop_all(test_engine)


@pytest.fixture
def test_app(
    session: Session,
) -> Generator[FastAPI, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        yield session

    app.dependency_overrides[get_db] = override_get_db

    yield app

    app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_agent_returns_open_tasks(
    test_app: FastAPI,
    session: Session,
) -> None:
    create_task(
        session,
        TaskCreate(
            title="Take out the bins",
        ),
    )

    transport = ASGITransport(app=test_app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/agent",
            json={
                "message": "What needs to be done?"
            },
        )

    assert response.status_code == 200

    body = response.json()

    assert body["intent"] == "get_open_tasks"
    assert len(body["data"]) == 1
    assert body["data"][0]["title"] == "Take out the bins"


@pytest.mark.anyio
async def test_agent_returns_household_presence(
    test_app: FastAPI,
    session: Session,
) -> None:
    create_presence(
        session,
        PresenceCreate(
            occupant_name="Obumneme",
            status="home",
        ),
    )

    transport = ASGITransport(app=test_app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/agent",
            json={
                "message": "Who is home?"
            },
        )

    assert response.status_code == 200

    body = response.json()

    assert body["intent"] == "get_household_presence"
    assert len(body["data"]) == 1
    assert body["data"][0]["occupant_name"] == "Obumneme"


@pytest.mark.anyio
async def test_agent_handles_unknown_request(
    test_app: FastAPI,
) -> None:
    transport = ASGITransport(app=test_app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/agent",
            json={
                "message": "Play some jazz."
            },
        )

    assert response.status_code == 200

    body = response.json()

    assert body["intent"] == "unknown"


@pytest.mark.anyio
async def test_agent_rejects_blank_message(
    test_app: FastAPI,
) -> None:
    transport = ASGITransport(app=test_app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/agent",
            json={
                "message": "   "
            },
        )

    assert response.status_code == 422

@pytest.mark.anyio
async def test_agent_create_task_requires_confirmation(
    test_app: FastAPI,
    monkeypatch,
) -> None:
    """Task creation should be proposed before execution."""

    from nexa_api import agent_service

    decision = AgentDecision(
        intent=AgentIntent.CREATE_TASK,
        confidence=0.98,
        task_title="Service the generator",
        task_description="Arrange generator maintenance.",
    )

    monkeypatch.setattr(
        agent_service,
        "resolve_agent_intent",
        lambda message: decision,
    )

    transport = ASGITransport(app=test_app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/agent",
            json={
                "message": "Create a task to service the generator"
            },
        )

    assert response.status_code == 200

    body = response.json()

    assert body["intent"] == "create_task"
    assert body["requires_confirmation"] is True
    assert body["action_executed"] is False
    assert (
        body["proposed_action"]["title"]
        == "Service the generator"
    )


@pytest.mark.anyio
async def test_agent_create_task_executes_after_confirmation(
    test_app: FastAPI,
    session: Session,
    monkeypatch,
) -> None:
    """Confirmed task creation should persist a household task."""

    from nexa_api import agent_service

    decision = AgentDecision(
        intent=AgentIntent.CREATE_TASK,
        confidence=0.99,
        task_title="Service the generator",
        task_description="Arrange generator maintenance.",
    )

    monkeypatch.setattr(
        agent_service,
        "resolve_agent_intent",
        lambda message: decision,
    )

    transport = ASGITransport(app=test_app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/agent",
            json={
                "message": "Create a task to service the generator",
                "confirm": True,
            },
        )

    assert response.status_code == 200

    body = response.json()

    assert body["intent"] == "create_task"
    assert body["requires_confirmation"] is False
    assert body["action_executed"] is True
    assert body["data"][0]["title"] == "Service the generator"

    tasks = list_tasks(session)

    assert len(tasks) == 1
    assert tasks[0].title == "Service the generator"


@pytest.mark.anyio
async def test_agent_complete_task_requires_confirmation(
    test_app: FastAPI,
    session: Session,
    monkeypatch,
) -> None:
    """Task completion should be proposed before execution."""

    from nexa_api import agent_service

    task = create_task(
        session,
        TaskCreate(
            title="Service the generator",
        ),
    )

    decision = AgentDecision(
        intent=AgentIntent.COMPLETE_TASK,
        confidence=0.99,
        target_task_title="Service the generator",
    )

    monkeypatch.setattr(
        agent_service,
        "resolve_agent_intent",
        lambda message: decision,
    )

    transport = ASGITransport(app=test_app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/agent",
            json={
                "message": "Mark service the generator as done."
            },
        )

    assert response.status_code == 200

    body = response.json()

    assert body["intent"] == "complete_task"
    assert body["requires_confirmation"] is True
    assert body["action_executed"] is False
    assert body["proposed_action"]["task_id"] == task.id

    session.refresh(task)

    assert task.status == TaskStatus.OPEN
    assert task.completed_at is None


@pytest.mark.anyio
async def test_agent_complete_task_executes_after_confirmation(
    test_app: FastAPI,
    session: Session,
    monkeypatch,
) -> None:
    """Confirmed task completion should persist the completed state."""

    from nexa_api import agent_service

    task = create_task(
        session,
        TaskCreate(
            title="Service the generator",
        ),
    )

    decision = AgentDecision(
        intent=AgentIntent.COMPLETE_TASK,
        confidence=0.99,
        target_task_title="Service the generator",
    )

    monkeypatch.setattr(
        agent_service,
        "resolve_agent_intent",
        lambda message: decision,
    )

    transport = ASGITransport(app=test_app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/agent",
            json={
                "message": "Mark service the generator as done.",
                "confirm": True,
            },
        )

    assert response.status_code == 200

    body = response.json()

    assert body["intent"] == "complete_task"
    assert body["requires_confirmation"] is False
    assert body["action_executed"] is True
    assert body["data"][0]["status"] == "completed"

    session.refresh(task)

    assert task.status == TaskStatus.COMPLETED
    assert task.completed_at is not None

@pytest.mark.anyio
async def test_agent_cancel_visitor_requires_confirmation(
    test_app: FastAPI,
    session: Session,
    monkeypatch,
) -> None:
    """Visitor cancellation should be proposed before execution."""

    from nexa_api import agent_service

    visitor = create_visitor(
        session,
        VisitorCreate(
            name="Ada Okafor",
            purpose="Electrical repair",
            expected_start=datetime(2030, 1, 1, 10, 0),
            expected_end=datetime(2030, 1, 1, 11, 0),
        ),
    )

    decision = AgentDecision(
        intent=AgentIntent.CANCEL_VISITOR,
        confidence=0.99,
        target_visitor_name="Ada Okafor",
    )

    monkeypatch.setattr(
        agent_service,
        "resolve_agent_intent",
        lambda message: decision,
    )

    transport = ASGITransport(app=test_app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/agent",
            json={
                "message": "Cancel Ada Okafor's visit."
            },
        )

    assert response.status_code == 200

    body = response.json()

    assert body["intent"] == "cancel_visitor"
    assert body["requires_confirmation"] is True
    assert body["action_executed"] is False
    assert body["proposed_action"]["visitor_id"] == visitor.id

    session.refresh(visitor)

    assert visitor.status == VisitorStatus.EXPECTED


@pytest.mark.anyio
async def test_agent_cancel_visitor_executes_after_confirmation(
    test_app: FastAPI,
    session: Session,
    monkeypatch,
) -> None:
    """Confirmed visitor cancellation should persist."""

    from nexa_api import agent_service

    visitor = create_visitor(
        session,
        VisitorCreate(
            name="Ada Okafor",
            purpose="Electrical repair",
            expected_start=datetime(2030, 1, 1, 10, 0),
            expected_end=datetime(2030, 1, 1, 11, 0),
        ),
    )

    decision = AgentDecision(
        intent=AgentIntent.CANCEL_VISITOR,
        confidence=0.99,
        target_visitor_name="Ada Okafor",
    )

    monkeypatch.setattr(
        agent_service,
        "resolve_agent_intent",
        lambda message: decision,
    )

    transport = ASGITransport(app=test_app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/agent",
            json={
                "message": "Cancel Ada Okafor's visit.",
                "confirm": True,
            },
        )

    assert response.status_code == 200

    body = response.json()

    assert body["intent"] == "cancel_visitor"
    assert body["requires_confirmation"] is False
    assert body["action_executed"] is True
    assert body["data"][0]["status"] == "cancelled"

    session.refresh(visitor)

    assert visitor.status == VisitorStatus.CANCELLED

@pytest.mark.anyio
async def test_agent_mark_visitor_arrived_requires_confirmation(
    test_app: FastAPI,
    session: Session,
    monkeypatch,
) -> None:
    """Visitor arrival should be proposed before execution."""

    from nexa_api import agent_service

    visitor = create_visitor(
        session,
        VisitorCreate(
            name="Ada Okafor",
            purpose="Electrical repair",
            expected_start=datetime(2030, 1, 1, 10, 0),
            expected_end=datetime(2030, 1, 1, 11, 0),
        ),
    )

    decision = AgentDecision(
        intent=AgentIntent.MARK_VISITOR_ARRIVED,
        confidence=0.99,
        target_visitor_name="Ada Okafor",
    )

    monkeypatch.setattr(
        agent_service,
        "resolve_agent_intent",
        lambda message: decision,
    )

    transport = ASGITransport(app=test_app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/agent",
            json={
                "message": "Ada Okafor has arrived."
            },
        )

    assert response.status_code == 200

    body = response.json()

    assert body["intent"] == "mark_visitor_arrived"
    assert body["requires_confirmation"] is True
    assert body["action_executed"] is False
    assert body["proposed_action"]["visitor_id"] == visitor.id

    session.refresh(visitor)

    assert visitor.status == VisitorStatus.EXPECTED
    assert visitor.arrived_at is None


@pytest.mark.anyio
async def test_agent_mark_visitor_arrived_executes_after_confirmation(
    test_app: FastAPI,
    session: Session,
    monkeypatch,
) -> None:
    """Confirmed visitor arrival should persist."""

    from nexa_api import agent_service

    visitor = create_visitor(
        session,
        VisitorCreate(
            name="Ada Okafor",
            purpose="Electrical repair",
            expected_start=datetime(2030, 1, 1, 10, 0),
            expected_end=datetime(2030, 1, 1, 11, 0),
        ),
    )

    decision = AgentDecision(
        intent=AgentIntent.MARK_VISITOR_ARRIVED,
        confidence=0.99,
        target_visitor_name="Ada Okafor",
    )

    monkeypatch.setattr(
        agent_service,
        "resolve_agent_intent",
        lambda message: decision,
    )

    transport = ASGITransport(app=test_app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/agent",
            json={
                "message": "Ada Okafor has arrived.",
                "confirm": True,
            },
        )

    assert response.status_code == 200

    body = response.json()

    assert body["intent"] == "mark_visitor_arrived"
    assert body["requires_confirmation"] is False
    assert body["action_executed"] is True
    assert body["data"][0]["status"] == "arrived"
    assert body["data"][0]["arrived_at"] is not None

    session.refresh(visitor)

    assert visitor.status == VisitorStatus.ARRIVED
    assert visitor.arrived_at is not None

@pytest.mark.anyio
async def test_agent_mark_visitor_departed_requires_confirmation(
    test_app: FastAPI,
    session: Session,
    monkeypatch,
) -> None:
    """Visitor departure should be proposed before execution."""

    from nexa_api import agent_service

    visitor = create_visitor(
        session,
        VisitorCreate(
            name="Chinedu Okafor",
            purpose="Generator inspection",
            expected_start=datetime(2030, 1, 2, 10, 0),
            expected_end=datetime(2030, 1, 2, 11, 0),
        ),
    )

    visitor = mark_visitor_arrived(
        session,
        visitor,
    )

    decision = AgentDecision(
        intent=AgentIntent.MARK_VISITOR_DEPARTED,
        confidence=0.99,
        target_visitor_name="Chinedu Okafor",
    )

    monkeypatch.setattr(
        agent_service,
        "resolve_agent_intent",
        lambda message: decision,
    )

    transport = ASGITransport(app=test_app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/agent",
            json={
                "message": "Chinedu Okafor has left."
            },
        )

    assert response.status_code == 200

    body = response.json()

    assert body["intent"] == "mark_visitor_departed"
    assert body["requires_confirmation"] is True
    assert body["action_executed"] is False
    assert body["proposed_action"]["visitor_id"] == visitor.id

    session.refresh(visitor)

    assert visitor.status == VisitorStatus.ARRIVED
    assert visitor.departed_at is None


@pytest.mark.anyio
async def test_agent_mark_visitor_departed_executes_after_confirmation(
    test_app: FastAPI,
    session: Session,
    monkeypatch,
) -> None:
    """Confirmed visitor departure should persist."""

    from nexa_api import agent_service

    visitor = create_visitor(
        session,
        VisitorCreate(
            name="Chinedu Okafor",
            purpose="Generator inspection",
            expected_start=datetime(2030, 1, 2, 10, 0),
            expected_end=datetime(2030, 1, 2, 11, 0),
        ),
    )

    visitor = mark_visitor_arrived(
        session,
        visitor,
    )

    decision = AgentDecision(
        intent=AgentIntent.MARK_VISITOR_DEPARTED,
        confidence=0.99,
        target_visitor_name="Chinedu Okafor",
    )

    monkeypatch.setattr(
        agent_service,
        "resolve_agent_intent",
        lambda message: decision,
    )

    transport = ASGITransport(app=test_app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/agent",
            json={
                "message": "Chinedu Okafor has left.",
                "confirm": True,
            },
        )

    assert response.status_code == 200

    body = response.json()

    assert body["intent"] == "mark_visitor_departed"
    assert body["requires_confirmation"] is False
    assert body["action_executed"] is True
    assert body["data"][0]["status"] == "departed"
    assert body["data"][0]["departed_at"] is not None

    session.refresh(visitor)

    assert visitor.status == VisitorStatus.DEPARTED
    assert visitor.departed_at is not None

@pytest.mark.anyio
async def test_agent_mark_delivery_collected_requires_confirmation(
    test_app: FastAPI,
    session: Session,
    monkeypatch,
) -> None:
    """Delivery collection should be proposed before execution."""

    from nexa_api import agent_service

    delivery = create_delivery(
        session,
        DeliveryCreate(
            description="MacBook Pro package",
            carrier="DHL",
            tracking_reference="NEXA-DHL-2030-001",
        ),
    )

    delivery = mark_delivery_delivered(
        session,
        delivery,
    )

    decision = AgentDecision(
        intent=AgentIntent.MARK_DELIVERY_COLLECTED,
        confidence=0.99,
        target_delivery_description="MacBook Pro package",
    )

    monkeypatch.setattr(
        agent_service,
        "resolve_agent_intent",
        lambda message: decision,
    )

    transport = ASGITransport(app=test_app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/agent",
            json={
                "message": "Mark the MacBook Pro package as collected."
            },
        )

    assert response.status_code == 200

    body = response.json()

    assert body["intent"] == "mark_delivery_collected"
    assert body["requires_confirmation"] is True
    assert body["action_executed"] is False
    assert body["proposed_action"]["delivery_id"] == delivery.id

    session.refresh(delivery)

    assert delivery.status == DeliveryStatus.DELIVERED
    assert delivery.collected_at is None


@pytest.mark.anyio
async def test_agent_mark_delivery_collected_executes_after_confirmation(
    test_app: FastAPI,
    session: Session,
    monkeypatch,
) -> None:
    """Confirmed delivery collection should persist."""

    from nexa_api import agent_service

    delivery = create_delivery(
        session,
        DeliveryCreate(
            description="MacBook Pro package",
            carrier="DHL",
            tracking_reference="NEXA-DHL-2030-001",
        ),
    )

    delivery = mark_delivery_delivered(
        session,
        delivery,
    )

    decision = AgentDecision(
        intent=AgentIntent.MARK_DELIVERY_COLLECTED,
        confidence=0.99,
        target_delivery_description="MacBook Pro package",
    )

    monkeypatch.setattr(
        agent_service,
        "resolve_agent_intent",
        lambda message: decision,
    )

    transport = ASGITransport(app=test_app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/agent",
            json={
                "message": "Mark the MacBook Pro package as collected.",
                "confirm": True,
            },
        )

    assert response.status_code == 200

    body = response.json()

    assert body["intent"] == "mark_delivery_collected"
    assert body["requires_confirmation"] is False
    assert body["action_executed"] is True
    assert body["data"][0]["status"] == "collected"
    assert body["data"][0]["collected_at"] is not None

    session.refresh(delivery)

    assert delivery.status == DeliveryStatus.COLLECTED
    assert delivery.collected_at is not None

@pytest.mark.anyio
async def test_agent_mark_delivery_delivered_requires_confirmation(
    test_app: FastAPI,
    session: Session,
    monkeypatch,
) -> None:
    """Delivery arrival should be proposed before execution."""

    from nexa_api import agent_service

    delivery = create_delivery(
        session,
        DeliveryCreate(
            description="Laptop automation package",
            carrier="DHL",
            tracking_reference="NEXA-MANUAL-003",
        ),
    )

    decision = AgentDecision(
        intent=AgentIntent.MARK_DELIVERY_DELIVERED,
        confidence=0.99,
        target_delivery_description="Laptop automation package",
    )

    monkeypatch.setattr(
        agent_service,
        "resolve_agent_intent",
        lambda message: decision,
    )

    transport = ASGITransport(app=test_app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/agent",
            json={
                "message": "The Laptop automation package has arrived."
            },
        )

    assert response.status_code == 200

    body = response.json()

    assert body["intent"] == "mark_delivery_delivered"
    assert body["requires_confirmation"] is True
    assert body["action_executed"] is False
    assert body["proposed_action"]["delivery_id"] == delivery.id

    session.refresh(delivery)

    assert delivery.status == DeliveryStatus.EXPECTED
    assert delivery.delivered_at is None


@pytest.mark.anyio
async def test_agent_mark_delivery_delivered_executes_after_confirmation(
    test_app: FastAPI,
    session: Session,
    monkeypatch,
) -> None:
    """Confirmed delivery arrival should persist."""

    from nexa_api import agent_service

    delivery = create_delivery(
        session,
        DeliveryCreate(
            description="Laptop automation package",
            carrier="DHL",
            tracking_reference="NEXA-MANUAL-003",
        ),
    )

    decision = AgentDecision(
        intent=AgentIntent.MARK_DELIVERY_DELIVERED,
        confidence=0.99,
        target_delivery_description="Laptop automation package",
    )

    monkeypatch.setattr(
        agent_service,
        "resolve_agent_intent",
        lambda message: decision,
    )

    transport = ASGITransport(app=test_app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/agent",
            json={
                "message": "The Laptop automation package has arrived.",
                "confirm": True,
            },
        )

    assert response.status_code == 200

    body = response.json()

    assert body["intent"] == "mark_delivery_delivered"
    assert body["requires_confirmation"] is False
    assert body["action_executed"] is True
    assert body["data"][0]["status"] == "delivered"
    assert body["data"][0]["delivered_at"] is not None

    session.refresh(delivery)

    assert delivery.status == DeliveryStatus.DELIVERED
    assert delivery.delivered_at is not None

@pytest.mark.anyio
async def test_agent_update_presence_requires_confirmation(
    test_app: FastAPI,
    session: Session,
    monkeypatch,
) -> None:
    """Presence updates should be proposed before execution."""

    from nexa_api import agent_service

    presence = create_presence(
        session,
        PresenceCreate(
            occupant_name="Obumneme",
            status=PresenceStatus.HOME,
            note="At home",
        ),
    )

    decision = AgentDecision(
        intent=AgentIntent.UPDATE_PRESENCE,
        confidence=0.99,
        target_occupant_name="Obumneme",
        target_presence_status="away",
    )

    monkeypatch.setattr(
        agent_service,
        "resolve_agent_intent",
        lambda message: decision,
    )

    transport = ASGITransport(app=test_app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/agent",
            json={
                "message": "Obumneme is leaving."
            },
        )

    assert response.status_code == 200

    body = response.json()

    assert body["intent"] == "update_presence"
    assert body["requires_confirmation"] is True
    assert body["action_executed"] is False
    assert body["proposed_action"]["presence_id"] == presence.id
    assert body["proposed_action"]["new_status"] == "away"

    session.refresh(presence)

    assert presence.status == PresenceStatus.HOME


@pytest.mark.anyio
async def test_agent_update_presence_executes_after_confirmation(
    test_app: FastAPI,
    session: Session,
    monkeypatch,
) -> None:
    """Confirmed presence updates should persist."""

    from nexa_api import agent_service

    presence = create_presence(
        session,
        PresenceCreate(
            occupant_name="Obumneme",
            status=PresenceStatus.HOME,
            note="At home",
        ),
    )

    decision = AgentDecision(
        intent=AgentIntent.UPDATE_PRESENCE,
        confidence=0.99,
        target_occupant_name="Obumneme",
        target_presence_status="away",
    )

    monkeypatch.setattr(
        agent_service,
        "resolve_agent_intent",
        lambda message: decision,
    )

    transport = ASGITransport(app=test_app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/agent",
            json={
                "message": "Obumneme is leaving.",
                "confirm": True,
            },
        )

    assert response.status_code == 200

    body = response.json()

    assert body["intent"] == "update_presence"
    assert body["requires_confirmation"] is False
    assert body["action_executed"] is True
    assert body["data"][0]["status"] == "away"

    session.refresh(presence)

    assert presence.status == PresenceStatus.AWAY

@pytest.mark.anyio
async def test_agent_creates_conversation_session(
    test_app: FastAPI,
) -> None:
    """A new agent request should create a conversation session."""

    transport = ASGITransport(app=test_app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/agent",
            json={
                "message": "Who is home?"
            },
        )

    assert response.status_code == 200

    body = response.json()

    assert body["session_id"] is not None
    assert body["session_id"] != ""


@pytest.mark.anyio
async def test_agent_reuses_existing_conversation_session(
    test_app: FastAPI,
) -> None:
    """A supplied session ID should be reused."""

    transport = ASGITransport(app=test_app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        first_response = await client.post(
            "/api/v1/agent",
            json={
                "message": "Who is home?"
            },
        )

        assert first_response.status_code == 200

        session_id = first_response.json()["session_id"]

        second_response = await client.post(
            "/api/v1/agent",
            json={
                "message": "What tasks are open?",
                "session_id": session_id,
            },
        )

    assert second_response.status_code == 200

    body = second_response.json()

    assert body["session_id"] == session_id


@pytest.mark.anyio
async def test_agent_persists_user_and_assistant_messages(
    test_app: FastAPI,
    session: Session,
) -> None:
    """Agent requests should persist both sides of the conversation."""

    from nexa_api.conversation_service import list_recent_messages

    transport = ASGITransport(app=test_app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/agent",
            json={
                "message": "Who is home?"
            },
        )

    assert response.status_code == 200

    body = response.json()
    session_id = body["session_id"]

    messages = list_recent_messages(
        session,
        session_id,
        limit=10,
    )

    assert len(messages) == 2

    assert messages[0].role == "user"
    assert messages[0].content == "Who is home?"

    assert messages[1].role == "assistant"
    assert messages[1].content == body["message"]


@pytest.mark.anyio
async def test_agent_rejects_unknown_conversation_session(
    test_app: FastAPI,
) -> None:
    """Unknown conversation IDs should return 404."""

    transport = ASGITransport(app=test_app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/agent",
            json={
                "message": "Who is home?",
                "session_id": "missing-conversation-session",
            },
        )

    assert response.status_code == 404

    body = response.json()

    assert body["detail"] == "Conversation session not found."

@pytest.mark.anyio
async def test_agent_reuses_history_across_requests(
    test_app: FastAPI,
    monkeypatch,
) -> None:
    """A follow-up request should receive prior conversation history."""

    from nexa_api import agent_service

    captured_history: list[dict[str, str]] | None = None

    def fake_resolver(
        message: str,
        history: list[dict[str, str]] | None = None,
    ) -> AgentDecision:
        nonlocal captured_history
        captured_history = history

        return AgentDecision(
            intent=AgentIntent.UNKNOWN,
            confidence=0.0,
        )

    monkeypatch.setattr(
        agent_service,
        "resolve_agent_intent",
        fake_resolver,
    )

    transport = ASGITransport(app=test_app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        first_response = await client.post(
            "/api/v1/agent",
            json={
                "message": "Who is coming today?"
            },
        )

        assert first_response.status_code == 200

        session_id = first_response.json()["session_id"]

        second_response = await client.post(
            "/api/v1/agent",
            json={
                "message": "Has she arrived?",
                "session_id": session_id,
            },
        )

    assert second_response.status_code == 200

    assert captured_history is not None
    assert len(captured_history) == 2

    assert captured_history[0]["role"] == "user"
    assert captured_history[0]["content"] == "Who is coming today?"

    assert captured_history[1]["role"] == "assistant"
    assert captured_history[1]["content"] == first_response.json()["message"]

@pytest.mark.anyio
@pytest.mark.anyio
async def test_agent_resolves_follow_up_reference_from_history(
    test_app: FastAPI,
    session: Session,
    monkeypatch,
) -> None:
    """A follow-up request should resolve a prior entity from history."""

    from nexa_api import agent_service

    visitor = create_visitor(
        session,
        VisitorCreate(
            name="Ada Okafor",
            purpose="Electrical repair",
            expected_start=datetime(2030, 1, 1, 10, 0),
            expected_end=datetime(2030, 1, 1, 11, 0),
        ),
    )

    call_count = 0

    def fake_resolver(
        message: str,
        history: list[dict[str, str]] | None = None,
    ) -> AgentDecision:
        nonlocal call_count
        call_count += 1

        if call_count == 1:
            return AgentDecision(
                intent=AgentIntent.UNKNOWN,
                confidence=0.0,
            )

        assert history is not None
        assert history[0]["role"] == "user"
        assert history[0]["content"] == "Who is coming today?"

        assert history[1]["role"] == "assistant"

        return AgentDecision(
            intent=AgentIntent.MARK_VISITOR_ARRIVED,
            confidence=0.99,
            target_visitor_name="Ada Okafor",
        )

    monkeypatch.setattr(
        agent_service,
        "resolve_agent_intent",
        fake_resolver,
    )

    transport = ASGITransport(app=test_app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        first_response = await client.post(
            "/api/v1/agent",
            json={
                "message": "Who is coming today?"
            },
        )

        assert first_response.status_code == 200

        session_id = first_response.json()["session_id"]

        second_response = await client.post(
            "/api/v1/agent",
            json={
                "message": "Has she arrived?",
                "session_id": session_id,
            },
        )

    assert second_response.status_code == 200

    body = second_response.json()

    assert body["intent"] == AgentIntent.MARK_VISITOR_ARRIVED.value
    assert body["requires_confirmation"] is True
    assert body["action_executed"] is False

    session.refresh(visitor)

    assert visitor.status == VisitorStatus.EXPECTED

@pytest.mark.anyio
async def test_agent_first_person_presence_update_requires_confirmation(
    test_app: FastAPI,
    session: Session,
    monkeypatch,
) -> None:
    """First-person presence updates should require confirmation through the API."""

    from nexa_api import agent_service

    presence = HouseholdPresence(
        occupant_name="Obumneme",
        status=PresenceStatus.AWAY,
    )

    session.add(presence)
    session.commit()
    session.refresh(presence)

    decision = AgentDecision(
        intent=AgentIntent.UPDATE_PRESENCE,
        confidence=0.99,
        target_occupant_name="Obumneme",
        target_presence_status="home",
    )

    def fake_resolver(
        message: str,
        history: list[dict[str, str]] | None = None,
        speaker_name: str | None = None,
    ) -> AgentDecision:
        assert message == "I'm home."
        assert speaker_name == "Obumneme"
        return decision

    monkeypatch.setattr(
        agent_service,
        "resolve_agent_intent",
        fake_resolver,
    )

    transport = ASGITransport(app=test_app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/agent",
            json={
                "message": "I'm home.",
                "speaker_name": "Obumneme",
            },
        )

    assert response.status_code == 200

    body = response.json()

    assert body["intent"] == AgentIntent.UPDATE_PRESENCE.value
    assert body["requires_confirmation"] is True
    assert body["action_executed"] is False

    session.refresh(presence)

    assert presence.status == PresenceStatus.AWAY


@pytest.mark.anyio
async def test_agent_confirmed_first_person_presence_update_executes(
    test_app: FastAPI,
    session: Session,
    monkeypatch,
) -> None:
    """Confirmed first-person presence updates should execute through the API."""

    from nexa_api import agent_service

    presence = HouseholdPresence(
        occupant_name="Obumneme",
        status=PresenceStatus.AWAY,
    )

    session.add(presence)
    session.commit()
    session.refresh(presence)

    decision = AgentDecision(
        intent=AgentIntent.UPDATE_PRESENCE,
        confidence=0.99,
        target_occupant_name="Obumneme",
        target_presence_status="home",
    )

    def fake_resolver(
        message: str,
        history: list[dict[str, str]] | None = None,
        speaker_name: str | None = None,
    ) -> AgentDecision:
        assert message == "I'm home."
        assert speaker_name == "Obumneme"
        return decision

    monkeypatch.setattr(
        agent_service,
        "resolve_agent_intent",
        fake_resolver,
    )

    transport = ASGITransport(app=test_app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/agent",
            json={
                "message": "I'm home.",
                "speaker_name": "Obumneme",
                "confirm": True,
            },
        )

    assert response.status_code == 200

    body = response.json()

    assert body["intent"] == AgentIntent.UPDATE_PRESENCE.value
    assert body["requires_confirmation"] is False
    assert body["action_executed"] is True

    session.refresh(presence)

    assert presence.status == PresenceStatus.HOME