"""Application factory.

`create_app(settings)` builds an isolated app (own DB engine, own rate limiter), which keeps tests
independent and avoids hidden global state.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import __version__
from app.api import (
    admin,
    admin_platform,
    auth,
    health,
    progress,
    simulation,
    specializations,
    teach,
    users,
)
from app.core.config import Settings, get_settings
from app.db.session import Database
from app.security.headers import SecurityHeadersMiddleware
from app.security.rate_limit import SlidingWindowRateLimiter

logger = logging.getLogger("bridge")


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        yield
        app.state.db.dispose()

    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        lifespan=lifespan,
        # Interactive docs are useful in development but are not exposed in production.
        docs_url=None if settings.is_production else "/docs",
        redoc_url=None,
        openapi_url=None if settings.is_production else "/openapi.json",
    )
    app.state.settings = settings
    app.state.db = Database(settings.database_url, echo=settings.database_echo)
    app.state.auth_rate_limiter = SlidingWindowRateLimiter(
        settings.auth_rate_limit_attempts, settings.auth_rate_limit_window_seconds
    )

    app.add_middleware(SecurityHeadersMiddleware, hsts=settings.is_production)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "Idempotency-Key"],
    )

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        # Never leak stack traces or internal details to clients.
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})

    app.include_router(health.router)
    api = APIRouter(prefix=settings.api_prefix)
    for module in (
        auth,
        users,
        specializations,
        admin,
        admin_platform,
        simulation,
        progress,
        teach,
    ):
        api.include_router(module.router)
    app.include_router(api)
    return app


# Run with:  uvicorn app.main:create_app --factory --reload
