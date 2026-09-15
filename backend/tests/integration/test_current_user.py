import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete

from agent_studio.bootstrap.api import create_app
from agent_studio.platform.database import get_session_factory
from agent_studio.platform.settings import Settings, get_settings
from agent_studio.platform.users.persistence import AppUserModel

pytestmark = [pytest.mark.integration, pytest.mark.anyio]


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


async def test_me_provisions_one_user_for_stable_identity() -> None:
    subject = f"integration-{uuid.uuid4()}"
    settings = Settings(
        environment="test",
        development_auth_subject=subject,
        development_auth_email=f"{subject}@example.com",
    )
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: settings
    transport = ASGITransport(app=app)

    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            first = await client.get("/api/v1/me")
            second = await client.get("/api/v1/me")

        assert first.status_code == 200
        assert second.status_code == 200
        assert first.json() == second.json()
        assert first.json()["subject"] == subject
    finally:
        with get_session_factory().begin() as session:
            session.execute(
                delete(AppUserModel).where(AppUserModel.auth_subject == subject)
            )
