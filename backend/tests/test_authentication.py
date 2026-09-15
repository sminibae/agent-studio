import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient
from pydantic import SecretStr

from agent_studio.bootstrap.api import create_app
from agent_studio.platform.identity.authentication import (
    resolve_authenticated_identity,
)
from agent_studio.platform.settings import Settings, get_settings


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def test_development_identity_ignores_untrusted_headers() -> None:
    settings = Settings(environment="development")

    identity = resolve_authenticated_identity(
        settings=settings,
        proxy_token="attacker-token",
        issuer="https://attacker.example",
        subject="attacker",
        email="attacker@example.com",
        display_name=None,
    )

    assert identity.issuer == settings.development_auth_issuer
    assert identity.subject == settings.development_auth_subject


def test_production_identity_requires_trusted_proxy_credential() -> None:
    settings = Settings(
        environment="production",
        proxy_shared_secret=SecretStr("expected-token"),
        allowed_auth_issuer="https://accounts.example.com",
        allowed_auth_subject="allowed-subject",
    )

    with pytest.raises(HTTPException) as raised:
        resolve_authenticated_identity(
            settings=settings,
            proxy_token="wrong-token",
            issuer="https://accounts.example.com",
            subject="allowed-subject",
            email="developer@example.com",
            display_name="Developer",
        )

    assert raised.value.status_code == 401


def test_production_identity_enforces_subject_allowlist() -> None:
    settings = Settings(
        environment="production",
        proxy_shared_secret=SecretStr("expected-token"),
        allowed_auth_issuer="https://accounts.example.com",
        allowed_auth_subject="allowed-subject",
    )

    with pytest.raises(HTTPException) as raised:
        resolve_authenticated_identity(
            settings=settings,
            proxy_token="expected-token",
            issuer="https://accounts.example.com",
            subject="other-subject",
            email="other@example.com",
            display_name=None,
        )

    assert raised.value.status_code == 401


def test_production_identity_accepts_allowlisted_issuer_and_subject() -> None:
    settings = Settings(
        environment="production",
        proxy_shared_secret=SecretStr("expected-token"),
        allowed_auth_issuer="https://accounts.example.com",
        allowed_auth_subject="allowed-subject",
    )

    identity = resolve_authenticated_identity(
        settings=settings,
        proxy_token="expected-token",
        issuer="https://accounts.example.com",
        subject="allowed-subject",
        email="developer@example.com",
        display_name="Developer",
    )

    assert identity.subject == "allowed-subject"


@pytest.mark.anyio
async def test_me_returns_json_401_without_proxy_credential() -> None:
    settings = Settings(
        environment="production",
        proxy_shared_secret=SecretStr("expected-token"),
        allowed_auth_issuer="https://accounts.example.com",
        allowed_auth_subject="allowed-subject",
    )
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: settings
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/me")

    assert response.status_code == 401
    assert response.json()["error"]["type"] == "unauthorized"
    assert response.json()["error"]["request_id"] == response.headers["X-Request-ID"]
