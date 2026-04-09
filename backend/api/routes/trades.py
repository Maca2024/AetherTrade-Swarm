"""
AetherTrade-Swarm — Trades & Execution Routes

GET  /api/v1/trades                  — trade history from Supabase
POST /api/v1/trades/execute          — execute a signal as a paper trade
GET  /api/v1/portfolio/equity-curve  — NAV timeseries from portfolio_snapshots
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from api.auth import ApiKeyDep
from models.database import get_db
from models.schemas import OracleBaseModel

logger = logging.getLogger("aethertrade.routes.trades")

router = APIRouter(tags=["trades"])


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class ExecuteSignalRequest(OracleBaseModel):
    symbol: str = Field(
        description="Ticker symbol, e.g. AAPL or BTC-USD",
        min_length=1,
        max_length=20,
    )
    direction: str = Field(
        description="Trade direction: long | short | neutral",
        pattern="^(long|short|neutral)$",
    )
    strength: float = Field(
        default=0.5,
        ge=-1.0,
        le=1.0,
        description="Signal strength [-1.0, 1.0]",
    )
    confidence: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Model confidence [0.0, 1.0]",
    )
    pod_name: str = Field(
        default="manual",
        max_length=64,
        description="Originating strategy pod",
    )
    signal_id: str | None = Field(
        default=None,
        description="Optional signal ID from signal engine",
    )


class TradeRecord(OracleBaseModel):
    trade_id: str
    signal_id: str | None = None
    symbol: str
    side: str
    quantity: float
    price: float
    total_value: float
    commission: float
    pod_name: str
    status: str
    executed_at: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExecuteTradeResponse(OracleBaseModel):
    status: str
    trade: TradeRecord | None = None
    reason: str | None = None
    executed_at: datetime


class TradeHistoryResponse(OracleBaseModel):
    trades: list[dict[str, Any]]
    total: int
    page: int
    page_size: int


class EquityCurvePoint(OracleBaseModel):
    date: str
    nav: float
    cash: float
    total_unrealized_pnl: float
    position_count: int


class EquityCurveResponse(OracleBaseModel):
    points: list[EquityCurvePoint]
    total: int
    initial_capital: float
    current_nav: float
    total_return_pct: float
    as_of: datetime


# ---------------------------------------------------------------------------
# GET /api/v1/trades
# ---------------------------------------------------------------------------

@router.get(
    "/api/v1/trades",
    response_model=TradeHistoryResponse,
    summary="Trade history",
)
async def get_trade_history(
    _key: ApiKeyDep,
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=50, ge=1, le=200, description="Records per page"),
    symbol: str | None = Query(default=None, description="Filter by symbol"),
    pod_name: str | None = Query(default=None, description="Filter by pod"),
    side: str | None = Query(default=None, pattern="^(buy|sell)$", description="Filter by side"),
) -> TradeHistoryResponse:
    """
    Returns paginated trade history from Supabase.
    Optionally filtered by symbol, pod_name, or side.
    """
    db = get_db()

    try:
        query = db.table("trades").select("*")

        if symbol:
            query = query.eq("symbol", symbol.upper())
        if pod_name:
            query = query.eq("pod_name", pod_name)
        if side:
            query = query.eq("side", side)

        # For Supabase (real client), apply ordering and range
        if not db.is_fallback:
            offset = (page - 1) * page_size
            result = (
                db.table("trades")
                .select("*", count="exact")
                .order("executed_at", desc=True)
                .range(offset, offset + page_size - 1)
                .execute()
            )
            trades = result.data or []
            total = result.count if hasattr(result, "count") and result.count is not None else len(trades)
        else:
            # In-memory fallback: simple pagination
            result = query.order("executed_at", desc=True).execute()
            all_trades = result.data or []
            total = len(all_trades)
            offset = (page - 1) * page_size
            trades = all_trades[offset: offset + page_size]

    except Exception as exc:
        logger.error("get_trade_history failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch trades: {exc}",
        ) from exc

    return TradeHistoryResponse(
        trades=trades,
        total=total,
        page=page,
        page_size=page_size,
    )


# ---------------------------------------------------------------------------
# POST /api/v1/trades/execute
# ---------------------------------------------------------------------------

@router.post(
    "/api/v1/trades/execute",
    response_model=ExecuteTradeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Execute a paper trade",
)
async def execute_trade(
    request: ExecuteSignalRequest,
    _key: ApiKeyDep,
) -> ExecuteTradeResponse:
    """
    Execute a signal as a paper trade.

    The engine calculates position size using:
        allocation = |strength| * confidence * 20% * NAV

    The position is capped at 20% of current NAV and available cash.
    Neutral signals are rejected immediately (422).
    """
    if request.direction == "neutral":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Neutral signals cannot be executed as trades.",
        )

    from execution.paper_trader import get_paper_trader

    trader = get_paper_trader()
    signal = request.model_dump()

    try:
        result = trader.execute_signal(signal)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except RuntimeError as exc:
        logger.error("Trade execution failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    if result.get("status") == "skipped":
        return ExecuteTradeResponse(
            status="skipped",
            trade=None,
            reason=result.get("reason"),
            executed_at=datetime.now(timezone.utc),
        )

    trade = TradeRecord(
        trade_id=result["trade_id"],
        signal_id=result.get("signal_id"),
        symbol=result["symbol"],
        side=result["side"],
        quantity=result["quantity"],
        price=result["price"],
        total_value=result["total_value"],
        commission=result["commission"],
        pod_name=result["pod_name"],
        status=result["status"],
        executed_at=result["executed_at"],
        metadata=result.get("metadata", {}),
    )

    return ExecuteTradeResponse(
        status="executed",
        trade=trade,
        reason=None,
        executed_at=datetime.now(timezone.utc),
    )


# ---------------------------------------------------------------------------
# GET /api/v1/portfolio/equity-curve
# ---------------------------------------------------------------------------

@router.get(
    "/api/v1/portfolio/equity-curve",
    response_model=EquityCurveResponse,
    summary="NAV equity curve",
)
async def get_equity_curve(
    _key: ApiKeyDep,
    limit: int = Query(default=365, ge=1, le=1825, description="Max data points (days)"),
) -> EquityCurveResponse:
    """
    Returns the NAV timeseries from portfolio_snapshots.

    Each point represents one daily snapshot.
    Use this to render the equity curve chart on the dashboard.
    """
    from execution.position_tracker import INITIAL_CAPITAL

    db = get_db()

    try:
        if not db.is_fallback:
            result = (
                db.table("portfolio_snapshots")
                .select("date,nav,cash,total_unrealized_pnl,position_count")
                .order("date", desc=False)
                .limit(limit)
                .execute()
            )
        else:
            result = (
                db.table("portfolio_snapshots")
                .select("*")
                .order("date", desc=False)
                .limit(limit)
                .execute()
            )
        snapshots: list[dict[str, Any]] = result.data or []
    except Exception as exc:
        logger.error("get_equity_curve failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch equity curve: {exc}",
        ) from exc

    points = [
        EquityCurvePoint(
            date=s["date"],
            nav=float(s.get("nav", INITIAL_CAPITAL)),
            cash=float(s.get("cash", INITIAL_CAPITAL)),
            total_unrealized_pnl=float(s.get("total_unrealized_pnl", 0.0)),
            position_count=int(s.get("position_count", 0)),
        )
        for s in snapshots
    ]

    current_nav = points[-1].nav if points else INITIAL_CAPITAL
    total_return_pct = round((current_nav - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100, 4)

    return EquityCurveResponse(
        points=points,
        total=len(points),
        initial_capital=INITIAL_CAPITAL,
        current_nav=current_nav,
        total_return_pct=total_return_pct,
        as_of=datetime.now(timezone.utc),
    )
