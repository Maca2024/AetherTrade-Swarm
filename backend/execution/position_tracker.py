"""
AetherTrade-Swarm — Position Tracker
Manages open positions, refreshes mark-to-market prices,
handles position closing, and saves daily portfolio snapshots.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger("aethertrade.position_tracker")

INITIAL_CAPITAL: float = 1_000_000.0


class PositionTracker:
    """
    Position lifecycle management.

    All read/write goes through the Supabase DatabaseClient.
    Uses MarketDataService for live price refresh.
    """

    def __init__(self, db: Any) -> None:
        self._db = db

    # ------------------------------------------------------------------
    # Read helpers
    # ------------------------------------------------------------------

    def get_open_positions(self) -> list[dict[str, Any]]:
        """
        Return all open positions, each enriched with current unrealized P&L.
        Prices are served from the in-process yfinance cache (5-min TTL).
        """
        try:
            result = (
                self._db.table("positions")
                .select("*")
                .eq("status", "open")
                .execute()
            )
            positions: list[dict[str, Any]] = result.data or []
        except Exception as exc:
            logger.error("get_open_positions failed: %s", exc)
            return []

        enriched = []
        for pos in positions:
            price = self._fetch_price(pos["symbol"]) or pos.get("current_price") or pos.get("avg_entry_price", 0)
            qty = float(pos.get("quantity", 0))
            avg_entry = float(pos.get("avg_entry_price", 0))
            side = pos.get("side", "buy")

            if side == "buy":
                upnl = (price - avg_entry) * qty
            else:
                upnl = (avg_entry - price) * qty

            enriched.append({
                **pos,
                "current_price": price,
                "unrealized_pnl": round(upnl, 4),
                "unrealized_pnl_pct": round(upnl / (avg_entry * qty) * 100, 4) if avg_entry * qty else 0.0,
            })

        return enriched

    # ------------------------------------------------------------------
    # Price refresh
    # ------------------------------------------------------------------

    def update_position_prices(self) -> int:
        """
        Refresh current_price and unrealized_pnl for all open positions.
        Returns count of positions updated.
        """
        try:
            result = (
                self._db.table("positions")
                .select("position_id,symbol,quantity,avg_entry_price,side")
                .eq("status", "open")
                .execute()
            )
            positions: list[dict[str, Any]] = result.data or []
        except Exception as exc:
            logger.error("update_position_prices fetch failed: %s", exc)
            return 0

        updated = 0
        now = datetime.now(timezone.utc).isoformat()

        for pos in positions:
            symbol = pos["symbol"]
            price = self._fetch_price(symbol)
            if not price:
                logger.warning("No price for %s — skipping update", symbol)
                continue

            qty = float(pos.get("quantity", 0))
            avg_entry = float(pos.get("avg_entry_price", 0))
            side = pos.get("side", "buy")

            if side == "buy":
                upnl = (price - avg_entry) * qty
            else:
                upnl = (avg_entry - price) * qty

            try:
                (
                    self._db.table("positions")
                    .update({
                        "current_price": price,
                        "unrealized_pnl": round(upnl, 4),
                        "updated_at": now,
                    })
                    .eq("position_id", pos["position_id"])
                    .execute()
                )
                updated += 1
            except Exception as exc:
                logger.error("Failed to update price for position %s (%s): %s", pos["position_id"], symbol, exc)

        logger.info("Updated prices for %d/%d open positions", updated, len(positions))
        return updated

    # ------------------------------------------------------------------
    # Position closing
    # ------------------------------------------------------------------

    def close_position(self, symbol: str, pod_name: str | None = None) -> dict[str, Any]:
        """
        Close all open positions for a symbol (optionally filtered by pod_name).
        Records a closing trade and moves unrealized P&L to realized.

        Returns a summary dict with realized_pnl and trade records created.
        """
        try:
            query = (
                self._db.table("positions")
                .select("*")
                .eq("symbol", symbol)
                .eq("status", "open")
            )
            if pod_name:
                query = query.eq("pod_name", pod_name)
            result = query.execute()
            positions: list[dict[str, Any]] = result.data or []
        except Exception as exc:
            logger.error("close_position fetch failed for %s: %s", symbol, exc)
            raise RuntimeError(f"Could not fetch positions for {symbol}: {exc}") from exc

        if not positions:
            return {"symbol": symbol, "closed": 0, "realized_pnl": 0.0, "trades": []}

        close_price = self._fetch_price(symbol)
        if not close_price:
            raise ValueError(f"Cannot close position: no valid price for {symbol}")

        now = datetime.now(timezone.utc).isoformat()
        trades_created = []
        total_realized = 0.0

        for pos in positions:
            qty = float(pos.get("quantity", 0))
            avg_entry = float(pos.get("avg_entry_price", 0))
            side = pos.get("side", "buy")

            if side == "buy":
                realized = (close_price - avg_entry) * qty
                close_side = "sell"
            else:
                realized = (avg_entry - close_price) * qty
                close_side = "buy"

            total_realized += realized

            # Update position record
            try:
                (
                    self._db.table("positions")
                    .update({
                        "status": "closed",
                        "current_price": close_price,
                        "unrealized_pnl": 0.0,
                        "realized_pnl": round(realized, 4),
                        "updated_at": now,
                    })
                    .eq("position_id", pos["position_id"])
                    .execute()
                )
            except Exception as exc:
                logger.error("Failed to close position record %s: %s", pos["position_id"], exc)
                continue

            # Record closing trade
            trade_id = str(uuid4())
            closing_trade: dict[str, Any] = {
                "trade_id": trade_id,
                "signal_id": None,
                "symbol": symbol,
                "side": close_side,
                "quantity": qty,
                "price": close_price,
                "total_value": round(qty * close_price, 4),
                "commission": 0.0,
                "pod_name": pos.get("pod_name", "manual"),
                "status": "executed",
                "executed_at": now,
                "metadata": {
                    "closing_trade": True,
                    "opened_position_id": pos["position_id"],
                    "realized_pnl": round(realized, 4),
                },
            }

            try:
                self._db.table("trades").insert(closing_trade).execute()
                trades_created.append(trade_id)
            except Exception as exc:
                logger.error("Failed to insert closing trade for %s: %s", symbol, exc)

        logger.info(
            "Closed %d position(s) for %s — realized_pnl=%.2f",
            len(positions), symbol, total_realized,
        )

        return {
            "symbol": symbol,
            "closed": len(positions),
            "realized_pnl": round(total_realized, 4),
            "close_price": close_price,
            "trades": trades_created,
        }

    # ------------------------------------------------------------------
    # Portfolio summary
    # ------------------------------------------------------------------

    def get_portfolio_summary(self) -> dict[str, Any]:
        """
        Compute NAV, cash, gross/net exposure, leverage, and position count.

        NAV = cash + market_value_of_open_positions
        Gross exposure = sum of |position market value| / NAV
        Net exposure   = (longs - shorts) / NAV
        Leverage       = gross_exposure (simplified, 1x = fully invested)
        """
        positions = self.get_open_positions()

        longs_value = 0.0
        shorts_value = 0.0
        long_count = 0
        short_count = 0

        for pos in positions:
            qty = abs(float(pos.get("quantity", 0)))
            price = float(pos.get("current_price", 0))
            market_val = qty * price

            if pos.get("side") == "buy":
                longs_value += market_val
                long_count += 1
            else:
                shorts_value += market_val
                short_count += 1

        invested = longs_value + shorts_value
        cash = max(INITIAL_CAPITAL - longs_value, 0.0)  # shorts don't consume cash in this model
        nav = cash + longs_value + shorts_value  # simplified: include both

        gross_exposure = (longs_value + shorts_value) / nav if nav > 0 else 0.0
        net_exposure = (longs_value - shorts_value) / nav if nav > 0 else 0.0
        leverage = gross_exposure

        total_unrealized = sum(float(p.get("unrealized_pnl", 0)) for p in positions)

        return {
            "nav": round(nav, 2),
            "cash": round(cash, 2),
            "invested": round(invested, 2),
            "gross_exposure": round(gross_exposure, 4),
            "net_exposure": round(net_exposure, 4),
            "leverage": round(leverage, 4),
            "position_count": len(positions),
            "long_count": long_count,
            "short_count": short_count,
            "total_unrealized_pnl": round(total_unrealized, 2),
            "as_of": datetime.now(timezone.utc).isoformat(),
        }

    # ------------------------------------------------------------------
    # Daily snapshot
    # ------------------------------------------------------------------

    def save_daily_snapshot(self) -> dict[str, Any]:
        """
        Persist current portfolio state to portfolio_snapshots table.
        Called once per day by scheduler or manually.
        """
        summary = self.get_portfolio_summary()
        now = datetime.now(timezone.utc)

        snapshot: dict[str, Any] = {
            "snapshot_id": str(uuid4()),
            "date": now.date().isoformat(),
            "nav": summary["nav"],
            "cash": summary["cash"],
            "invested": summary["invested"],
            "gross_exposure": summary["gross_exposure"],
            "net_exposure": summary["net_exposure"],
            "leverage": summary["leverage"],
            "position_count": summary["position_count"],
            "long_count": summary["long_count"],
            "short_count": summary["short_count"],
            "total_unrealized_pnl": summary["total_unrealized_pnl"],
            "created_at": now.isoformat(),
        }

        try:
            self._db.table("portfolio_snapshots").insert(snapshot).execute()
            logger.info("Daily snapshot saved: date=%s nav=%.2f", snapshot["date"], snapshot["nav"])
        except Exception as exc:
            logger.error("Failed to save portfolio snapshot: %s", exc)
            raise RuntimeError(f"Snapshot persistence failed: {exc}") from exc

        return snapshot

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _fetch_price(self, symbol: str) -> float | None:
        try:
            from data.market_data import get_market_data_service, get_crypto_service, CRYPTO_UNIVERSE
            if symbol in CRYPTO_UNIVERSE:
                prices = get_crypto_service().fetch_prices([symbol])
                return prices.get(symbol)
            svc = get_market_data_service()
            data = svc.fetch_daily(symbol, "5d")
            return data.get("last_close")
        except Exception as exc:
            logger.error("Price fetch failed for %s: %s", symbol, exc)
            return None


# Module-level singleton
_position_tracker: PositionTracker | None = None


def get_position_tracker() -> PositionTracker:
    global _position_tracker
    if _position_tracker is None:
        from models.database import get_db
        _position_tracker = PositionTracker(get_db())
    return _position_tracker
