"""Serve the Nexa Alexa+ simulator interface."""

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse

router = APIRouter(
    tags=["simulator-ui"],
)


SIMULATOR_HTML = (
    Path(__file__).resolve().parent
    / "static"
    / "simulator.html"
)


@router.get(
    "/simulator",
    include_in_schema=False,
)
def simulator_page() -> FileResponse:
    """Return the Alexa+ style Nexa simulator."""

    return FileResponse(SIMULATOR_HTML)