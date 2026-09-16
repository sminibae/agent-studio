from typing import Literal

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from agent_studio import __version__
from agent_studio.platform.database import check_database

router = APIRouter(prefix="/health", tags=["health"])


class LiveResponse(BaseModel):
    status: Literal["ok"]
    service: Literal["agent-studio-api"]
    version: str


@router.get("/live", response_model=LiveResponse)
def liveness() -> LiveResponse:
    return LiveResponse(
        status="ok",
        service="agent-studio-api",
        version=__version__,
    )


@router.get("/ready", response_model=LiveResponse)
def readiness() -> LiveResponse:
    try:
        check_database()
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="database unavailable",
        ) from error
    return liveness()
