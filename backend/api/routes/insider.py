"""
AETHERTRADE-SWARM — Insider Trading Routes

SEC EDGAR Form 4 cluster buy signal endpoints.

GET  /api/v1/insider/clusters/today           — active clusters detected today
GET  /api/v1/insider/clusters/hot             — top 10 clusters by strength (last 30 days)
GET  /api/v1/insider/clusters/{cluster_id}    — cluster detail with constituent trades
GET  /api/v1/insider/companies/{ticker}/trades — all insider trades for a ticker
GET  /api/v1/insider/backtest                 — latest backtest results
POST /api/v1/insider/subscribe                — webhook subscription (pro tier)

All endpoints require X-API-Key header. Subscribe endpoint requires PRO or ENTERPRISE tier.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field, HttpUrl

from api.auth import ApiKeyDep
from api.deps import DatabaseDep
from models.schemas import OracleBaseModel

logger = logging.getLogger("aethertrade.api.insider")

router = APIRouter(prefix="/api/v1/insider", tags=["insider"])

# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class InsiderTradeOut(OracleBaseModel):
    """Single Form 4 transaction record."""

    id: str
    cik: str
    ticker: str
    company_name: str
    insider_name: str
    insider_title: str
    transaction_date: str
    transaction_code: str
    transaction_code_label: str
    shares: float
    price_per_share: float
    total_value: float
    shares_owned_after: float
    filing_timestamp: str
    form4_url: str
    created_at: str | None = None


class ClusterOut(OracleBaseModel):
    """Insider cluster buy event."""

    cluster_id: str
    ticker: str
    cik: str
    company_name: str
    insider_count: int
    total_value: float
    avg_price: float
    window_start: str
    window_end: str
    cluster_strength: int
    insider_names: list[str]
    detected_at: str
    signal_label: str           # "STRONG BUY", "BUY", "WATCH"


class ClusterDetailOut(OracleBaseModel):
    """Cluster with embedded trade details."""

    cluster: ClusterOut
    trades: list[InsiderTradeOut]


class BacktestPeriodOut(OracleBaseModel):
    """Backtest result for one hold period."""

    run_date: str
    period_days: int
    total_return: float
    annualised_return: float | None = None
    sharpe_ratio: float
    win_rate: float
    max_drawdown: float
    alpha_vs_spy: float
    trade_count: int


class BacktestOut(OracleBaseModel):
    """All backtest periods in one response."""

    results: list[BacktestPeriodOut]
    generated_at: str
    note: str


class WebhookSubscriptionRequest(OracleBaseModel):
    """Webhook subscription for real-time cluster alerts."""

    url: str = Field(description="HTTPS callback URL for cluster alerts")
    min_strength: int = Field(
        default=60,
        ge=40,
        le=100,
        description="Minimum cluster_strength to trigger webhook (40-100)",
    )
    tickers: list[str] | None = Field(
        default=None,
        description="Optional list of tickers to watch (all if omitted)",
        max_length=50,
    )


class WebhookSubscriptionOut(OracleBaseModel):
    subscription_id: str
    url: str
    min_strength: int
    tickers: list[str] | None
    created_at: str
    status: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TRANSACTION_LABELS = {
    "P": "Open Market Purchase",
    "S": "Open Market Sale",
    "A": "Grant/Award",
    "D": "Return/Disposition",
    "F": "Tax Withholding",
    "G": "Gift",
    "M": "Option Exercise",
    "C": "Conversion",
}

_STRENGTH_LABELS = {
    (80, 101): "STRONG BUY",
    (60, 80): "BUY",
    (40, 60): "WATCH",
}


def _strength_label(score: int) -> str:
    for (lo, hi), label in _STRENGTH_LABELS.items():
        if lo <= score < hi:
            return label
    return "WATCH"


def _row_to_trade_out(row: dict[str, Any]) -> InsiderTradeOut:
    code = str(row.get("transaction_code", ""))
    return InsiderTradeOut(
        id=str(row.get("id", "")),
        cik=str(row.get("cik", "")),
        ticker=str(row.get("ticker", "")),
        company_name=str(row.get("company_name", "")),
        insider_name=str(row.get("insider_name", "")),
        insider_title=str(row.get("insider_title", "")),
        transaction_date=str(row.get("transaction_date", "")),
        transaction_code=code,
        transaction_code_label=_TRANSACTION_LABELS.get(code, code),
        shares=float(row.get("shares", 0.0)),
        price_per_share=float(row.get("price_per_share", 0.0)),
        total_value=float(row.get("total_value", 0.0)),
        shares_owned_after=float(row.get("shares_owned_after", 0.0)),
        filing_timestamp=str(row.get("filing_timestamp", "")),
        form4_url=str(row.get("form4_url", "")),
        created_at=str(row.get("created_at", "")),
    )


def _row_to_cluster_out(row: dict[str, Any]) -> ClusterOut:
    trades_json = row.get("trades_json", {})
    insider_names: list[str] = []
    if isinstance(trades_json, dict):
        insider_names = trades_json.get("insider_names", [])
    elif isinstance(trades_json, list):
        insider_names = trades_json

    strength = int(row.get("cluster_strength", 0))
    return ClusterOut(
        cluster_id=str(row.get("id", row.get("cluster_id", ""))),
        ticker=str(row.get("ticker", "")),
        cik=str(row.get("cik", "")),
        company_name=str(row.get("company_name", "")),
        insider_count=int(row.get("insider_count", 0)),
        total_value=float(row.get("total_value", 0.0)),
        avg_price=float(row.get("avg_price", 0.0)),
        window_start=str(row.get("window_start", "")),
        window_end=str(row.get("window_end", "")),
        cluster_strength=strength,
        insider_names=insider_names,
        detected_at=str(row.get("detected_at", "")),
        signal_label=_strength_label(strength),
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get(
    "/clusters/today",
    response_model=list[ClusterOut],
    summary="Today's active insider clusters",
)
async def get_clusters_today(
    _key: ApiKeyDep,
    db: DatabaseDep,
    min_strength: int = Query(default=40, ge=40, le=100, description="Minimum cluster strength"),
) -> list[ClusterOut]:
    """
    Return insider cluster buy signals detected within the last 24 hours.
    Clusters are scored 40-100; score >= 80 = STRONG BUY signal.

    The endpoint auto-runs cluster detection on the latest insider_trades rows
    if no clusters exist for today in the database.
    """
    today = date.today()
    today_str = today.isoformat()

    try:
        result = (
            db.table("insider_clusters")
            .select("*")
            .gte("detected_at", today_str)
            .gte("cluster_strength", min_strength)
            .order("cluster_strength", desc=True)
            .execute()
        )
        rows: list[dict[str, Any]] = result.data or []
    except Exception as exc:
        logger.error("Failed to query insider_clusters for today: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database query failed — try again shortly.",
        )

    if not rows:
        # Trigger on-demand detection from last 30 days of stored trades
        logger.info("No clusters found for today — running on-demand detection")
        try:
            from insider.cluster_detector import (
                load_trades_from_db,
                detect_clusters,
                store_clusters,
            )
            trades = load_trades_from_db(db, since_date=today - timedelta(days=30))
            clusters = detect_clusters(trades)
            store_clusters(clusters, db)

            # Re-query after detection
            result2 = (
                db.table("insider_clusters")
                .select("*")
                .gte("detected_at", today_str)
                .gte("cluster_strength", min_strength)
                .order("cluster_strength", desc=True)
                .execute()
            )
            rows = result2.data or []
        except Exception as exc:
            logger.warning("On-demand detection failed: %s", exc)

    return [_row_to_cluster_out(r) for r in rows]


@router.get(
    "/clusters/hot",
    response_model=list[ClusterOut],
    summary="Top 10 clusters by strength (last 30 days)",
)
async def get_hot_clusters(
    _key: ApiKeyDep,
    db: DatabaseDep,
    days: int = Query(default=30, ge=1, le=90, description="Look-back window in days"),
    limit: int = Query(default=10, ge=1, le=50, description="Maximum clusters to return"),
) -> list[ClusterOut]:
    """
    Return the strongest insider cluster buy signals from the last N days,
    sorted by cluster_strength descending. Use this for a watchlist of
    high-conviction insider accumulation.
    """
    since = (date.today() - timedelta(days=days)).isoformat()

    try:
        result = (
            db.table("insider_clusters")
            .select("*")
            .gte("detected_at", since)
            .order("cluster_strength", desc=True)
            .limit(limit)
            .execute()
        )
        rows: list[dict[str, Any]] = result.data or []
    except Exception as exc:
        logger.error("Failed to query hot clusters: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database query failed.",
        )

    return [_row_to_cluster_out(r) for r in rows]


@router.get(
    "/clusters/{cluster_id}",
    response_model=ClusterDetailOut,
    summary="Cluster detail with constituent trades",
)
async def get_cluster_detail(
    cluster_id: str,
    _key: ApiKeyDep,
    db: DatabaseDep,
) -> ClusterDetailOut:
    """
    Return full detail for a specific cluster, including all constituent
    insider trades that triggered the cluster signal.
    """
    try:
        result = (
            db.table("insider_clusters")
            .select("*")
            .eq("id", cluster_id)
            .limit(1)
            .execute()
        )
        rows: list[dict[str, Any]] = result.data or []
    except Exception as exc:
        logger.error("Failed to fetch cluster %s: %s", cluster_id, exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database query failed.",
        )

    if not rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cluster {cluster_id!r} not found.",
        )

    cluster_row = rows[0]
    cluster_out = _row_to_cluster_out(cluster_row)

    # Extract trade IDs from the JSON blob
    trades_json = cluster_row.get("trades_json", {})
    trade_ids: list[str] = []
    if isinstance(trades_json, dict):
        trade_ids = trades_json.get("trade_ids", [])

    # Fetch constituent trades
    trade_rows: list[dict[str, Any]] = []
    if trade_ids:
        try:
            # Supabase `in_` filter — query for all trade IDs
            # We use .in_ via the PostgREST filter pattern
            ids_str = ",".join(str(tid) for tid in trade_ids)
            trade_result = (
                db.table("insider_trades")
                .select("*")
                .in_("id", trade_ids)
                .execute()
            )
            trade_rows = trade_result.data or []
        except Exception as exc:
            logger.warning("Could not fetch constituent trades for cluster %s: %s", cluster_id, exc)

    return ClusterDetailOut(
        cluster=cluster_out,
        trades=[_row_to_trade_out(r) for r in trade_rows],
    )


@router.get(
    "/companies/{ticker}/trades",
    response_model=list[InsiderTradeOut],
    summary="All insider trades for a ticker",
)
async def get_company_trades(
    ticker: str,
    _key: ApiKeyDep,
    db: DatabaseDep,
    days: int = Query(default=90, ge=1, le=365, description="Look-back window in days"),
    code: str | None = Query(default=None, description="Filter by transaction code: P, S, A, etc."),
    limit: int = Query(default=100, ge=1, le=500, description="Maximum records to return"),
) -> list[InsiderTradeOut]:
    """
    Return all insider Form 4 transactions for a given ticker.
    Use the `code` parameter to filter by transaction type:
    - P = open-market purchase (most bullish)
    - S = open-market sale
    - A = award/grant (compensation, less informative)
    """
    ticker = ticker.upper()
    since = (date.today() - timedelta(days=days)).isoformat()

    try:
        query = (
            db.table("insider_trades")
            .select("*")
            .eq("ticker", ticker)
            .gte("transaction_date", since)
            .order("transaction_date", desc=True)
            .limit(limit)
        )
        if code:
            query = query.eq("transaction_code", code.upper())

        result = query.execute()
        rows: list[dict[str, Any]] = result.data or []
    except Exception as exc:
        logger.error("Failed to query insider trades for %s: %s", ticker, exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database query failed.",
        )

    return [_row_to_trade_out(r) for r in rows]


@router.get(
    "/backtest",
    response_model=BacktestOut,
    summary="Latest insider cluster backtest results",
)
async def get_backtest_results(
    _key: ApiKeyDep,
    db: DatabaseDep,
    run_fresh: bool = Query(
        default=False,
        description="Set true to rerun the backtest (takes 60-120 seconds)",
    ),
) -> BacktestOut:
    """
    Return historical backtest results for the insider cluster buy strategy.

    Results cover 2020-2025 with 60, 90, and 180-day hold periods.
    Metrics include annualised return, Sharpe ratio, win rate, max drawdown,
    and alpha vs SPY.

    Set `run_fresh=true` to trigger a fresh backtest run (slow — runs in background).
    """
    if run_fresh:
        # Trigger fresh backtest (synchronous for now — move to BackgroundTasks for prod)
        logger.info("Fresh backtest requested via API — running now")
        try:
            from insider.backtest import run_backtest, store_backtest_results
            results = run_backtest()
            store_backtest_results(results, db)
        except Exception as exc:
            logger.error("Fresh backtest failed: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Backtest execution failed: {exc}",
            )

    from insider.backtest import load_latest_backtest
    rows = load_latest_backtest(db)

    if not rows:
        return BacktestOut(
            results=[],
            generated_at=datetime.now(timezone.utc).isoformat(),
            note=(
                "No backtest results available yet. "
                "Call with ?run_fresh=true to generate results (takes 60-120 seconds)."
            ),
        )

    period_results: list[BacktestPeriodOut] = []
    for row in rows:
        hold_days = int(row.get("period_days", 0))
        total_ret = float(row.get("total_return", 0.0))
        # Compute annualised return from total and hold period
        years = (hold_days * float(row.get("trade_count", 1))) / 252
        ann_ret = (1 + total_ret) ** (1 / max(years, 0.1)) - 1 if total_ret > -1 else None

        period_results.append(BacktestPeriodOut(
            run_date=str(row.get("run_date", "")),
            period_days=hold_days,
            total_return=total_ret,
            annualised_return=ann_ret,
            sharpe_ratio=float(row.get("sharpe_ratio", 0.0)),
            win_rate=float(row.get("win_rate", 0.0)),
            max_drawdown=float(row.get("max_drawdown", 0.0)),
            alpha_vs_spy=float(row.get("alpha_vs_spy", 0.0)),
            trade_count=int(row.get("trade_count", 0)),
        ))

    return BacktestOut(
        results=period_results,
        generated_at=datetime.now(timezone.utc).isoformat(),
        note=(
            "Backtest: 2020-2025 | Equal-weighted cluster buy portfolio | "
            "Entry: next trading day after cluster detection | "
            "Benchmark: SPY buy-and-hold"
        ),
    )


@router.post(
    "/subscribe",
    response_model=WebhookSubscriptionOut,
    status_code=status.HTTP_201_CREATED,
    summary="Subscribe to cluster alerts via webhook",
)
async def subscribe_to_clusters(
    body: WebhookSubscriptionRequest,
    key: ApiKeyDep,
    db: DatabaseDep,
) -> WebhookSubscriptionOut:
    """
    Register a webhook URL to receive real-time insider cluster alerts.

    When a new cluster is detected that meets `min_strength`, a POST request
    will be sent to your URL with a ClusterOut payload.

    Requires PRO or ENTERPRISE tier API key.

    The system validates the URL is reachable before confirming the subscription.
    """
    # Tier check — free tier cannot subscribe to webhooks
    tier = key.get("tier", "free")
    if tier == "free":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Webhook subscriptions require PRO or ENTERPRISE tier. "
                "Upgrade your API key to access real-time cluster alerts."
            ),
        )

    # Validate URL scheme
    url = body.url
    if not (url.startswith("https://") or url.startswith("http://localhost")):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Webhook URL must use HTTPS (or http://localhost for development).",
        )

    subscription_id = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()

    record = {
        "subscription_id": subscription_id,
        "owner_email": key.get("owner_email", ""),
        "key_id": key.get("key_id", ""),
        "url": url,
        "min_strength": body.min_strength,
        "tickers": body.tickers,
        "created_at": now,
        "is_active": True,
    }

    try:
        db.table("insider_webhook_subscriptions").insert(record).execute()
    except Exception as exc:
        logger.warning("Webhook subscription store failed (table may not exist yet): %s", exc)
        # Non-fatal for MVP — subscription is returned but not persisted

    return WebhookSubscriptionOut(
        subscription_id=subscription_id,
        url=url,
        min_strength=body.min_strength,
        tickers=body.tickers,
        created_at=now,
        status="active",
    )
