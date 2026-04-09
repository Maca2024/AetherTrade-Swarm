"""
AETHERTRADE-SWARM — Options & Volatility Pod
Volatility Risk Premium (VRP) harvesting + Tail Hedge management.

Signals driven by REAL market data:
1. Realized vol vs. historical median proxy (VRP signal on SPY)
2. Tail hedge: protective long when realized vol > 25%
3. Vol term structure: contango/backwardation from SPY rolling windows
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import numpy as np

from data.market_data import get_market_data_service
from models.schemas import PodName, RegimeState, SignalDirection
from .base import BaseStrategyPod

logger = logging.getLogger("aethertrade.options_vol")

VOL_UNDERLYINGS = ["SPY", "QQQ", "IWM", "GLD", "TLT"]

# Annualization factor for daily returns
TRADING_DAYS = 252


def _annualized_vol(returns: np.ndarray) -> float:
    """Return annualized realized volatility from daily log returns."""
    if len(returns) < 5:
        return float("nan")
    return float(np.std(returns, ddof=1) * np.sqrt(TRADING_DAYS))


def _rolling_vol(returns: np.ndarray, window: int) -> np.ndarray:
    """Compute rolling annualized vol for a return series."""
    if len(returns) < window:
        return np.array([])
    vols = []
    for i in range(window, len(returns) + 1):
        chunk = returns[i - window:i]
        vols.append(np.std(chunk, ddof=1) * np.sqrt(TRADING_DAYS))
    return np.array(vols)


class OptionsVolPod(BaseStrategyPod):

    def __init__(self) -> None:
        super().__init__(PodName.OPTIONS_VOL)
        self._svc = get_market_data_service()

    def generate_signals(self, context: dict[str, Any]) -> list[dict[str, Any]]:
        regime = context.get("regime", RegimeState.BULL)
        signals: list[dict[str, Any]] = []

        # ------------------------------------------------------------------ #
        # 1. Fetch SPY returns (1 year lookback)                             #
        # ------------------------------------------------------------------ #
        try:
            spy_returns = self._svc.get_returns("SPY", period="1y")
        except Exception as exc:
            logger.error("options_vol: failed to fetch SPY returns: %s", exc)
            return signals

        if len(spy_returns) < 30:
            logger.warning("options_vol: insufficient SPY return history (%d rows)", len(spy_returns))
            return signals

        # ------------------------------------------------------------------ #
        # 2. VRP signal: realized vol vs. historical median                  #
        # ------------------------------------------------------------------ #
        rv_30d = _annualized_vol(spy_returns[-30:])
        # Historical median of rolling 30-day realized vols (full year)
        rolling_30d = _rolling_vol(spy_returns, 30)
        if len(rolling_30d) < 10:
            logger.warning("options_vol: not enough rolling vol samples")
            return signals

        hist_median_rv = float(np.median(rolling_30d))

        # Regime multiplier — vol selling is riskier in bear/crisis
        vrp_regime_mult = {
            RegimeState.BULL: 1.0,
            RegimeState.RANGE: 0.8,
            RegimeState.BEAR: 0.3,
            RegimeState.CRISIS: -0.5,
        }.get(regime, 0.5)

        vrp_spread = rv_30d - hist_median_rv  # + means current vol is elevated

        if abs(vrp_spread) > 0.01:
            if vrp_spread < 0:
                # Current vol below median → implied vol likely rich → sell vol
                direction = SignalDirection.SHORT
                raw_strength = min(abs(vrp_spread) * 8.0, 1.0) * max(vrp_regime_mult, 0.0)
                strength = -raw_strength
            else:
                # Current vol above median → buy protection
                direction = SignalDirection.LONG
                strength = min(vrp_spread * 8.0, 1.0)

            confidence = float(np.clip(0.65 + abs(vrp_spread) * 2.0, 0.60, 0.90))

            signals.append({
                "asset": "SPY",
                "signal_name": "vrp_realized_vol",
                "direction": direction.value,
                "strength": round(float(strength), 4),
                "confidence": round(confidence, 4),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "metadata": {
                    "rv_30d": round(rv_30d, 4),
                    "hist_median_rv": round(hist_median_rv, 4),
                    "vrp_spread": round(vrp_spread, 4),
                    "regime": regime.value if hasattr(regime, "value") else str(regime),
                    "signal_type": "vrp",
                    "instrument": "short_straddle" if vrp_spread < 0 else "long_strangle",
                },
            })

        # ------------------------------------------------------------------ #
        # 3. Tail hedge: always add a small protective signal when vol > 25% #
        # ------------------------------------------------------------------ #
        if rv_30d > 0.25:
            hedge_strength = float(np.clip((rv_30d - 0.25) / 0.25, 0.0, 1.0)) * 0.5
            signals.append({
                "asset": "SPY",
                "signal_name": "tail_hedge_high_vol",
                "direction": SignalDirection.LONG.value,
                "strength": round(hedge_strength, 4),
                "confidence": round(float(np.clip(0.65 + (rv_30d - 0.25) * 1.5, 0.65, 0.92)), 4),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "metadata": {
                    "rv_30d": round(rv_30d, 4),
                    "trigger_threshold": 0.25,
                    "strike_moneyness": "-5%",
                    "expiry_days": 90,
                    "signal_type": "tail_hedge",
                },
            })

        # ------------------------------------------------------------------ #
        # 4. Vol term structure: compare 10-day vs 30-day vs 60-day RV      #
        # ------------------------------------------------------------------ #
        if len(spy_returns) >= 60:
            rv_10d = _annualized_vol(spy_returns[-10:])
            rv_60d = _annualized_vol(spy_returns[-60:])
            # Contango proxy: short-term vol < long-term vol → normal → sell front vol
            term_slope = rv_60d - rv_10d
            if abs(term_slope) > 0.015:
                if term_slope > 0:
                    # Contango: near vol cheap, far vol rich → sell back-month vol (short)
                    ts_direction = SignalDirection.SHORT
                    ts_strength = -float(np.clip(term_slope * 6.0, 0.0, 0.7))
                else:
                    # Backwardation: near vol spiked → buy near protection
                    ts_direction = SignalDirection.LONG
                    ts_strength = float(np.clip(abs(term_slope) * 6.0, 0.0, 0.7))

                signals.append({
                    "asset": "VIX_FUTURES",
                    "signal_name": "vol_term_structure_slope",
                    "direction": ts_direction.value,
                    "strength": round(ts_strength, 4),
                    "confidence": round(float(np.clip(0.58 + abs(term_slope) * 2.0, 0.55, 0.80)), 4),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "metadata": {
                        "rv_10d": round(rv_10d, 4),
                        "rv_60d": round(rv_60d, 4),
                        "term_slope": round(term_slope, 4),
                        "structure": "contango" if term_slope > 0 else "backwardation",
                        "signal_type": "term_structure",
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
