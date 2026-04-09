"""
AETHERTRADE-SWARM — Behavioral / Sentiment Pod
Exploits cognitive biases and sentiment extremes in market participants.

Signals:
1. Sentiment composite — aggregated bull/bear sentiment from positioning data
2. Contrarian reversal — extreme fear/greed readings trigger fade signals
3. Herding score — crowd divergence creates short-term alpha
4. Disposition effect — retail selling pressure after gains (overestimated)
"""
from __future__ import annotations

import random
from datetime import datetime, timezone
from typing import Any

import numpy as np

from models.schemas import PodName, RegimeState, SignalDirection
from .base import BaseStrategyPod


SENTIMENT_ASSETS = ["SPY", "QQQ", "IWM", "AAPL", "TSLA", "AMZN", "NVDA", "BTC", "ETH"]
SENTIMENT_SOURCES = [
    "AAII_bull_bear_spread",
    "CNN_fear_greed",
    "put_call_ratio",
    "NAAIM_exposure",
    "twitter_sentiment",
    "options_skew",
]


class BehavioralPod(BaseStrategyPod):

    def __init__(self, seed: int = 6) -> None:
        super().__init__(PodName.BEHAVIORAL)
        self._rng = np.random.default_rng(seed)
        self._random = random.Random(seed)
        self._signal_count = 15

    def generate_signals(self, context: dict[str, Any]) -> list[dict[str, Any]]:
        regime = context.get("regime", RegimeState.BULL)
        signals: list[dict[str, Any]] = []

        # Contrarian works well in extremes — dampened in crisis (rational fear)
        regime_multiplier = {
            RegimeState.BULL: 0.8,   # Moderate greed → modest contrarian
            RegimeState.RANGE: 1.0,  # Best environment: sentiment swings
            RegimeState.BEAR: 0.9,
            RegimeState.CRISIS: 0.4, # Extreme fear can persist
        }.get(regime, 0.7)

        # --- Sentiment composite ---
        # Composite ranges -100 (extreme fear) to +100 (extreme greed)
        sentiment_composite = float(self._rng.normal(0.0, 35.0))
        sentiment_composite = float(np.clip(sentiment_composite, -100.0, 100.0))

        # Contrarian: extreme readings predict reversal
        if abs(sentiment_composite) > 55.0:
            # Fade the crowd
            direction = SignalDirection.SHORT if sentiment_composite > 0 else SignalDirection.LONG
            contrarian_strength = min(abs(sentiment_composite) / 100.0, 1.0) * regime_multiplier
            if direction == SignalDirection.SHORT:
                contrarian_strength = -contrarian_strength

            signals.append({
                "asset": "SPY",
                "signal_name": "sentiment_contrarian_fade",
                "direction": direction.value,
                "strength": round(float(contrarian_strength), 4),
                "confidence": round(float(self._rng.uniform(0.58, 0.80)), 4),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "metadata": {
                    "sentiment_composite": round(float(sentiment_composite), 2),
                    "source_count": len(SENTIMENT_SOURCES),
                    "signal_type": "contrarian",
                    "extreme_threshold": 55.0,
                },
            })

        # --- Put/Call ratio contrarian ---
        put_call_ratio = float(self._rng.uniform(0.6, 1.8))
        if put_call_ratio > 1.4:
            # Extreme put buying → contrarian long
            pc_strength = min((put_call_ratio - 1.4) / 0.6, 1.0) * regime_multiplier
            signals.append({
                "asset": "SPY",
                "signal_name": "put_call_contrarian_long",
                "direction": SignalDirection.LONG.value,
                "strength": round(float(pc_strength), 4),
                "confidence": round(float(self._rng.uniform(0.60, 0.78)), 4),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "metadata": {
                    "put_call_ratio": round(float(put_call_ratio), 4),
                    "signal_type": "put_call_contrarian",
                    "interpretation": "excessive_hedging",
                },
            })
        elif put_call_ratio < 0.75:
            # Extreme call buying → contrarian short
            pc_strength = min((0.75 - put_call_ratio) / 0.25, 1.0) * regime_multiplier
            signals.append({
                "asset": "SPY",
                "signal_name": "put_call_contrarian_short",
                "direction": SignalDirection.SHORT.value,
                "strength": round(float(-pc_strength), 4),
                "confidence": round(float(self._rng.uniform(0.60, 0.78)), 4),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "metadata": {
                    "put_call_ratio": round(float(put_call_ratio), 4),
                    "signal_type": "put_call_contrarian",
                    "interpretation": "complacency_risk",
                },
            })

        # --- Herding / crowding score per stock ---
        crowded_assets = self._random.sample(SENTIMENT_ASSETS, k=4)
        for asset in crowded_assets:
            # Crowding score: 0 = uncrowded, 1 = max crowded
            crowding = float(self._rng.uniform(0.0, 1.0))
            if crowding > 0.75:
                # Over-crowded long → fade / reduce
                fade_strength = (crowding - 0.75) / 0.25 * 0.6 * regime_multiplier
                signals.append({
                    "asset": asset,
                    "signal_name": "crowding_fade",
                    "direction": SignalDirection.SHORT.value,
                    "strength": round(float(-fade_strength), 4),
                    "confidence": round(float(self._rng.uniform(0.50, 0.72)), 4),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "metadata": {
                        "crowding_score": round(float(crowding), 4),
                        "signal_type": "herding_contrarian",
                        "percentile_rank": round(float(crowding * 100), 1),
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
