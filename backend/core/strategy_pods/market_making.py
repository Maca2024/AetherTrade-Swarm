"""
AETHERTRADE-SWARM — Market Making Pod
Order flow and microstructure signals for liquid instruments.

Signals driven by REAL market data:
1. Spread indicator  — high-low range as % of close (wider = more opportunity)
2. Volume profile    — above-average volume days = active market making window
3. Intraday reversal — open-to-close direction differs from prev close-to-open
Applies to SPY, QQQ, AAPL, MSFT, NVDA, TSLA, BTC-USD, ETH-USD.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import numpy as np

from data.market_data import get_market_data_service
from models.schemas import PodName, RegimeState, SignalDirection
from .base import BaseStrategyPod

logger = logging.getLogger("aethertrade.market_making")

MM_UNIVERSE = ["SPY", "QQQ", "AAPL", "MSFT", "NVDA", "TSLA", "BTC-USD", "ETH-USD"]

# Reference half-spreads in bps per instrument (used for PnL estimate)
TYPICAL_SPREADS: dict[str, float] = {
    "SPY": 0.5, "QQQ": 0.6,
    "AAPL": 1.0, "MSFT": 1.0, "NVDA": 1.5, "TSLA": 2.0,
    "BTC-USD": 5.0, "ETH-USD": 6.0,
}


class MarketMakingPod(BaseStrategyPod):

    def __init__(self) -> None:
        super().__init__(PodName.MARKET_MAKING)
        self._svc = get_market_data_service()

    def generate_signals(self, context: dict[str, Any]) -> list[dict[str, Any]]:
        regime = context.get("regime", RegimeState.RANGE)
        signals: list[dict[str, Any]] = []

        # Market making is near-useless in crisis (too much adverse selection)
        if regime == RegimeState.CRISIS:
            return signals

        regime_multiplier = {
            RegimeState.BULL: 0.8,
            RegimeState.RANGE: 1.0,
            RegimeState.BEAR: 0.7,
            RegimeState.CRISIS: 0.05,
        }.get(regime, 0.5)

        for asset in MM_UNIVERSE:
            asset_signals = self._analyze_asset(asset, regime_multiplier)
            signals.extend(asset_signals)

        return signals

    # ---------------------------------------------------------------------- #
    # Per-asset microstructure analysis                                        #
    # ---------------------------------------------------------------------- #

    def _analyze_asset(self, asset: str, regime_mult: float) -> list[dict[str, Any]]:
        signals: list[dict[str, Any]] = []
        nominal_spread_bps = TYPICAL_SPREADS.get(asset, 2.0)

        try:
            raw = self._svc.fetch_daily(asset, period="3mo")
        except Exception as exc:
            logger.error("market_making: fetch_daily(%s): %s", asset, exc)
            return signals

        rows = raw.get("data", [])
        if len(rows) < 22:
            logger.warning("market_making: %s has only %d rows, skipping", asset, len(rows))
            return signals

        opens = np.array([r["open"] for r in rows], dtype=float)
        highs = np.array([r["high"] for r in rows], dtype=float)
        lows = np.array([r["low"] for r in rows], dtype=float)
        closes = np.array([r["close"] for r in rows], dtype=float)
        volumes = np.array([r["volume"] for r in rows], dtype=float)

        # ------------------------------------------------------------------ #
        # Signal 1: Spread indicator — high-low range % of close             #
        # Wide daily ranges signal opportunity for market making              #
        # ------------------------------------------------------------------ #
        hl_ranges_pct = (highs - lows) / closes  # fraction, not bps
        today_range_pct = float(hl_ranges_pct[-1])
        avg_range_pct_20d = float(np.mean(hl_ranges_pct[-21:-1]))  # exclude today
        range_ratio = today_range_pct / avg_range_pct_20d if avg_range_pct_20d > 0 else 1.0

        if range_ratio > 1.3:
            # Wider than normal spread → post tighter quotes to capture more
            spread_strength = float(np.clip((range_ratio - 1.3) / 1.0 * regime_mult, 0.0, 0.6))
            expected_pnl_bps = nominal_spread_bps * range_ratio * regime_mult

            signals.append({
                "asset": asset,
                "signal_name": "wide_spread_capture",
                "direction": SignalDirection.NEUTRAL.value,
                "strength": round(spread_strength, 4),
                "confidence": round(float(np.clip(0.60 + (range_ratio - 1.3) * 0.15, 0.60, 0.82)), 4),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "metadata": {
                    "today_range_pct": round(today_range_pct * 100, 3),
                    "avg_range_pct_20d": round(avg_range_pct_20d * 100, 3),
                    "range_ratio": round(range_ratio, 3),
                    "nominal_spread_bps": nominal_spread_bps,
                    "expected_pnl_bps": round(expected_pnl_bps, 3),
                    "signal_type": "spread_capture",
                    "quote_qty_pct_adv": round(0.002 * regime_mult, 6),
                },
            })

        # ------------------------------------------------------------------ #
        # Signal 2: Volume profile — active market making when vol elevated  #
        # ------------------------------------------------------------------ #
        avg_vol_20d = float(np.mean(volumes[-21:-1]))
        today_vol = float(volumes[-1])
        vol_ratio = today_vol / avg_vol_20d if avg_vol_20d > 0 else 1.0

        if vol_ratio > 1.5:
            # High volume day → tighter spreads, more turns → better MM economics
            vol_strength = float(np.clip((vol_ratio - 1.5) / 2.0 * regime_mult, 0.0, 0.5))
            signals.append({
                "asset": asset,
                "signal_name": "volume_profile_active",
                "direction": SignalDirection.NEUTRAL.value,
                "strength": round(vol_strength, 4),
                "confidence": round(float(np.clip(0.55 + (vol_ratio - 1.5) * 0.05, 0.55, 0.78)), 4),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "metadata": {
                    "today_volume": int(today_vol),
                    "avg_vol_20d": round(avg_vol_20d, 0),
                    "vol_ratio": round(vol_ratio, 2),
                    "signal_type": "volume_profile",
                    "interpretation": "elevated_liquidity",
                },
            })
        elif vol_ratio < 0.5:
            # Very low volume → adverse selection risk → do not make market
            signals.append({
                "asset": asset,
                "signal_name": "low_volume_halt",
                "direction": SignalDirection.NEUTRAL.value,
                "strength": 0.0,
                "confidence": round(float(np.clip(0.65 + (0.5 - vol_ratio) * 0.3, 0.65, 0.90)), 4),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "metadata": {
                    "today_volume": int(today_vol),
                    "avg_vol_20d": round(avg_vol_20d, 0),
                    "vol_ratio": round(vol_ratio, 2),
                    "action": "halt_market_making",
                    "signal_type": "volume_profile",
                    "interpretation": "thin_market_adverse_selection",
                },
            })

        # ------------------------------------------------------------------ #
        # Signal 3: Intraday reversal                                         #
        # If open-to-close direction differs from prev close-to-open →       #
        # mean-reversion opportunity                                          #
        # ------------------------------------------------------------------ #
        if len(rows) >= 2:
            today_open = float(opens[-1])
            today_close = float(closes[-1])
            prev_close = float(closes[-2])
            prev_open = float(opens[-2])

            # Today: direction from open to close
            today_oc = today_close - today_open
            # Previous: direction from prev close to today open (overnight gap)
            prev_co = today_open - prev_close
            # Legacy check: prev close-to-open direction (from the prior session)
            prev_session_co = prev_close - prev_open

            # Reversal: today's open-to-close direction is OPPOSITE yesterday's
            # close-to-open gap direction AND the move is material
            oc_pct = today_oc / today_open if today_open > 0 else 0.0
            co_pct = prev_co / prev_close if prev_close > 0 else 0.0

            if abs(oc_pct) > 0.003 and abs(co_pct) > 0.002:
                if (today_oc > 0 and prev_co < 0) or (today_oc < 0 and prev_co > 0):
                    # Directions differ → classic intraday reversal pattern
                    reversal_mag = abs(oc_pct)
                    if today_oc < 0:
                        # Closed below open despite gap-up → likely to bounce
                        rev_direction = SignalDirection.LONG
                        rev_strength = float(np.clip(reversal_mag * 8.0 * regime_mult, 0.0, 0.65))
                    else:
                        # Closed above open despite gap-down → likely to fade
                        rev_direction = SignalDirection.SHORT
                        rev_strength = -float(np.clip(reversal_mag * 8.0 * regime_mult, 0.0, 0.65))

                    confidence = float(np.clip(0.52 + reversal_mag * 5.0, 0.52, 0.75))

                    signals.append({
                        "asset": asset,
                        "signal_name": "intraday_reversal",
                        "direction": rev_direction.value,
                        "strength": round(rev_strength, 4),
                        "confidence": round(confidence, 4),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "metadata": {
                            "today_open": round(today_open, 4),
                            "today_close": round(today_close, 4),
                            "prev_close": round(prev_close, 4),
                            "oc_pct": round(oc_pct * 100, 3),
                            "gap_pct": round(co_pct * 100, 3),
                            "signal_type": "intraday_reversal",
                            "interpretation": "gap_fade",
                        },
                    })

        return signals

    def get_metrics(self) -> dict[str, Any]:
        return {
            "pod_name": self.pod_name,
            "status": "active",
            "signal_count": self._signal_count,
            "uptime_seconds": round(self.uptime_seconds, 1),
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }
