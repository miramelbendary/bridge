from __future__ import annotations

import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app import __version__

router = APIRouter(tags=["health"])
logger = logging.getLogger("bridge.health")


@router.get("/health")
def liveness() -> dict:
    """The process is up. Does not touch the database."""
    return {"status": "ok", "version": __version__}


@router.get("/health/ready")
def readiness(request: Request) -> JSONResponse:
    """The process can serve traffic: the database is reachable."""
    try:
        request.app.state.db.ping()
    except Exception:
        logger.exception("Database readiness check failed")
        return JSONResponse(status_code=503, content={"status": "unavailable", "database": "down"})
    return JSONResponse(content={"status": "ok", "database": "up"})
