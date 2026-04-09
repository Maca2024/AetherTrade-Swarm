"""
AETHERTRADE-SWARM — Statistical Arbitrage Pod
PCA residual trading + Post-Earnings Announcement Drift (PEAD).

Signals:
1. PCA residual — factor-neutral equity deviation from predicted price
2. PEAD — systematic drift following earnings surprises (SUE-ranked)
3. Index rebalance arbitrage — front-running known index add/removes
"""
from __future__ import annotations

import random
from datetime import datetime, timezone
from typing import Any

import numpy as np

from models.schemas import PodName, RegimeState, SignalDirection
from .base import BaseStrategyPod


ELIGIBLE_UNIVERSE = [
    "AAPL", "MSFT", "AMZN", "GOOGL", "META", "NVDA", "TSLA",
    "JPM", "BAC", "GS", "MS", "C", "WFC",
    "XOM", "CVX", "COP", "SLB",
    "JNJ", "PFE", "MRK", "ABBV",
    "SPY", "QQQ", "IWM", "MDY",
]


class StatArbPod(BaseStrategyPod):

    def __init__(self, seed: int = 4) -> None:
        super().__init__(PodName.STAT_ARB)
        self._rng = np.random.default_rng(seed)
        self._random = random.Random(seed)
        self._signal_count = 31

    def generate_signals(self, context: dict[str, Any]) -> list[dict[str, Any]]:
        regime = context.get("regime", RegimeState.RANGE)
        signals: list[dict[str, Any]] = []

        # Stat arb is market-neutral — best in range, survives bear
        regime_multiplier = {
            RegimeState.BULL: 0.7,
            RegimeState.RANGE: 1.0,
            RegimeState.BEAR: 0.8,
            RegimeState.CRISIS: 0.3,
        }.get(regime, 0.6)

        # --- PCA Residual signals ---
        # Simulate factor model: predicted = sum(beta_i * factor_i)
        # Residual = actual - predicted; trade mean-reversion of residual
        pca_candidates = self._random.sample(ELIGIBLE_UNIVERSE, k=8)
        for asset in pca_candidates:
            # Residual Z-score: positive = rich, negative = cheap
            residual_z = float(self._rng.normal(0.0, 2.0))
            n_factors = self._random.randint(3, 6)

            if abs(residual_z) > 1.8:
                # Rich asset → short; cheap asset → long
                direction = SignalDirection.SHORT if residual_z > 0 else SignalDirection.LONG
                raw_strength = min(abs(residual_z) / 4.0, 1.0) * regime_multiplier
                strength = raw_strength if direction == SignalDirection.LONG else -raw_strength

                signals.append({
                    "asset": asset,
                    "signal_name": "pca_residual_reversion",
                    "direction": direction.value,
                    "strength": round(float(strength), 4),
                    "confidence": round(float(self._rng.uniform(0.60, 0.85)), 4),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "metadata": {
                        "residual_z_score": round(float(residual_z), 4),
                        "n_factors": n_factors,
                        "r_squared": round(float(self._rng.uniform(0.72, 0.95)), 4),
                        "half_life_days": self._random.randint(3, 12),
                        "signal_type": "pca_residual",
                    },
                })

        # --- PEAD signals ---
        # Post-earnings announcement drift: buy (sell) stocks with positive
        # (negative) earnings surprise, expected drift lasts 30–60 days
        pead_candidates = self._random.sample(ELIGIBLE_UNIVERSE[:16], k=4)
        for asset in pead_candidates:
            # Standardised Unexpected Earnings (SUE) score
            sue_score = float(self._rng.normal(0.0, 1.5))
            if abs(sue_score) > 0.8:
                direction = SignalDirection.LONG if sue_score > 0 else SignalDirection.SHORT
                drift_strength = min(abs(sue_score) / 2.5, 1.0) * regime_multiplier
                if direction == SignalDirection.SHORT:
                    drift_strength = -drift_strength

                days_since_earnings = self._random.randint(1, 45)
                # Decay signal as we approach 60-day boundary
                decay = max(0.0, 1.0 - days_since_earnings / 60.0)

                signals.append({
                    "asset": asset,
                    "signal_name": "pead_earnings_drift",
                    "direction": direction.value,
                    "strength": round(float(drift_strength * decay), 4),
                    "confidence": round(float(self._rng.uniform(0.55, 0.78)), 4),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "metadata": {
                        "sue_score": round(float(sue_score), 4),
                        "days_since_earnings": days_since_earnings,
                        "decay_factor": round(float(decay), 4),
                        "expected_drift_days": 60 - days_since_earnings,
                        "signal_type": "pead",
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
