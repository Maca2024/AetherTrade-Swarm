"""
AetherTrade-Swarm — Mean Reversion Pod
Real RSI-2 + Bollinger Band reversion signals from yfinance data.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import numpy as np

from data.market_data import get_market_data_service, EQUITY_UNIVERSE, ETF_UNIVERSE
from models.schemas import PodName, RegimeState, SignalDirection
from .base import BaseStrategyPod

logger = logging.getLogger("aethertrade.pod.mean_reversion")

RSI_UNIVERSE = ["SPY", "QQQ", "IWM", "AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA", "GLD", "TLT"]


def _compute_rsi(closes: list[float], period: int = 2) -> float:
    """Compute RSI from closing prices."""
    if len(closes) < period + 1:
        return 50.0
    deltas = np.diff(closes[-(period + 1):])
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    avg_gain = np.mean(gains) if len(gains) > 0 else 0
    avg_loss = np.mean(losses) if len(losses) > 0 else 1e-10
    rs = avg_gain / avg_loss if avg_loss > 0 else 100
    return 100 - (100 / (1 + rs))


def _compute_bollinger(closes: list[float], period: int = 20, num_std: float = 2.0) -> tuple[float, float, float]:
    """Compute Bollinger Bands. Returns (upper, middle, lower)."""
    if len(closes) < period:
        c = closes[-1] if closes else 0
        return c, c, c
    recent = np.array(closes[-period:])
    middle = float(np.mean(recent))
    std = float(np.std(recent))
    return middle + num_std * std, middle, middle - num_std * std


class MeanReversionPod(BaseStrategyPod):

    def __init__(self) -> None:
        super().__init__(PodName.MEAN_REVERSION)

    def generate_signals(self, context: dict[str, Any]) -> list[dict[str, Any]]:
        regime = context.get("regime", RegimeState.RANGE)
        mds = get_market_data_service()
        signals = []

        regime_multiplier = {
            RegimeState.BULL: 0.5,
            RegimeState.RANGE: 1.0,
            RegimeState.BEAR: 0.7,
            RegimeState.CRISIS: 0.3,
        }.get(regime, 0.5)

        for symbol in RSI_UNIVERSE:
            try:
                data = mds.fetch_daily(symbol, "3mo")
                closes = [d["close"] for d in data.get("data", [])]
                if len(closes) < 25:
                    continue

                # RSI-2
                rsi2 = _compute_rsi(closes, period=2)

                if rsi2 < 10:
                    strength = (10 - rsi2) / 10 * regime_multiplier
                    signals.append({
                        "asset": symbol,
                        "signal_name": "rsi_2_oversold",
                        "direction": SignalDirection.LONG.value,
                        "strength": round(strength, 4),
                        "confidence": round(min(0.55 + (10 - rsi2) / 20, 0.85), 4),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "metadata": {"rsi_2": round(rsi2, 2), "hold_days": 3},
                    })
                elif rsi2 > 90:
                    strength = -((rsi2 - 90) / 10) * regime_multiplier
                    signals.append({
                        "asset": symbol,
                        "signal_name": "rsi_2_overbought",
                        "direction": SignalDirection.SHORT.value,
                        "strength": round(strength, 4),
                        "confidence": round(min(0.55 + (rsi2 - 90) / 20, 0.85), 4),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "metadata": {"rsi_2": round(rsi2, 2), "hold_days": 3},
                    })

                # Bollinger Band
                upper, middle, lower = _compute_bollinger(closes)
                current = closes[-1]

                if current < lower:
                    bb_pct = (lower - current) / (upper - lower) if upper != lower else 0
                    strength = min(bb_pct * regime_multiplier, 1.0)
                    signals.append({
                        "asset": symbol,
                        "signal_name": "bollinger_oversold",
                        "direction": SignalDirection.LONG.value,
                        "strength": round(strength, 4),
                        "confidence": round(min(0.6 + bb_pct * 0.2, 0.85), 4),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "metadata": {
                            "current": round(current, 2),
                            "lower_band": round(lower, 2),
                            "upper_band": round(upper, 2),
                        },
                    })
                elif current > upper:
                    bb_pct = (current - upper) / (upper - lower) if upper != lower else 0
                    strength = -min(bb_pct * regime_multiplier, 1.0)
                    signals.append({
                        "asset": symbol,
                        "signal_name": "bollinger_overbought",
                        "direction": SignalDirection.SHORT.value,
                        "strength": round(strength, 4),
                        "confidence": round(min(0.6 + bb_pct * 0.2, 0.85), 4),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "metadata": {
                            "current": round(current, 2),
                            "lower_band": round(lower, 2),
                            "upper_band": round(upper, 2),
                        },
                    })

            except Exception as exc:
                logger.debug("MeanRev %s: %s", symbol, exc)

        self._signal_count = len(signals)
        return signals

    def get_metrics(self) -> dict[str, Any]:
        return {
            "pod_name": self.pod_name,
            "status": "active",
            "signal_count": self._signal_count,
            "universe_size": len(RSI_UNIVERSE),
            "uptime_seconds": round(self.uptime_seconds, 1),
        }
