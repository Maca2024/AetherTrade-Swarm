"""
AETHERTRADE-SWARM — Signal Aggregation Engine
Combines signals from all 9 strategy pods into a single ensemble signal.
Applies regime-based weight adjustments and confidence weighting.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import numpy as np

from models.schemas import PodName, RegimeState, SignalDirection

logger = logging.getLogger("oracle.signal_engine")


# Base weights per pod (sum = 1.0)
BASE_WEIGHTS: dict[PodName, float] = {
    PodName.MOMENTUM:       0.15,
    PodName.MEAN_REVERSION: 0.10,
    PodName.MACRO:          0.12,
    PodName.STAT_ARB:       0.10,
    PodName.OPTIONS_VOL:    0.10,
    PodName.BEHAVIORAL:     0.08,
    PodName.AI_ML:          0.13,
    PodName.MULTI_FACTOR:   0.12,
    PodName.MARKET_MAKING:  0.10,
}

# Regime overlays — multiplicative adjustment to base weights
REGIME_OVERLAYS: dict[RegimeState, dict[PodName, float]] = {
    RegimeState.BULL: {
        PodName.MOMENTUM:       1.50,
        PodName.MEAN_REVERSION: 0.50,
        PodName.MACRO:          1.00,
        PodName.STAT_ARB:       0.50,
        PodName.OPTIONS_VOL:    0.50,
        PodName.BEHAVIORAL:     1.20,
        PodName.AI_ML:          1.20,
        PodName.MULTI_FACTOR:   1.30,
        PodName.MARKET_MAKING:  0.80,
    },
    RegimeState.RANGE: {
        PodName.MOMENTUM:       0.40,
        PodName.MEAN_REVERSION: 2.00,
        PodName.MACRO:          0.80,
        PodName.STAT_ARB:       2.00,
        PodName.OPTIONS_VOL:    1.20,
        PodName.BEHAVIORAL:     1.00,
        PodName.AI_ML:          1.00,
        PodName.MULTI_FACTOR:   0.50,
        PodName.MARKET_MAKING:  1.50,
    },
    RegimeState.BEAR: {
        PodName.MOMENTUM:       0.30,
        PodName.MEAN_REVERSION: 1.50,
        PodName.MACRO:          1.80,
        PodName.STAT_ARB:       1.20,
        PodName.OPTIONS_VOL:    2.00,
        PodName.BEHAVIORAL:     0.60,
        PodName.AI_ML:          1.10,
        PodName.MULTI_FACTOR:   0.40,
        PodName.MARKET_MAKING:  1.00,
    },
    RegimeState.CRISIS: {
        PodName.MOMENTUM:       0.10,
        PodName.MEAN_REVERSION: 0.80,
        PodName.MACRO:          2.50,
        PodName.STAT_ARB:       0.60,
        PodName.OPTIONS_VOL:    3.00,
        PodName.BEHAVIORAL:     0.30,
        PodName.AI_ML:          0.80,
        PodName.MULTI_FACTOR:   0.20,
        PodName.MARKET_MAKING:  0.20,
    },
}


class SignalEngine:
    """
    Aggregates signals from all 9 pods into a regime-aware ensemble.
    """

    def compute_regime_weights(self, regime: RegimeState) -> dict[PodName, float]:
        """Apply regime overlay to base weights and normalise to sum=1."""
        overlay = REGIME_OVERLAYS.get(regime, {p: 1.0 for p in PodName})
        raw = {pod: BASE_WEIGHTS[pod] * overlay.get(pod, 1.0) for pod in PodName}
        total = sum(raw.values())
        if total == 0:
            return BASE_WEIGHTS.copy()
        return {pod: w / total for pod, w in raw.items()}

    def aggregate_signals(
        self,
        pod_signals: dict[str, dict[str, Any]],
        regime: RegimeState,
    ) -> dict[str, Any]:
        """
        Combine pod-level aggregate signals into an ensemble signal.

        pod_signals: {pod_name: {"aggregate_strength": float, "aggregate_direction": str, ...}}
        Returns ensemble signal dict.
        """
        weights = self.compute_regime_weights(regime)
        contributions: dict[str, float] = {}
        weighted_strength = 0.0
        total_weight = 0.0

        for pod in PodName:
            pod_data = pod_signals.get(pod.value, {})
            strength = float(pod_data.get("aggregate_strength", 0.0))
            weight = weights.get(pod, 0.0)
            contribution = weight * strength
            contributions[pod.value] = round(contribution, 6)
            weighted_strength += contribution
            total_weight += weight

        if total_weight > 0:
            ensemble_strength = weighted_strength
        else:
            ensemble_strength = 0.0

        # Determine direction
        if ensemble_strength > 0.06:
            direction = SignalDirection.LONG
        elif ensemble_strength < -0.06:
            direction = SignalDirection.SHORT
        else:
            direction = SignalDirection.NEUTRAL

        # Confidence: based on agreement across pods
        pod_directions = []
        for pod in PodName:
            pod_data = pod_signals.get(pod.value, {})
            pod_directions.append(pod_data.get("aggregate_direction", SignalDirection.NEUTRAL.value))

        if direction != SignalDirection.NEUTRAL:
            agreement = sum(1 for d in pod_directions if d == direction.value)
            confidence = min(0.95, 0.5 + agreement / len(pod_directions) * 0.5)
        else:
            confidence = 0.55

        return {
            "ensemble_direction": direction.value,
            "ensemble_strength": round(ensemble_strength, 6),
            "regime_adjusted": True,
            "pod_contributions": contributions,
            "confidence": round(confidence, 4),
            "regime_weights": {pod.value: round(w, 4) for pod, w in weights.items()},
        }


# Singleton
_engine: SignalEngine | None = None


def get_signal_engine() -> SignalEngine:
    global _engine
    if _engine is None:
        _engine = SignalEngine()
    return _engine
