"""
AETHERTRADE-SWARM — Insider Cluster Buy Detector

Detects coordinated insider buying patterns (cluster buys) from a stream of
Form 4 transactions. Academic research (Cohen, Malloy, Pomorski 2012; Seyhun 1998)
shows that cluster buys — multiple insiders buying at the same company within a
short window — generate significant alpha vs. the market.

Algorithm:
- Group P (open-market purchase) transactions by company ticker
- Apply a 10-day rolling window
- Flag companies where 3+ unique insiders bought, each trade > $25K
- Score clusters 0-100 based on insider seniority and trade size
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger("aethertrade.insider.cluster_detector")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Default thresholds — can be overridden per call
DEFAULT_MIN_INSIDERS = 3
DEFAULT_WINDOW_DAYS = 10
DEFAULT_MIN_TRADE_VALUE = 25_000.0   # USD

# Transaction code for open-market purchase (the only signal that matters)
BUY_CODE = "P"

# Insider titles that indicate C-suite / senior insiders
SENIOR_TITLES = frozenset({"ceo", "cfo", "coo", "cto", "cso", "chairman", "president"})

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class TradeInput:
    """
    Minimal trade record needed for cluster detection.
    Matches the fields produced by edgar_fetcher.InsiderTrade and the
    insider_trades DB table.
    """
    id: str
    ticker: str
    cik: str
    company_name: str
    insider_name: str
    insider_title: str
    transaction_date: date
    transaction_code: str
    total_value: float
    price_per_share: float
    shares: float


@dataclass
class Cluster:
    """A detected insider cluster buy event."""

    cluster_id: str
    ticker: str
    cik: str
    company_name: str

    # Window
    window_start: date
    window_end: date

    # Aggregate metrics
    insider_count: int
    total_value: float
    avg_price: float

    # Constituent trades
    trade_ids: list[str] = field(default_factory=list)
    insider_names: list[str] = field(default_factory=list)

    # Signal quality
    cluster_strength: int = 0   # 0-100

    detected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def _score_cluster(
    trades_in_window: list[TradeInput],
    insider_count: int,
    total_value: float,
) -> int:
    """
    Compute cluster_strength (0-100) based on:

    Base                         40  (meeting 3-insider / 10-day / $25K threshold)
    +10 per extra insider above 3
    +15 if CEO, CFO, or Chairman included
    +10 if any single trade > $100K
    +5  if 2+ directors present (broad insider conviction)
    Cap at 100.

    Returns:
        Integer score 0-100
    """
    score = 40

    # Bonus per additional insider beyond the minimum threshold
    extra_insiders = max(0, insider_count - DEFAULT_MIN_INSIDERS)
    score += extra_insiders * 10

    # Check for senior executives
    titles_lower = [t.insider_title.lower() for t in trades_in_window]
    has_senior = any(
        any(kw in title for kw in SENIOR_TITLES)
        for title in titles_lower
    )
    if has_senior:
        score += 15

    # Large single trade
    if any(t.total_value > 100_000 for t in trades_in_window):
        score += 10

    # Multiple directors (more than 1 director = broad conviction)
    director_count = sum(1 for t in titles_lower if "director" in t)
    if director_count >= 2:
        score += 5

    return min(100, score)


# ---------------------------------------------------------------------------
# Core detection algorithm
# ---------------------------------------------------------------------------

def detect_clusters(
    trades: list[TradeInput],
    min_insiders: int = DEFAULT_MIN_INSIDERS,
    window_days: int = DEFAULT_WINDOW_DAYS,
    min_trade_value: float = DEFAULT_MIN_TRADE_VALUE,
) -> list[Cluster]:
    """
    Detect insider cluster buys from a list of trade records.

    The algorithm:
    1. Filter to open-market purchases (code == 'P') above the min_trade_value.
    2. Group filtered trades by ticker.
    3. For each ticker, apply a sliding window of `window_days` days.
    4. A cluster is triggered when `min_insiders` or more unique insiders
       have purchased within the window.
    5. Score each cluster and return Cluster objects.

    Note: 10% holders (passive institutional) should be filtered at the
    edgar_fetcher level before calling this function.

    Args:
        trades:          Raw trade records (any transaction code mix is OK — we filter)
        min_insiders:    Minimum unique insiders required (default 3)
        window_days:     Rolling window length in calendar days (default 10)
        min_trade_value: Minimum USD value per trade (default $25,000)

    Returns:
        List of detected Cluster objects, sorted by cluster_strength descending
    """
    # --- Step 1: Filter to qualifying open-market purchases ---
    qualifying: list[TradeInput] = [
        t for t in trades
        if t.transaction_code == BUY_CODE and t.total_value >= min_trade_value
    ]

    if not qualifying:
        logger.info("No qualifying P-coded trades found — no clusters detected")
        return []

    # --- Step 2: Group by ticker ---
    by_ticker: dict[str, list[TradeInput]] = {}
    for t in qualifying:
        by_ticker.setdefault(t.ticker, []).append(t)

    # --- Step 3 & 4: Sliding window per ticker ---
    clusters: list[Cluster] = []
    window_delta = timedelta(days=window_days)

    for ticker, ticker_trades in by_ticker.items():
        # Sort by transaction date ascending for window scanning
        sorted_trades = sorted(ticker_trades, key=lambda t: t.transaction_date)

        # O(n^2) sliding window — trade counts per ticker are small (<50 typically)
        seen_windows: set[tuple[str, str]] = set()  # (window_start, window_end) to avoid duplication

        for i, anchor in enumerate(sorted_trades):
            window_end_date = anchor.transaction_date + window_delta

            # Collect all trades within [anchor.date, anchor.date + window_days]
            window_trades: list[TradeInput] = [
                t for t in sorted_trades[i:]
                if t.transaction_date <= window_end_date
            ]

            # Unique insider check
            unique_insiders = {t.insider_name for t in window_trades}
            if len(unique_insiders) < min_insiders:
                continue

            # Deduplication key — collapse overlapping windows for same period
            win_key = (anchor.transaction_date.isoformat(), window_end_date.isoformat())
            if win_key in seen_windows:
                continue
            seen_windows.add(win_key)

            # --- Build cluster ---
            insider_count = len(unique_insiders)
            total_value = sum(t.total_value for t in window_trades)
            avg_price = (
                sum(t.price_per_share for t in window_trades) / len(window_trades)
                if window_trades else 0.0
            )
            strength = _score_cluster(window_trades, insider_count, total_value)

            cluster = Cluster(
                cluster_id=str(uuid4()),
                ticker=ticker,
                cik=window_trades[0].cik,
                company_name=window_trades[0].company_name,
                window_start=anchor.transaction_date,
                window_end=window_end_date,
                insider_count=insider_count,
                total_value=total_value,
                avg_price=avg_price,
                trade_ids=[t.id for t in window_trades],
                insider_names=list(unique_insiders),
                cluster_strength=strength,
            )
            clusters.append(cluster)

    # Sort strongest clusters first
    clusters.sort(key=lambda c: c.cluster_strength, reverse=True)
    logger.info("Detected %d clusters across %d tickers", len(clusters), len(by_ticker))
    return clusters


# ---------------------------------------------------------------------------
# Load trades from DB for detection
# ---------------------------------------------------------------------------

def load_trades_from_db(
    db: Any,
    since_date: date | None = None,
    ticker: str | None = None,
) -> list[TradeInput]:
    """
    Load insider_trades records from Supabase and convert to TradeInput objects.

    Args:
        db:         DatabaseClient instance
        since_date: Only load trades on or after this date (default: last 30 days)
        ticker:     Optional ticker filter

    Returns:
        List of TradeInput records ready for detect_clusters()
    """
    if since_date is None:
        since_date = date.today() - timedelta(days=30)

    query = (
        db.table("insider_trades")
        .select("*")
        .gte("transaction_date", since_date.isoformat())
        .order("transaction_date", desc=False)
    )
    if ticker:
        query = query.eq("ticker", ticker.upper())

    try:
        result = query.execute()
        rows = result.data or []
    except Exception as exc:
        logger.error("Failed to load insider trades from DB: %s", exc)
        return []

    trades: list[TradeInput] = []
    for row in rows:
        try:
            tx_date_raw = row.get("transaction_date", "")
            if isinstance(tx_date_raw, str):
                tx_date = date.fromisoformat(tx_date_raw[:10])
            elif isinstance(tx_date_raw, date):
                tx_date = tx_date_raw
            else:
                continue

            trades.append(TradeInput(
                id=str(row.get("id", uuid4())),
                ticker=str(row.get("ticker", "")),
                cik=str(row.get("cik", "")),
                company_name=str(row.get("company_name", "")),
                insider_name=str(row.get("insider_name", "")),
                insider_title=str(row.get("insider_title", "")),
                transaction_date=tx_date,
                transaction_code=str(row.get("transaction_code", "")),
                total_value=float(row.get("total_value", 0.0)),
                price_per_share=float(row.get("price_per_share", 0.0)),
                shares=float(row.get("shares", 0.0)),
            ))
        except Exception as exc:
            logger.debug("Skipping malformed DB row: %s", exc)

    logger.debug("Loaded %d trades from DB (since=%s)", len(trades), since_date)
    return trades


# ---------------------------------------------------------------------------
# Supabase persistence
# ---------------------------------------------------------------------------

def store_clusters(clusters: list[Cluster], db: Any) -> int:
    """
    Upsert detected clusters into the Supabase `insider_clusters` table.

    Args:
        clusters: Detected Cluster objects
        db:       DatabaseClient instance

    Returns:
        Count of records stored
    """
    if not clusters:
        return 0

    stored = 0
    for cluster in clusters:
        record = {
            "ticker": cluster.ticker,
            "cik": cluster.cik,
            "company_name": cluster.company_name,
            "insider_count": cluster.insider_count,
            "total_value": cluster.total_value,
            "avg_price": cluster.avg_price,
            "window_start": cluster.window_start.isoformat(),
            "window_end": cluster.window_end.isoformat(),
            "cluster_strength": cluster.cluster_strength,
            "trades_json": {
                "trade_ids": cluster.trade_ids,
                "insider_names": cluster.insider_names,
            },
            "detected_at": cluster.detected_at.isoformat(),
        }
        try:
            db.table("insider_clusters").insert(record).execute()
            stored += 1
        except Exception as exc:
            logger.debug("Cluster insert skipped (likely duplicate): %s", exc)

    logger.info("Stored %d/%d cluster records", stored, len(clusters))
    return stored


def run_daily_detection(db: Any) -> list[Cluster]:
    """
    Convenience function to run the full detection pipeline:
    1. Load last 30 days of trades from DB
    2. Detect clusters
    3. Store clusters
    4. Return new clusters

    Designed to be called from a daily cron job or background task.
    """
    logger.info("Starting daily cluster detection run")
    trades = load_trades_from_db(db, since_date=date.today() - timedelta(days=30))
    clusters = detect_clusters(trades)
    stored = store_clusters(clusters, db)
    logger.info(
        "Daily detection complete: %d trades → %d clusters → %d stored",
        len(trades), len(clusters), stored,
    )
    return clusters
