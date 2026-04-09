"""
AetherTrade-Swarm — Backtest API Routes
  POST /api/v1/backtest         — Run a backtest with custom parameters
  GET  /api/v1/backtest/latest  — Get the latest backtest results from disk
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from pydantic import BaseModel, Field

logger = logging.getLogger("aethertrade.api.backtest")

router = APIRouter(prefix="/api/v1/backtest", tags=["backtest"])

RESULTS_FILE = Path(__file__).resolve().parent.parent.parent / "backtest" / "results" / "backtest_results.json"

# In-memory cache for running jobs
_running_jobs: dict[str, dict[str, Any]] = {}


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class BacktestRunRequest(BaseModel):
    start_date: str = Field(
        default="2025-04-08",
        description="Backtest start date (YYYY-MM-DD)",
    )
    end_date: str = Field(
        default="2026-04-07",
        description="Backtest end date (YYYY-MM-DD)",
    )
    initial_capital: float = Field(
        default=5_000.0,
        ge=1_000.0,
        le=10_000_000.0,
        description="Starting capital in USD",
    )
    leverage: float = Field(
        default=3.0,
        ge=1.0,
        le=10.0,
        description="Leverage multiplier",
    )
    universe: list[str] = Field(
        default=["SPY", "QQQ", "AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA", "GLD", "TLT"],
        description="List of ticker symbols to include",
        min_length=2,
        max_length=30,
    )


class BacktestJobResponse(BaseModel):
    job_id: str
    status: str = Field(description="queued | running | done | error")
    message: str
    submitted_at: str
    results_url: str | None = None


class BacktestSummaryResponse(BaseModel):
    run_id: str
    start_date: str
    end_date: str
    initial_capital: float
    final_nav: float
    total_return: float
    annualized_return: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    win_rate: float
    total_trades: int
    regime_breakdown: dict[str, float]
    generated_at: str


# ---------------------------------------------------------------------------
# Background job runner
# ---------------------------------------------------------------------------

def _run_backtest_job(job_id: str, req: BacktestRunRequest) -> None:
    """Executed in a background thread via FastAPI BackgroundTasks."""
    _running_jobs[job_id]["status"] = "running"
    try:
        from backtest.engine import BacktestEngine

        start = date.fromisoformat(req.start_date)
        end = date.fromisoformat(req.end_date)

        engine = BacktestEngine(
            start=start,
            end=end,
            initial_capital=req.initial_capital,
            leverage=req.leverage,
            universe=req.universe,
        )

        results = engine.run()

        results_dict: dict[str, Any] = {
            "run_id": results.run_id,
            "job_id": job_id,
            "start_date": results.start_date,
            "end_date": results.end_date,
            "initial_capital": results.initial_capital,
            "leverage": req.leverage,
            "universe": req.universe,
            "final_nav": results.final_nav,
            "total_return": results.total_return,
            "annualized_return": results.annualized_return,
            "sharpe_ratio": results.sharpe_ratio,
            "sortino_ratio": results.sortino_ratio,
            "calmar_ratio": results.calmar_ratio,
            "max_drawdown": results.max_drawdown,
            "win_rate": results.win_rate,
            "profit_factor": results.profit_factor,
            "avg_win": results.avg_win,
            "avg_loss": results.avg_loss,
            "total_trades": results.total_trades,
            "best_day": results.best_day,
            "worst_day": results.worst_day,
            "volatility_annual": results.volatility_annual,
            "regime_breakdown": results.regime_breakdown,
            "pod_attribution": results.pod_attribution,
            "run_duration_ms": results.run_duration_ms,
            "equity_curve": results.equity_curve,
            "trade_log": results.trade_log,
        }

        # Persist to disk
        RESULTS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(RESULTS_FILE, "w", encoding="utf-8") as f:
            json.dump(results_dict, f, indent=2, default=str)

        _running_jobs[job_id]["status"] = "done"
        _running_jobs[job_id]["results"] = results_dict
        logger.info("Backtest job %s complete: NAV=$%.2f (%.2f%%)",
                    job_id, results.final_nav, results.total_return * 100)

    except Exception as exc:
        logger.error("Backtest job %s failed: %s", job_id, exc)
        _running_jobs[job_id]["status"] = "error"
        _running_jobs[job_id]["error"] = str(exc)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "",
    response_model=BacktestJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Run a backtest",
    description=(
        "Kicks off a full backtest with the provided parameters. "
        "The job runs asynchronously. Poll GET /api/v1/backtest/latest for results "
        "or check job status via the returned job_id."
    ),
)
async def run_backtest(
    req: BacktestRunRequest,
    background_tasks: BackgroundTasks,
) -> BacktestJobResponse:
    # Validate dates
    try:
        start = date.fromisoformat(req.start_date)
        end = date.fromisoformat(req.end_date)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"Invalid date format: {exc}") from exc

    if start >= end:
        raise HTTPException(status_code=422, detail="start_date must be before end_date.")

    delta_days = (end - start).days
    if delta_days > 1500:
        raise HTTPException(status_code=422, detail="Date range cannot exceed 4 years (1500 days).")

    job_id = str(uuid.uuid4())[:8]
    submitted_at = datetime.now(tz=timezone.utc).isoformat()

    _running_jobs[job_id] = {
        "status": "queued",
        "submitted_at": submitted_at,
        "request": req.model_dump(),
    }

    background_tasks.add_task(_run_backtest_job, job_id, req)

    logger.info("Backtest job %s queued: %s → %s, $%.0f %.0fx leverage",
                job_id, req.start_date, req.end_date, req.initial_capital, req.leverage)

    return BacktestJobResponse(
        job_id=job_id,
        status="queued",
        message=(
            f"Backtest queued. Fetching {len(req.universe)} symbols over "
            f"{delta_days} days. This takes 30-90 seconds."
        ),
        submitted_at=submitted_at,
        results_url="/api/v1/backtest/latest",
    )


@router.get(
    "/job/{job_id}",
    summary="Check job status",
)
async def get_job_status(job_id: str) -> dict[str, Any]:
    if job_id not in _running_jobs:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found.")
    job = _running_jobs[job_id].copy()
    # Don't return full results in status check (too large)
    job.pop("results", None)
    return job


@router.get(
    "/latest",
    response_model=BacktestSummaryResponse,
    summary="Get latest backtest results",
    description="Returns the summary of the most recently completed backtest.",
)
async def get_latest_backtest() -> BacktestSummaryResponse:
    if not RESULTS_FILE.exists():
        raise HTTPException(
            status_code=404,
            detail=(
                "No backtest results found. "
                "Run POST /api/v1/backtest first, or execute: "
                "python -m backtest.run_backtest"
            ),
        )

    try:
        with open(RESULTS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        raise HTTPException(status_code=500, detail=f"Failed to read results: {exc}") from exc

    return BacktestSummaryResponse(
        run_id=data.get("run_id", "unknown"),
        start_date=data.get("start_date", ""),
        end_date=data.get("end_date", ""),
        initial_capital=data.get("initial_capital", 0),
        final_nav=data.get("final_nav", 0),
        total_return=data.get("total_return", 0),
        annualized_return=data.get("annualized_return", 0),
        sharpe_ratio=data.get("sharpe_ratio", 0),
        sortino_ratio=data.get("sortino_ratio", 0),
        max_drawdown=data.get("max_drawdown", 0),
        win_rate=data.get("win_rate", 0),
        total_trades=data.get("total_trades", 0),
        regime_breakdown=data.get("regime_breakdown", {}),
        generated_at=data.get("generated_at", datetime.now(tz=timezone.utc).isoformat()),
    )


@router.get(
    "/latest/full",
    summary="Get full backtest results including equity curve and trade log",
)
async def get_latest_full() -> dict[str, Any]:
    if not RESULTS_FILE.exists():
        raise HTTPException(
            status_code=404,
            detail="No backtest results found. Run POST /api/v1/backtest first.",
        )
    try:
        with open(RESULTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
