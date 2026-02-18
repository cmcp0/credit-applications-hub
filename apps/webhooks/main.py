from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI
from sqlalchemy.orm import Session, sessionmaker

from apps.backend.database import create_session_factory
from apps.backend.settings import Settings
from apps.webhooks.ingress.router import router as ingress_router


def create_webhooks_app(
    settings: Optional[Settings] = None,
    session_factory: Optional[sessionmaker[Session]] = None,
) -> FastAPI:
    runtime_settings = settings or Settings.from_env()

    app = FastAPI(title="Credit Applications Hub Webhooks")
    app.state.settings = runtime_settings
    app.state.session_factory = session_factory or create_session_factory(runtime_settings.database_url)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(ingress_router, prefix="/webhooks")
    return app


def get_app() -> FastAPI:
    return create_webhooks_app()


try:
    app = create_webhooks_app()
except RuntimeError as exc:
    startup_error_message = str(exc)

    @asynccontextmanager
    async def _error_lifespan(_app: FastAPI):
        raise RuntimeError(startup_error_message)
        yield

    app = FastAPI(title="Credit Applications Hub Webhooks", lifespan=_error_lifespan)

