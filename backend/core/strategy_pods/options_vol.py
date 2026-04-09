"""
AETHERTRADE-SWARM — Options & Volatility Pod
Volatility Risk Premium (VRP) harvesting + Tail Hedge management.

Signals:
1. VRP — sell implied vol when IV > realised vol (normalised spread)
2. Skew arb — exploit put/call skew mispricing
3. Tail hedge — buy cheap convexity in low-vol regimes
4. Term structure roll — harvest theta from vol futures contango
"""
from __future__ import annotations

import random
from datetime import datetime, timezone
from typing import Any

import numpy as np

from models.schemas import PodName, RegimeState, SignalDirection
from .base import BaseStrategyPod


# VIX-proxy term structure nodes (days to expiry → simulated mid-IV)
VOL_TERM_NODES = [7, 14, 30, 60, 90, 180]
VOL_UNDERLYINGS = ["SPY", "QQQ", "IWM", "GLD", "TLT", "USO", "EEM"]


class OptionsVolPod(BaseStrategyPod):

    def __init__(self, seed: int = 5) -> None:
        super().__init__(PodName.OPTIONS_VOL)
        self._rng = np.random.default_rng(seed)
        self._random = random.Random(seed)
        self._signal_count = 8

    def generate_signals(self, context: dict[str, Any]) -> list[dict[str, Any]]:
        regime = context.get("regime", RegimeState.BULL)
        signals: list[dict[str, Any]] = []

        # VRP: best when IV consistently > RV → sell vol in calm regimes
        vrp_regime_mult = {
            RegimeState.BULL: 1.0,
            RegimeState.RANGE: 0.8,
            RegimeState.BEAR: 0.3,
            RegimeState.CRISIS: -0.5,  # Vol spike → buy vol
        }.get(regime, 0.5)

        # --- VRP signals ---
        for underlying in self._random.sample(VOL_UNDERLYINGS, k=3):
            # Implied vol (annualised fraction)
            iv_30d = float(self._rng.uniform(0.12, 0.40))
            # Realised vol over past 30 days
            rv_30d = float(self._rng.uniform(0.09, 0.35))
            vrp = iv_30d - rv_30d  # Positive = IV rich → sell

            if abs(vrp) > 0.02:
                if vrp > 0:
                    # IV rich → short vega (sell straddles/calls)
                    direction = SignalDirection.SHORT
                    strength = min(vrp * 5.0, 1.0) * max(vrp_regime_mult, 0.0)
                    strength = -strength
                else:
                    # IV cheap → long vega (buy protection)
                    direction = SignalDirection.LONG
                    strength = min(abs(vrp) * 5.0, 1.0)

                signals.append({
                    "asset": underlying,
                    "signal_name": "vrp_vega_harvest",
                    "direction": direction.value,
                    "strength": round(float(strength), 4),
                    "confidence": round(float(self._rng.uniform(0.60, 0.85)), 4),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "metadata": {
                        "iv_30d": round(float(iv_30d), 4),
                        "rv_30d": round(float(rv_30d), 4),
                        "vrp": round(float(vrp), 4),
                        "signal_type": "vrp",
                        "instrument": "short_straddle" if vrp > 0 else "long_strangle",
                    },
                })

        # --- Tail hedge signal ---
        # In low-vol bull regimes, buy cheap OTM puts for convexity
        vix_proxy = float(self._rng.uniform(12.0, 35.0))
        if regime == RegimeState.BULL and vix_proxy < 18.0:
            hedge_strength = (18.0 - vix_proxy) / 18.0 * 0.6
            signals.append({
                "asset": "SPY",
                "signal_name": "tail_hedge_otm_put",
                "direction": SignalDirection.LONG.value,
                "strength": round(float(hedge_strength), 4),
                "confidence": round(float(self._rng.uniform(0.70, 0.90)), 4),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "metadata": {
                    "vix_proxy": round(float(vix_proxy), 2),
                    "strike_moneyness": "-5%",
                    "expiry_days": 90,
                    "signal_type": "tail_hedge",
                    "cost_bps": round(float(self._rng.uniform(3.0, 12.0)), 2),
                },
            })
        elif regime == RegimeState.CRISIS:
            # Crisis → monetise hedges
            signals.append({
                "asset": "SPY",
                "signal_name": "tail_hedge_monetise",
                "direction": SignalDirection.SHORT.value,
                "strength": round(float(-self._rng.uniform(0.5, 0.9)), 4),
                "confidence": round(float(self._rng.uniform(0.75, 0.95)), 4),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "metadata": {
                    "vix_proxy": round(float(vix_proxy), 2),
                    "action": "close_hedge_take_profit",
                    "signal_type": "tail_hedge_exit",
                },
            })

        # --- Vol term structure roll ---
        front_iv = float(self._rng.uniform(0.15, 0.45))
        back_iv = front_iv + float(self._rng.normal(0.02, 0.03))  # Contango typical
        contango_bps = (back_iv - front_iv) * 10000
        if contango_bps > 100:  # Meaningful roll yield
            signals.append({
                "asset": "VIX_FUTURES",
                "signal_name": "vol_term_structure_roll",
                "direction": SignalDirection.SHORT.value,
                "strength": round(float(-min(contango_bps / 500.0, 0.8)), 4),
                "confidence": round(float(self._rng.uniform(0.58, 0.78)), 4),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "metadata": {
                    "front_month_iv": round(float(front_iv), 4),
                    "back_month_iv": round(float(back_iv), 4),
                    "contango_bps": round(float(contango_bps), 1),
                    "signal_type": "term_structure_roll",
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
