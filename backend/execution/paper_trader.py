"""
AetherTrade-Swarm — Paper Trading Engine
Executes simulated trades from strategy pod signals.

No real broker connection. All positions tracked in Supabase.
Initial capital: $1,000,000. Commission: $0.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

logger = logging.getLogger("aethertrade.paper_trader")

# Trading constants
INITIAL_CAPITAL: float = 1_000_000.0
COMMISSION: float = 0.0
MAX_POSITION_PCT: float = 0.20  # 20% max per single position


class PaperTrader:
    """
    Executes paper trades from strategy pod signals.

    Workflow:
        1. Receive signal dict with symbol, direction, strength, confidence, pod_name
        2. Calculate position size: strength * confidence * MAX_POSITION_PCT * NAV
        3. Fetch current price from MarketDataService
        4. Insert trade record into Supabase `trades` table
        5. Upsert position record into Supabase `positions` table
    """

    def __init__(self, db: Any) -> None:
        self._db = db

    # ------------------------------------------------------------------
    # Capital / cash helpers
    # ------------------------------------------------------------------

    def _get_cash(self) -> float:
        """
        Derive available cash: INITIAL_CAPITAL minus sum of all open
        long position values plus sum of all open short position values
        (shorts free up notional, treated as cash-neutral here for safety).
        """
        try:
            result = (
                self._db.table("positions")
                .select("quantity,avg_entry_price,side")
                .eq("status", "open")
                .execute()
            )
            positions = result.data or []
        except Exception as exc:
            logger.warning("Could not fetch positions for cash calc: %s", exc)
            positions = []

        invested = sum(
            abs(p.get("quantity", 0)) * p.get("avg_entry_price", 0)
            for p in positions
        )
        return max(INITIAL_CAPITAL - invested, 0.0)

    def _get_nav(self) -> float:
        """
        NAV = cash + sum(|qty| * current_price) for all open positions.
        """
        try:
            result = (
                self._db.table("positions")
                .select("quantity,avg_entry_price,current_price,side")
                .eq("status", "open")
                .execute()
            )
            positions = result.data or []
        except Exception as exc:
            logger.warning("Could not fetch positions for NAV calc: %s", exc)
            return INITIAL_CAPITAL

        market_value = sum(
            abs(p.get("quantity", 0)) * (p.get("current_price") or p.get("avg_entry_price", 0))
            for p in positions
        )
        invested = sum(
            abs(p.get("quantity", 0)) * p.get("avg_entry_price", 0)
            for p in positions
        )
        cash = max(INITIAL_CAPITAL - invested, 0.0)
        return cash + market_value

    # ------------------------------------------------------------------
    # Price fetching
    # ------------------------------------------------------------------

    def _fetch_price(self, symbol: str) -> float | None:
        """Fetch current price via MarketDataService (yfinance cache)."""
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

    # ------------------------------------------------------------------
    # Core execution
    # ------------------------------------------------------------------

    def execute_signal(self, signal: dict[str, Any]) -> dict[str, Any]:
        """
        Execute a signal as a paper trade.

        Expected signal keys:
            symbol      : str  — ticker e.g. "AAPL"
            direction   : str  — "long" | "short" | "neutral"
            strength    : float  — [-1.0, 1.0]
            confidence  : float  — [0.0, 1.0]
            pod_name    : str  — originating strategy pod
            signal_id   : str  — optional, generated if missing

        Returns the trade record dict on success, raises on failure.
        """
        symbol: str = signal["symbol"]
        direction: str = signal.get("direction", "neutral")
        strength: float = float(signal.get("strength", 0.0))
        confidence: float = float(signal.get("confidence", 0.5))
        pod_name: str = signal.get("pod_name", "unknown")
        signal_id: str = signal.get("signal_id") or str(uuid4())

        if direction == "neutral":
            logger.info("Skipping neutral signal for %s from %s", symbol, pod_name)
            return {"status": "skipped", "reason": "neutral signal", "symbol": symbol}

        # --- Price ---
        price = self._fetch_price(symbol)
        if not price or price <= 0:
            msg = f"Cannot execute trade: no valid price for {symbol}"
            logger.warning(msg)
            raise ValueError(msg)

        # --- Position sizing ---
        nav = self._get_nav()
        cash = self._get_cash()
        raw_alloc = abs(strength) * confidence * MAX_POSITION_PCT * nav
        alloc = min(raw_alloc, cash, MAX_POSITION_PCT * nav)

        if alloc < 1.0:
            return {"status": "skipped", "reason": "insufficient allocation", "symbol": symbol}

        quantity = round(alloc / price, 6)
        total_value = round(quantity * price, 4)

        # --- Build trade record ---
        now = datetime.now(timezone.utc).isoformat()
        trade_id = str(uuid4())
        side = "buy" if direction == "long" else "sell"

        trade_record: dict[str, Any] = {
            "trade_id": trade_id,
            "signal_id": signal_id,
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "price": price,
            "total_value": total_value,
            "commission": COMMISSION,
            "pod_name": pod_name,
            "status": "executed",
            "executed_at": now,
            "metadata": {
                "direction": direction,
                "strength": strength,
                "confidence": confidence,
                "nav_at_execution": round(nav, 2),
                "alloc_pct": round(alloc / nav * 100, 4),
            },
        }

        # --- Persist trade ---
        try:
            self._db.table("trades").insert(trade_record).execute()
            logger.info(
                "Trade executed: %s %s x%.4f @ %.4f (pod=%s)",
                side.upper(), symbol, quantity, price, pod_name,
            )
        except Exception as exc:
            logger.error("Failed to persist trade for %s: %s", symbol, exc)
            raise RuntimeError(f"Trade persistence failed: {exc}") from exc

        # --- Upsert position ---
        self._upsert_position(
            symbol=symbol,
            side=side,
            quantity=quantity,
            price=price,
            pod_name=pod_name,
            now=now,
        )

        return trade_record

    def _upsert_position(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        pod_name: str,
        now: str,
    ) -> None:
        """
        Insert or update the position for a symbol.

        If a position already exists for this symbol+pod, average-in.
        If direction reverses, close the old position first (simple model).
        """
        try:
            existing_result = (
                self._db.table("positions")
                .select("*")
                .eq("symbol", symbol)
                .eq("pod_name", pod_name)
                .eq("status", "open")
                .execute()
            )
            existing = existing_result.data[0] if existing_result.data else None
        except Exception as exc:
            logger.warning("Could not fetch existing position for %s: %s", symbol, exc)
            existing = None

        if existing:
            old_qty = float(existing.get("quantity", 0))
            old_avg = float(existing.get("avg_entry_price", 0))
            old_side = existing.get("side", side)

            if old_side != side:
                # Direction flip — close existing, open new
                self._close_position_record(existing, price, now)
                self._insert_new_position(symbol, side, quantity, price, pod_name, now)
            else:
                # Average in
                new_qty = old_qty + quantity
                new_avg = ((old_qty * old_avg) + (quantity * price)) / new_qty
                unrealized = (price - new_avg) * new_qty if side == "buy" else (new_avg - price) * new_qty

                try:
                    (
                        self._db.table("positions")
                        .update({
                            "quantity": round(new_qty, 6),
                            "avg_entry_price": round(new_avg, 6),
                            "current_price": price,
                            "unrealized_pnl": round(unrealized, 4),
                            "updated_at": now,
                        })
                        .eq("position_id", existing["position_id"])
                        .execute()
                    )
                except Exception as exc:
                    logger.error("Failed to update position for %s: %s", symbol, exc)
        else:
            self._insert_new_position(symbol, side, quantity, price, pod_name, now)

    def _insert_new_position(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        pod_name: str,
        now: str,
    ) -> None:
        unrealized = 0.0  # Entry price == current price at open
        record: dict[str, Any] = {
            "position_id": str(uuid4()),
            "symbol": symbol,
            "side": side,
            "quantity": round(quantity, 6),
            "avg_entry_price": price,
            "current_price": price,
            "unrealized_pnl": unrealized,
            "realized_pnl": 0.0,
            "pod_name": pod_name,
            "status": "open",
            "opened_at": now,
            "updated_at": now,
        }
        try:
            self._db.table("positions").insert(record).execute()
            logger.info("Position opened: %s %s x%.4f @ %.4f", side.upper(), symbol, quantity, price)
        except Exception as exc:
            logger.error("Failed to insert position for %s: %s", symbol, exc)

    def _close_position_record(
        self,
        position: dict[str, Any],
        close_price: float,
        now: str,
    ) -> None:
        """Mark position as closed and calculate realized P&L."""
        qty = float(position.get("quantity", 0))
        avg_entry = float(position.get("avg_entry_price", 0))
        side = position.get("side", "buy")

        if side == "buy":
            realized = (close_price - avg_entry) * qty
        else:
            realized = (avg_entry - close_price) * qty

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
                .eq("position_id", position["position_id"])
                .execute()
            )
            logger.info(
                "Position closed: %s realized_pnl=%.2f",
                position.get("symbol"), realized,
            )
        except Exception as exc:
            logger.error(
                "Failed to close position %s: %s",
                position.get("position_id"), exc,
            )


# Module-level singleton
_paper_trader: PaperTrader | None = None


def get_paper_trader() -> PaperTrader:
    global _paper_trader
    if _paper_trader is None:
        from models.database import get_db
        _paper_trader = PaperTrader(get_db())
    return _paper_trader
