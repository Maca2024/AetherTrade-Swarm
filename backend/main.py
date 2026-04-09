"""
AETHERTRADE-SWARM — FastAPI Application Entry Point
16-agent AI trading platform backend.

Run with:
    uvicorn main:app --reload --port 8888
"""
from __future__ import annotations

import logging
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import get_settings
from models.schemas import ErrorDetail, ErrorResponse

settings = get_settings()

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
)
logger = logging.getLogger("oracle.main")


# ---------------------------------------------------------------------------
# Lifespan — startup / shutdown
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # --- Startup ---
    logger.info("AETHERTRADE-SWARM starting up (env=%s)", settings.environment)

    # Init database client
    from models.database import init_db
    db = init_db(settings.supabase_url, settings.supabase_key)
    logger.info("Database client ready (fallback=%s)", db.is_fallback)

    # Init data simulator (2-year history pre-computed at startup)
    from utils.data_simulator import init_simulator
    sim = init_simulator(seed=settings.simulation_seed)
    logger.info("Data simulator ready (seed=%d, nav=%.2f)", settings.simulation_seed, sim._nav)

    # Seed a default dev API key so the app is usable immediately
    from api.auth import create_api_key
    from models.schemas import KeyTier
    _raw, _record = create_api_key(
        name="dev-default",
        tier=KeyTier.ENTERPRISE,
        owner_email="dev@aethertrade-swarm.io",
        description="Auto-generated dev key — replace in production",
    )
    logger.info(
        "Dev API key created: prefix=%s  raw_key=%s  (REPLACE IN PRODUCTION)",
        _record["prefix"],
        _raw,
    )

    yield

    # --- Shutdown ---
    logger.info("AETHERTRADE-SWARM shutting down.")


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "AETHERTRADE-SWARM — 16-agent AI trading platform. "
        "9 strategy pods, HMM regime detection, Bayesian portfolio optimiser, "
        "Kelly/Black-Litterman sizing, 4-layer risk management."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Exception handlers
# ---------------------------------------------------------------------------

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Unhandled exception on %s %s: %s", request.method, request.url.path, exc, exc_info=True)
    body = ErrorResponse(
        error=ErrorDetail(
            code="INTERNAL_SERVER_ERROR",
            message="An unexpected error occurred.",
            detail=str(exc) if settings.debug else None,
            timestamp=datetime.now(timezone.utc),
        )
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=body.model_dump(mode="json"),
    )


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    body = ErrorResponse(
        error=ErrorDetail(
            code="VALIDATION_ERROR",
            message=str(exc),
            timestamp=datetime.now(timezone.utc),
        )
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=body.model_dump(mode="json"),
    )


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

from api.routes.health import router as health_router
from api.routes.regime import router as regime_router
from api.routes.strategies import router as strategies_router
from api.routes.signals import router as signals_router
from api.routes.portfolio import router as portfolio_router
from api.routes.risk import router as risk_router
from api.routes.keys import router as keys_router
from api.routes.chat import router as chat_router
from api.routes.market_data import router as market_data_router

app.include_router(health_router)
app.include_router(regime_router)
app.include_router(strategies_router)
app.include_router(signals_router)
app.include_router(portfolio_router)
app.include_router(risk_router)
app.include_router(keys_router)
app.include_router(chat_router)
app.include_router(market_data_router)


# ---------------------------------------------------------------------------
# Root endpoint
# ---------------------------------------------------------------------------

@app.get("/", tags=["root"], summary="App info")
async def root() -> dict:
    """
    Returns basic application metadata. No authentication required.
    """
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "docs": "/docs",
        "health": "/health",
        "endpoints": {
            "regime": "/api/v1/regime",
            "strategies": "/api/v1/strategies",
            "signals": "/api/v1/signals/combined",
            "portfolio": "/api/v1/portfolio",
            "risk": "/api/v1/risk",
            "keys": "/api/v1/keys",
        },
    }
