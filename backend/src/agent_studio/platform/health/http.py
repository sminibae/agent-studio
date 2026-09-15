from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

from agent_studio import __version__

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
