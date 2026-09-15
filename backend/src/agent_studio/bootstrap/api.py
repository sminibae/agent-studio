from fastapi import FastAPI

from agent_studio import __version__
from agent_studio.platform.health.http import router as health_router
from agent_studio.platform.identity.http import router as identity_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="Agent Studio API",
        version=__version__,
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
    )
    app.include_router(health_router, prefix="/api/v1")
    app.include_router(identity_router, prefix="/api/v1")
    return app


app = create_app()
