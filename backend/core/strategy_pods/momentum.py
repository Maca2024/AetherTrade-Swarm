"""
AetherTrade-Swarm — Vol-Scaled Momentum Pod
Real 12-1 cross-sectional momentum + TSMOM from yfinance data.

Signals:
1. 12-1 cross-sectional momentum (long top quintile, short bottom)
2. Time-series TSMOM (sign of past return, vol-scaled)
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import numpy as np

from data.market_data import get_market_data_service, EQUITY_UNIVERSE, ETF_UNIVERSE
from models.schemas import PodName, RegimeState, SignalDirection
from .base import BaseStrategyPod

logger = logging.getLogger("aethertrade.pod.momentum")

UNIVERSE = EQUITY_UNIVERSE + ETF_UNIVERSE[:4]


class MomentumPod(BaseStrategyPod):

    def __init__(self) -> None:
        super().__init__(PodName.MOMENTUM)
        self._vol_target = 0.12

    def generate_signals(self, context: dict[str, Any]) -> list[dict[str, Any]]:
        regime = context.get("regime", RegimeState.BULL)
        mds = get_market_data_service()
        signals = []

        regime_multiplier = {
            RegimeState.BULL: 1.0,
            RegimeState.RANGE: 0.4,
            RegimeState.BEAR: 0.2,
            RegimeState.CRISIS: 0.05,
        }.get(regime, 0.5)

        # 12-1 Cross-Sectional Momentum from real price data
        momentum_scores: list[tuple[str, float]] = []
        for symbol in UNIVERSE:
            try:
                data = mds.fetch_daily(symbol, "1y")
                closes = [d["close"] for d in data.get("data", [])]
                if len(closes) < 252:
                    continue
                ret_12_1 = (closes[-21] / closes[0]) - 1.0
                momentum_scores.append((symbol, ret_12_1))
            except Exception:
                continue

        if len(momentum_scores) >= 6:
            momentum_scores.sort(key=lambda x: x[1], reverse=True)
            n = max(len(momentum_scores) // 5, 2)

            for symbol, score in momentum_scores[:n]:
                strength = min(abs(score) * regime_multiplier, 1.0)
                signals.append({
                    "asset": symbol,
                    "signal_name": "crosssectional_momentum_12_1",
                    "direction": SignalDirection.LONG.value,
                    "strength": round(strength, 4),
                    "confidence": round(min(0.5 + abs(score), 0.95), 4),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "metadata": {"return_12_1": round(score, 4), "rank": "top_quintile"},
                })

            for symbol, score in momentum_scores[-n:]:
                strength = -min(abs(score) * regime_multiplier, 1.0)
                signals.append({
                    "asset": symbol,
                    "signal_name": "crosssectional_momentum_12_1",
                    "direction": SignalDirection.SHORT.value,
                    "strength": round(strength, 4),
                    "confidence": round(min(0.5 + abs(score), 0.90), 4),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "metadata": {"return_12_1": round(score, 4), "rank": "bottom_quintile"},
                })

        # TSMOM on SPY from real data
        try:
            spy_returns = mds.get_returns("SPY", "1y")
            if len(spy_returns) >= 252:
                past_return = float(np.sum(spy_returns[-252:]))
                vol = float(np.std(spy_returns[-60:]) * np.sqrt(252))
                vol_scale = self._vol_target / vol if vol > 0 else 1.0
                tsmom_strength = np.sign(past_return) * min(abs(past_return) * vol_scale, 1.0) * regime_multiplier

                signals.append({
                    "asset": "SPY",
                    "signal_name": "tsmom_252",
                    "direction": SignalDirection.LONG.value if tsmom_strength > 0 else SignalDirection.SHORT.value,
                    "strength": round(float(tsmom_strength), 4),
                    "confidence": round(min(0.6 + abs(past_return) * 0.5, 0.90), 4),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "metadata": {
                        "past_return_252d": round(past_return, 4),
                        "realized_vol": round(vol, 4),
                        "vol_scale": round(vol_scale, 4),
                    },
                })
        except Exception as exc:
            logger.debug("TSMOM error: %s", exc)

        self._signal_count = len(signals)
        return signals

    def get_metrics(self) -> dict[str, Any]:
        return {
            "pod_name": self.pod_name,
            "status": "active",
            "signal_count": self._signal_count,
            "vol_target": self._vol_target,
            "universe_size": len(UNIVERSE),
            "uptime_seconds": round(self.uptime_seconds, 1),
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }
