"""
AETHERTRADE-SWARM — Statistical Arbitrage Pod
Real pairs-trading: price-ratio z-score on three cointegrated pairs.

Pairs:
  AAPL / MSFT  — mega-cap tech
  GOOGL / META — digital advertising duopoly
  JPM  / GS    — US investment banking

Signal rules:
  long spread  (long leg-A, short leg-B) when z < -2
  short spread (short leg-A, long leg-B) when z > +2
  neutral when |z| < 1
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import numpy as np

from data.market_data import get_market_data_service
from models.schemas import PodName, RegimeState, SignalDirection
from .base import BaseStrategyPod

logger = logging.getLogger("aethertrade.stat_arb")

# Each tuple: (leg_A, leg_B, rolling_window_days)
PAIRS: list[tuple[str, str, int]] = [
    ("AAPL", "MSFT", 60),
    ("GOOGL", "META", 60),
    ("JPM", "GS", 60),
]

# Z-score entry / exit thresholds
Z_ENTRY = 2.0
Z_EXIT = 1.0


def _zscore_series(ratio: np.ndarray, window: int) -> float:
    """
    Compute the z-score of the most recent ratio value against its
    rolling window mean and std. Returns NaN if insufficient data.
    """
    if len(ratio) < window:
        return float("nan")
    rolling = ratio[-window:]
    mu = float(np.mean(rolling))
    sigma = float(np.std(rolling, ddof=1))
    if sigma < 1e-10:
        return float("nan")
    return float((ratio[-1] - mu) / sigma)


def _fetch_closes(svc: Any, symbol: str) -> list[float]:
    """Return list of closing prices for symbol, empty on error."""
    try:
        daily = svc.fetch_daily(symbol, period="6mo")
        rows = daily.get("data", [])
        return [r["close"] for r in rows if r.get("close")]
    except Exception as exc:
        logger.error("stat_arb: fetch %s failed: %s", symbol, exc)
        return []


class StatArbPod(BaseStrategyPod):

    def __init__(self) -> None:
        super().__init__(PodName.STAT_ARB)
        self._svc = get_market_data_service()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def generate_signals(self, context: dict[str, Any]) -> list[dict[str, Any]]:
        regime = context.get("regime", RegimeState.RANGE)
        signals: list[dict[str, Any]] = []
        ts = datetime.now(timezone.utc).isoformat()

        # Stat arb is market-neutral; scale back only in crisis
        regime_scale = {
            RegimeState.BULL: 0.80,
            RegimeState.RANGE: 1.00,
            RegimeState.BEAR: 0.85,
            RegimeState.CRISIS: 0.30,
        }.get(regime, 0.70)

        for leg_a, leg_b, window in PAIRS:
            closes_a = _fetch_closes(self._svc, leg_a)
            closes_b = _fetch_closes(self._svc, leg_b)

            # Align to the shorter series length
            min_len = min(len(closes_a), len(closes_b))
            if min_len < window + 5:
                logger.warning(
                    "stat_arb: insufficient data for pair %s/%s (%d rows)",
                    leg_a, leg_b, min_len,
                )
                continue

            closes_a = closes_a[-min_len:]
            closes_b = closes_b[-min_len:]

            prices_a = np.array(closes_a)
            prices_b = np.array(closes_b)

            # Price ratio: A / B
            ratio = prices_a / prices_b
            z = _zscore_series(ratio, window)

            if np.isnan(z):
                logger.warning("stat_arb: z-score NaN for %s/%s", leg_a, leg_b)
                continue

            current_ratio = float(ratio[-1])
            rolling_mean = float(np.mean(ratio[-window:]))
            rolling_std = float(np.std(ratio[-window:], ddof=1))

            # Current price of each leg for metadata
            price_a = float(prices_a[-1])
            price_b = float(prices_b[-1])

            abs_z = abs(z)

            if abs_z < Z_EXIT:
                # No signal — ratio within normal range
                continue

            # Strength proportional to how far z is from threshold, capped at 1
            raw_strength = min((abs_z - Z_EXIT) / (Z_ENTRY - Z_EXIT + 0.001), 1.0)
            scaled = round(raw_strength * regime_scale, 4)

            if z < -Z_ENTRY:
                # Spread too cheap: long A, short B
                dir_a, dir_b = SignalDirection.LONG, SignalDirection.SHORT
                strength_a, strength_b = scaled, -scaled
            elif z > Z_ENTRY:
                # Spread too rich: short A, long B
                dir_a, dir_b = SignalDirection.SHORT, SignalDirection.LONG
                strength_a, strength_b = -scaled, scaled
            else:
                # |z| between Z_EXIT and Z_ENTRY — no new entry, existing positions allowed
                continue

            # Confidence: higher z divergence → higher confidence, capped at 0.88
            confidence = round(min(0.50 + abs_z * 0.08, 0.88), 4)

            pair_label = f"{leg_a}_{leg_b}"

            signals.append({
                "asset": leg_a,
                "signal_name": f"pairs_zscore_{pair_label}",
                "direction": dir_a.value,
                "strength": strength_a,
                "confidence": confidence,
                "timestamp": ts,
                "metadata": {
                    "pair": pair_label,
                    "leg": "A",
                    "z_score": round(z, 4),
                    "ratio": round(current_ratio, 4),
                    "rolling_mean": round(rolling_mean, 4),
                    "rolling_std": round(rolling_std, 4),
                    "window_days": window,
                    "price": round(price_a, 2),
                    "regime_scale": regime_scale,
                    "signal_type": "pairs_spread",
                },
            })

            signals.append({
                "asset": leg_b,
                "signal_name": f"pairs_zscore_{pair_label}",
                "direction": dir_b.value,
                "strength": strength_b,
                "confidence": confidence,
                "timestamp": ts,
                "metadata": {
                    "pair": pair_label,
                    "leg": "B",
                    "z_score": round(z, 4),
                    "ratio": round(current_ratio, 4),
                    "rolling_mean": round(rolling_mean, 4),
                    "rolling_std": round(rolling_std, 4),
                    "window_days": window,
                    "price": round(price_b, 2),
                    "regime_scale": regime_scale,
                    "signal_type": "pairs_spread",
                },
            })

        self._signal_count = len(signals)
        return signals

    def get_metrics(self) -> dict[str, Any]:
        return {
            "pod_name": self.pod_name,
            "status": "active",
            "signal_count": self._signal_count,
            "pairs": [f"{a}/{b}" for a, b, _ in PAIRS],
            "z_entry_threshold": Z_ENTRY,
            "z_exit_threshold": Z_EXIT,
            "uptime_seconds": round(self.uptime_seconds, 1),
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }
