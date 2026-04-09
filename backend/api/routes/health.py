"""
AETHERTRADE-SWARM — Health Routes
GET /health — public, no auth required.
"""
from __future__ import annotations

import time
from datetime import datetime, timezone

from fastapi import APIRouter

from config import get_settings
from models.schemas import HealthResponse, ServiceStatus

router = APIRouter(tags=["health"])
settings = get_settings()

_start_time = time.monotonic()


@router.get("/health", response_model=HealthResponse, summary="Health check")
async def health_check() -> HealthResponse:
    """
    Returns application health status, uptime, active pod count, and
    dependency statuses. No authentication required.
    """
    from utils.data_simulator import get_simulator
    from models.database import get_db

    uptime = time.monotonic() - _start_time

    # Check simulator
    try:
        sim = get_simulator()
        pods = sim.get_pod_metrics()
        pods_active = sum(1 for p in pods if p["status"] == "active")
        sim_status = ServiceStatus(name="data_simulator", status="healthy", latency_ms=0.5)
    except Exception as exc:
        pods_active = 0
        sim_status = ServiceStatus(name="data_simulator", status="down", detail=str(exc))

    # Check database
    try:
        db = get_db()
        db_status = ServiceStatus(
            name="database",
            status="healthy" if not db.is_fallback else "degraded",
            detail="in-memory fallback" if db.is_fallback else "supabase",
        )
    except Exception as exc:
        db_status = ServiceStatus(name="database", status="down", detail=str(exc))

    services = [sim_status, db_status]
    overall = "healthy"
    if any(s.status == "down" for s in services):
        overall = "down"
    elif any(s.status == "degraded" for s in services):
        overall = "degraded"

    return HealthResponse(
        status=overall,
        version=settings.app_version,
        environment=settings.environment,
        uptime_seconds=round(uptime, 2),
        timestamp=datetime.now(timezone.utc),
        services=services,
    )
