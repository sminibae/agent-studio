import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from agent_studio.platform.identity.application import resolve_current_user
from agent_studio.platform.identity.authentication import authenticate_identity
from agent_studio.platform.identity.domain import AuthenticatedIdentity
from agent_studio.platform.identity.persistence import SqlAlchemyUserProvisioner

router = APIRouter(tags=["identity"])


class CurrentUserResponse(BaseModel):
    id: uuid.UUID
    issuer: str
    subject: str
    email: str
    display_name: str | None


@router.get("/me", response_model=CurrentUserResponse)
def get_current_user(
    identity: Annotated[AuthenticatedIdentity, Depends(authenticate_identity)],
) -> CurrentUserResponse:
    user = resolve_current_user(identity, SqlAlchemyUserProvisioner())
    return CurrentUserResponse(
        id=user.id,
        issuer=user.issuer,
        subject=user.subject,
        email=user.email,
        display_name=user.display_name,
    )
