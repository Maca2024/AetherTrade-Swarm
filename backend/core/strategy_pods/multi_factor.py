"""
AETHERTRADE-SWARM — Multi-Factor Pod (AQR-style)
Systematic long/short across Value, Quality, Momentum, Low-Volatility factors.

Signals:
1. Value — book/price, earnings yield, cash flow yield
2. Quality — ROE, gross margin, accruals, leverage
3. Momentum — 12-1 cross-sectional (synced with momentum pod, different sizing)
4. Low-Volatility — minimum variance, beta-sorted decile
5. Composite Z-score — equal-weighted factor combination
"""
from __future__ import annotations

import random
from datetime import datetime, timezone
from typing import Any

import numpy as np

from models.schemas import PodName, RegimeState, SignalDirection
from .base import BaseStrategyPod


FACTOR_UNIVERSE = [
    "AAPL", "MSFT", "AMZN", "GOOGL", "META", "NVDA", "TSLA",
    "JPM", "BAC", "WFC", "GS", "BRK-B",
    "JNJ", "PFE", "ABBV", "UNH",
    "XOM", "CVX", "NEE",
    "PG", "KO", "PEP", "MCD",
    "HD", "LOW", "TGT",
    "SPY", "IWM",
]

FACTORS = ["value", "quality", "momentum", "low_volatility"]


class MultiFactorPod(BaseStrategyPod):

    def __init__(self, seed: int = 8) -> None:
        super().__init__(PodName.MULTI_FACTOR)
        self._rng = np.random.default_rng(seed)
        self._random = random.Random(seed)
        self._signal_count = 42

    def generate_signals(self, context: dict[str, Any]) -> list[dict[str, Any]]:
        regime = context.get("regime", RegimeState.BULL)
        signals: list[dict[str, Any]] = []

        # Factor tilts adjust by regime
        factor_tilts = self._regime_factor_tilts(regime)

        # Score each asset across all factors
        selected_assets = self._random.sample(FACTOR_UNIVERSE, k=12)

        for asset in selected_assets:
            factor_scores: dict[str, float] = {}

            # Simulate individual factor z-scores for this asset
            for factor in FACTORS:
                raw_z = float(self._rng.normal(0.0, 1.2))
                tilt = factor_tilts.get(factor, 1.0)
                factor_scores[factor] = round(float(raw_z * tilt), 4)

            # Composite z-score (equal weight)
            composite_z = float(np.mean(list(factor_scores.values())))

            # Only trade if composite score is material
            if abs(composite_z) < 0.5:
                continue

            direction = SignalDirection.LONG if composite_z > 0 else SignalDirection.SHORT
            # Strength: tanh scaling so extremes don't blow out
            strength = float(np.tanh(composite_z * 0.8))

            signals.append({
                "asset": asset,
                "signal_name": "multi_factor_composite",
                "direction": direction.value,
                "strength": round(float(strength), 4),
                "confidence": round(float(self._rng.uniform(0.58, 0.88)), 4),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "metadata": {
                    "composite_z": round(float(composite_z), 4),
                    "factor_scores": factor_scores,
                    "active_factors": FACTORS,
                    "regime_tilts": factor_tilts,
                    "signal_type": "multi_factor",
                    "rebalance_freq": "monthly",
                },
            })

        # Top/bottom decile: explicitly label long-short book
        long_signals = sorted(
            [s for s in signals if s["direction"] == SignalDirection.LONG.value],
            key=lambda s: s["strength"],
            reverse=True,
        )[:4]
        short_signals = sorted(
            [s for s in signals if s["direction"] == SignalDirection.SHORT.value],
            key=lambda s: s["strength"],
        )[:4]

        # Mark top longs and shorts with "top_decile" flag
        for sig in long_signals + short_signals:
            sig["metadata"]["decile"] = "top_long" if sig["direction"] == SignalDirection.LONG.value else "top_short"

        return signals

    def _regime_factor_tilts(self, regime: RegimeState) -> dict[str, float]:
        """
        Returns scaling multipliers per factor based on regime.
        Factor performance is regime-dependent (e.g., momentum fails in bear).
        """
        tilts = {
            RegimeState.BULL: {
                "value": 0.8,
                "quality": 0.9,
                "momentum": 1.2,
                "low_volatility": 0.7,
            },
            RegimeState.RANGE: {
                "value": 1.1,
                "quality": 1.0,
                "momentum": 0.6,
                "low_volatility": 1.1,
            },
            RegimeState.BEAR: {
                "value": 1.2,
                "quality": 1.3,
                "momentum": 0.4,
                "low_volatility": 1.4,
            },
            RegimeState.CRISIS: {
                "value": 0.5,
                "quality": 1.5,
                "momentum": 0.2,
                "low_volatility": 1.8,
            },
        }
        return tilts.get(regime, {f: 1.0 for f in FACTORS})

    def get_metrics(self) -> dict[str, Any]:
        return {
            "pod_name": self.pod_name,
            "status": "active",
            "signal_count": self._signal_count,
            "uptime_seconds": round(self.uptime_seconds, 1),
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }
