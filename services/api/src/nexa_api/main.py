"""Main FastAPI application for Nexa."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Literal

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from nexa_api.agent_routes import router as agent_router
from nexa_api.config import get_settings
from nexa_api.delivery_routes import router as delivery_router
from nexa_api.event_routes import router as event_router
from nexa_api.mcp_server import build_mcp_app, mcp
from nexa_api.presence_routes import router as presence_router
from nexa_api.simulator_routes import router as simulator_router
from nexa_api.simulator_ui import router as simulator_ui_router
from nexa_api.task_routes import router as task_router
from nexa_api.visitor_routes import router as visitor_router

settings = get_settings()


class HealthResponse(BaseModel):
    """Response returned by the Nexa health endpoint."""

    status: Literal["ok"]
    service: str
    version: str
    environment: str
    timestamp: datetime


# Important:
# Build the MCP ASGI application before the FastAPI lifespan starts.
#
# Calling build_mcp_app() creates mcp.session_manager, which the
# parent FastAPI application must start in its own lifespan.
mcp_app = build_mcp_app()


@asynccontextmanager
async def lifespan(
    app: FastAPI,
) -> AsyncIterator[None]:
    """Manage Nexa application-level services."""

    async with mcp.session_manager.run():
        yield


app = FastAPI(
    title=settings.app_name,
    description="Household intelligence and automation API for Nexa.",
    version=settings.api_version,
    lifespan=lifespan,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.web_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Mcp-Session-Id"],
)


app.include_router(task_router)
app.include_router(visitor_router)
app.include_router(delivery_router)
app.include_router(presence_router)
app.include_router(event_router)
app.include_router(agent_router)
app.include_router(simulator_router)
app.include_router(simulator_ui_router)


@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["system"],
)
def health() -> HealthResponse:
    """Report whether the Nexa API is running."""

    return HealthResponse(
        status="ok",
        service=settings.app_name,
        version=settings.api_version,
        environment=settings.environment,
        timestamp=datetime.now(UTC),
    )


# Keep this mount last.
#
# build_mcp_app() uses streamable_http_path="/", so mounting it here
# exposes the MCP Streamable HTTP endpoint as /mcp.
app.mount(
    "/mcp",
    mcp_app,
    name="mcp",
)