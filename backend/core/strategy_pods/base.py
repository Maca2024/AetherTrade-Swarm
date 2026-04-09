"""
AETHERTRADE-SWARM — Abstract Base Strategy Pod
All 9 strategy pods inherit from this base.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any

from models.schemas import PodName, SignalDirection


class BaseStrategyPod(ABC):
    """
    Abstract base class for AETHERTRADE-SWARM strategy pods.

    Each pod:
    - Has a unique name (PodName enum value)
    - Generates signals from market data
    - Reports its current metrics
    - Is regime-aware (adjusts signal generation based on market regime)
    """

    def __init__(self, name: PodName) -> None:
        self.name = name
        self._initialized_at = datetime.now(timezone.utc)
        self._signal_count = 0

    @abstractmethod
    def generate_signals(self, context: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Generate trading signals from market context.

        context should contain:
          - regime: RegimeState
          - market_data: dict of price/vol data
          - lookback_returns: list of recent returns

        Returns list of signal dicts with keys:
          asset, signal_name, direction, strength, confidence, metadata
        """
        ...

    @abstractmethod
    def get_metrics(self) -> dict[str, Any]:
        """Return current performance metrics for this pod."""
        ...

    def get_aggregate_signal(self, signals: list[dict[str, Any]]) -> tuple[SignalDirection, float]:
        """
        Compute aggregate direction and strength from a list of signals.
        Weighted by confidence.
        """
        if not signals:
            return SignalDirection.NEUTRAL, 0.0

        total_weight = sum(s.get("confidence", 0.5) for s in signals)
        if total_weight == 0:
            return SignalDirection.NEUTRAL, 0.0

        weighted_strength = sum(
            s.get("strength", 0.0) * s.get("confidence", 0.5)
            for s in signals
        ) / total_weight

        if weighted_strength > 0.08:
            direction = SignalDirection.LONG
        elif weighted_strength < -0.08:
            direction = SignalDirection.SHORT
        else:
            direction = SignalDirection.NEUTRAL

        return direction, round(weighted_strength, 4)

    @property
    def pod_name(self) -> str:
        return self.name.value

    @property
    def uptime_seconds(self) -> float:
        return (datetime.now(timezone.utc) - self._initialized_at).total_seconds()
