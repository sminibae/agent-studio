import secrets
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status

from agent_studio.platform.identity.domain import AuthenticatedIdentity
from agent_studio.platform.settings import Settings, get_settings


def _unauthorized(message: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=message)


def resolve_authenticated_identity(
    *,
    settings: Settings,
    proxy_token: str | None,
    issuer: str | None,
    subject: str | None,
    email: str | None,
    display_name: str | None,
) -> AuthenticatedIdentity:
    if settings.environment in {"development", "test"}:
        return AuthenticatedIdentity(
            issuer=settings.development_auth_issuer,
            subject=settings.development_auth_subject,
            email=settings.development_auth_email,
            display_name=settings.development_auth_name,
        )

    expected_token = settings.proxy_shared_secret
    if expected_token is None or proxy_token is None:
        raise _unauthorized("trusted proxy credential required")
    if not secrets.compare_digest(proxy_token, expected_token.get_secret_value()):
        raise _unauthorized("trusted proxy credential required")
    if not issuer or not subject or not email:
        raise _unauthorized("complete proxy identity required")
    if (
        settings.allowed_auth_issuer != issuer
        or settings.allowed_auth_subject != subject
    ):
        raise _unauthorized("identity is not allowed")

    return AuthenticatedIdentity(
        issuer=issuer,
        subject=subject,
        email=email,
        display_name=display_name,
    )


def authenticate_identity(
    settings: Annotated[Settings, Depends(get_settings)],
    proxy_token: Annotated[
        str | None, Header(alias="X-Agent-Studio-Proxy-Token")
    ] = None,
    issuer: Annotated[str | None, Header(alias="X-Agent-Studio-Auth-Issuer")] = None,
    subject: Annotated[str | None, Header(alias="X-Agent-Studio-Auth-Subject")] = None,
    email: Annotated[str | None, Header(alias="X-Agent-Studio-Auth-Email")] = None,
    display_name: Annotated[
        str | None, Header(alias="X-Agent-Studio-Auth-Name")
    ] = None,
) -> AuthenticatedIdentity:
    return resolve_authenticated_identity(
        settings=settings,
        proxy_token=proxy_token,
        issuer=issuer,
        subject=subject,
        email=email,
        display_name=display_name,
    )
