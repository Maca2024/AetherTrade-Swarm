"""
AETHERTRADE-SWARM — Behavioral / Sentiment Pod
Exploits price-based behavioral patterns: momentum divergence, volume spikes,
consecutive down-day oversold conditions.

Signals driven by REAL market data:
1. Momentum divergence: 5-day negative vs. 20-day positive → contrarian long
2. Volume spike: today's volume > 2x 20-day average → reversal signal
3. Consecutive down days: > 3 days consecutive lower closes → oversold long
Applies to SPY, QQQ, AAPL, MSFT, NVDA, TSLA.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import numpy as np

from data.market_data import get_market_data_service
from models.schemas import PodName, RegimeState, SignalDirection
from .base import BaseStrategyPod

logger = logging.getLogger("aethertrade.behavioral")

BEHAVIORAL_ASSETS = ["SPY", "QQQ", "AAPL", "MSFT", "NVDA", "TSLA"]


class BehavioralPod(BaseStrategyPod):

    def __init__(self) -> None:
        super().__init__(PodName.BEHAVIORAL)
        self._svc = get_market_data_service()

    def generate_signals(self, context: dict[str, Any]) -> list[dict[str, Any]]:
        regime = context.get("regime", RegimeState.BULL)
        signals: list[dict[str, Any]] = []

        # Contrarian signals work best in range-bound markets; dampen in crisis
        regime_multiplier = {
            RegimeState.BULL: 0.8,
            RegimeState.RANGE: 1.0,
            RegimeState.BEAR: 0.9,
            RegimeState.CRISIS: 0.4,
        }.get(regime, 0.7)

        for asset in BEHAVIORAL_ASSETS:
            asset_signals = self._analyze_asset(asset, regime_multiplier)
            signals.extend(asset_signals)

        return signals

    # ---------------------------------------------------------------------- #
    # Per-asset analysis                                                       #
    # ---------------------------------------------------------------------- #

    def _analyze_asset(self, asset: str, regime_mult: float) -> list[dict[str, Any]]:
        signals: list[dict[str, Any]] = []

        try:
            raw = self._svc.fetch_daily(asset, period="3mo")
        except Exception as exc:
            logger.error("behavioral: fetch_daily(%s): %s", asset, exc)
            return signals

        rows = raw.get("data", [])
        if len(rows) < 25:
            logger.warning("behavioral: %s has only %d rows, skipping", asset, len(rows))
            return signals

        closes = np.array([r["close"] for r in rows], dtype=float)
        volumes = np.array([r["volume"] for r in rows], dtype=float)

        # ------------------------------------------------------------------ #
        # Signal 1: Momentum divergence                                       #
        # 5-day return strongly negative AND 20-day return positive           #
        # ------------------------------------------------------------------ #
        ret_5d = float((closes[-1] - closes[-6]) / closes[-6]) if len(closes) >= 6 else 0.0
        ret_20d = float((closes[-1] - closes[-21]) / closes[-21]) if len(closes) >= 21 else 0.0

        if ret_5d < -0.03 and ret_20d > 0.0:
            # Short-term fear in a medium-term uptrend → contrarian long
            divergence_magnitude = abs(ret_5d)
            strength = float(np.clip(divergence_magnitude * 10.0 * regime_mult, 0.0, 1.0))
            confidence = float(np.clip(0.55 + divergence_magnitude * 4.0, 0.55, 0.82))

            signals.append({
                "asset": asset,
                "signal_name": "momentum_divergence_long",
                "direction": SignalDirection.LONG.value,
                "strength": round(strength, 4),
                "confidence": round(confidence, 4),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "metadata": {
                    "ret_5d": round(ret_5d, 4),
                    "ret_20d": round(ret_20d, 4),
                    "signal_type": "momentum_divergence",
                    "interpretation": "short_term_panic_in_uptrend",
                },
            })

        # ------------------------------------------------------------------ #
        # Signal 2: Volume spike — today's volume > 2x 20-day average        #
        # ------------------------------------------------------------------ #
        if len(volumes) >= 21:
            avg_vol_20d = float(np.mean(volumes[-21:-1]))  # exclude today
            today_vol = float(volumes[-1])
            vol_ratio = today_vol / avg_vol_20d if avg_vol_20d > 0 else 0.0

            if vol_ratio > 2.0:
                # Panic selling on spike volume → likely exhaustion → reversal
                # Direction depends on whether today's price dropped
                today_close = closes[-1]
                prev_close = closes[-2]
                day_return = (today_close - prev_close) / prev_close

                if day_return < -0.01:
                    # Volume spike on down day → likely capitulation → long
                    direction = SignalDirection.LONG
                    strength = float(np.clip((vol_ratio - 2.0) / 3.0 * regime_mult, 0.0, 0.8))
                else:
                    # Volume spike on up day → potential exhaustion → short
                    direction = SignalDirection.SHORT
                    strength = -float(np.clip((vol_ratio - 2.0) / 3.0 * regime_mult, 0.0, 0.6))

                confidence = float(np.clip(0.52 + (vol_ratio - 2.0) * 0.06, 0.52, 0.78))

                signals.append({
                    "asset": asset,
                    "signal_name": "volume_spike_reversal",
                    "direction": direction.value,
                    "strength": round(strength, 4),
                    "confidence": round(confidence, 4),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "metadata": {
                        "today_volume": int(today_vol),
                        "avg_vol_20d": round(avg_vol_20d, 0),
                        "vol_ratio": round(vol_ratio, 2),
                        "day_return": round(day_return, 4),
                        "signal_type": "volume_spike",
                        "interpretation": "capitulation" if day_return < -0.01 else "exhaustion",
                    },
                })

        # ------------------------------------------------------------------ #
        # Signal 3: Consecutive down days (> 3) → oversold → long            #
        # ------------------------------------------------------------------ #
        consecutive_down = 0
        for i in range(len(closes) - 1, 0, -1):
            if closes[i] < closes[i - 1]:
                consecutive_down += 1
            else:
                break

        if consecutive_down > 3:
            # Cumulative loss over the streak
            streak_start_close = closes[-(consecutive_down + 1)]
            streak_return = float((closes[-1] - streak_start_close) / streak_start_close)
            strength = float(np.clip(abs(streak_return) * 5.0 * regime_mult, 0.0, 0.85))
            confidence = float(np.clip(0.50 + consecutive_down * 0.04, 0.50, 0.78))

            signals.append({
                "asset": asset,
                "signal_name": "consecutive_down_days_oversold",
                "direction": SignalDirection.LONG.value,
                "strength": round(strength, 4),
                "confidence": round(confidence, 4),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "metadata": {
                    "consecutive_down_days": consecutive_down,
                    "streak_return": round(streak_return, 4),
                    "signal_type": "consecutive_down_days",
                    "interpretation": "oversold_exhaustion",
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
