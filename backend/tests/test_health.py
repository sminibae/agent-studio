import pytest
from httpx import ASGITransport, AsyncClient

from agent_studio.bootstrap.api import create_app

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


async def test_liveness_reports_service_version() -> None:
    transport = ASGITransport(app=create_app())
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health/live")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "agent-studio-api",
        "version": "0.1.0",
    }


async def test_readiness_reports_database_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_database_check() -> None:
        raise RuntimeError("connection refused")

    monkeypatch.setattr(
        "agent_studio.platform.health.http.check_database",
        fail_database_check,
    )
    transport = ASGITransport(app=create_app())

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health/ready")

    assert response.status_code == 503
    assert response.json() == {"detail": "database unavailable"}
