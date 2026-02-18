from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager, suppress
from typing import Optional

from fastapi import Depends, FastAPI
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session, sessionmaker

from apps.backend.api.router import router as api_router
from apps.backend.auth.dependencies import get_current_principal
from apps.backend.auth.router import router as auth_router
from apps.backend.database import create_session_factory
from apps.backend.rate_limit.middleware import RateLimitMiddleware
from apps.backend.rate_limit.redis_storage import (
    InMemorySlidingWindowStorage,
    RedisSlidingWindowStorage,
)
from apps.backend.realtime.applications_stream import (
    ApplicationsRealtimeHub,
    ApplicationsRealtimeProjector,
)
from apps.backend.realtime.router import router as realtime_router
from apps.backend.security.pii_redaction import install_pii_redaction_filter
from apps.backend.settings import Settings
from src.applications.shared.domain.errors import ApplicationError, ValidationError
from src.auth.shared.domain.errors import AuthError

logger = logging.getLogger(__name__)


def create_app(
    settings: Optional[Settings] = None,
    session_factory: Optional[sessionmaker[Session]] = None,
    rate_limit_storage: Optional[object] = None,
) -> FastAPI:
    install_pii_redaction_filter()
    runtime_settings = settings or Settings.from_env()
    runtime_settings.validate_required()

    @asynccontextmanager
    async def app_lifespan(app: FastAPI):
        if runtime_settings.applications_realtime_enabled:
            projector = ApplicationsRealtimeProjector(
                session_factory=app.state.session_factory,
                hub=app.state.applications_realtime_hub,
                poll_interval_ms=runtime_settings.applications_realtime_poll_interval_ms,
            )
            projector_task = asyncio.create_task(
                projector.run(),
                name="applications-realtime-projector",
            )
            app.state.applications_realtime_projector = projector
            app.state.applications_realtime_projector_task = projector_task

        try:
            yield
        finally:
            projector = app.state.applications_realtime_projector
            projector_task = app.state.applications_realtime_projector_task
            if projector is not None:
                projector.stop()
            if projector_task is not None:
                projector_task.cancel()
                with suppress(asyncio.CancelledError):
                    await projector_task
            app.state.applications_realtime_projector = None
            app.state.applications_realtime_projector_task = None

    app = FastAPI(title="Credit Applications Hub API", lifespan=app_lifespan)
    app.state.settings = runtime_settings
    app.state.session_factory = session_factory or create_session_factory(runtime_settings.database_url)
    if rate_limit_storage is not None:
        app.state.rate_limit_storage = rate_limit_storage
    elif runtime_settings.rate_limit_enabled:
        app.state.rate_limit_storage = RedisSlidingWindowStorage(runtime_settings.rate_limit_redis_url)
    else:
        app.state.rate_limit_storage = InMemorySlidingWindowStorage()
    app.state.applications_realtime_hub = ApplicationsRealtimeHub()
    app.state.applications_realtime_projector = None
    app.state.applications_realtime_projector_task = None

    app.add_middleware(
        RateLimitMiddleware,
        settings=runtime_settings,
        storage=app.state.rate_limit_storage,
    )

    @app.exception_handler(AuthError)
    async def auth_error_handler(request, exc: AuthError) -> JSONResponse:
        # Login failures are already logged in auth.router with email fingerprints.
        if not (request.url.path == "/auth/login" and exc.code in {"INVALID_CREDENTIALS", "USER_INACTIVE"}):
            logger.warning(
                "auth_error",
                extra={
                    "auth": {
                        "code": exc.code,
                        "path": request.url.path,
                        "method": request.method,
                        "ip_address": request.client.host if request.client else None,
                    }
                },
            )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "code": exc.code,
                "message": exc.message,
            },
        )

    @app.exception_handler(ApplicationError)
    async def application_error_handler(_request, exc: ApplicationError) -> JSONResponse:
        response_content: dict[str, object] = {
            "code": exc.code,
            "message": exc.message,
        }
        if isinstance(exc, ValidationError):
            response_content["errors"] = [
                {
                    "field": error.field,
                    "code": error.code,
                    "message": error.message,
                }
                for error in exc.errors
            ]

        return JSONResponse(
            status_code=exc.status_code,
            content=response_content,
        )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(auth_router)
    app.include_router(realtime_router, prefix="/api")
    app.include_router(
        api_router,
        prefix="/api",
        dependencies=[Depends(get_current_principal)],
    )

    return app


def get_app() -> FastAPI:
    return create_app()


try:
    app = create_app()
except RuntimeError as exc:
    startup_error_message = str(exc)
    logger.error("app_configuration_error", extra={"error": startup_error_message})

    @asynccontextmanager
    async def _error_lifespan(_app: FastAPI):
        raise RuntimeError(startup_error_message)
        yield

    app = FastAPI(title="Credit Applications Hub API", lifespan=_error_lifespan)
