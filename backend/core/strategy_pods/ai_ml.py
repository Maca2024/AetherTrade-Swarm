"""
AETHERTRADE-SWARM — AI/ML Feature Scoring Pod
No external LLM calls. Derives a directional signal from real SPY market data
using four technical features combined via majority-vote scoring.

Features computed on real yfinance data:
  F1  SMA crossovers  — 5/20-day and 10/50-day bullish/bearish cross
  F2  RSI-14          — oversold (<30 bullish), overbought (>70 bearish)
  F3  Volume trend    — close-price day above/below 20-day avg volume
  F4  Price momentum  — 20-day log-return sign

Scoring:
  Each feature votes +1 (bullish), -1 (bearish), or 0 (neutral).
  Final score = sum of votes (range -4 … +4).
  score >= +2  → LONG signal on SPY
  score <= -2  → SHORT signal on SPY
  |score| < 2  → NEUTRAL (no signal emitted)
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import numpy as np

from data.market_data import get_market_data_service
from models.schemas import PodName, RegimeState, SignalDirection
from .base import BaseStrategyPod

logger = logging.getLogger("aethertrade.ai_ml")

PRIMARY_SYMBOL = "SPY"
SECONDARY_SYMBOLS = ["QQQ", "IWM"]  # Additional breadth signals


def _sma(prices: np.ndarray, period: int) -> np.ndarray:
    """Simple moving average via convolution (no pandas dependency)."""
    if len(prices) < period:
        return np.full(len(prices), float("nan"))
    kernel = np.ones(period) / period
    sma = np.convolve(prices, kernel, mode="valid")
    # Pad the front with NaN so index aligns with original prices array
    return np.concatenate([np.full(period - 1, float("nan")), sma])


def _rsi(prices: np.ndarray, period: int = 14) -> float:
    """
    Wilder's RSI for the most recent value.
    Returns NaN if insufficient data.
    """
    if len(prices) < period + 1:
        return float("nan")
    deltas = np.diff(prices)
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)
    avg_gain = float(np.mean(gains[:period]))
    avg_loss = float(np.mean(losses[:period]))
    for g, l in zip(gains[period:], losses[period:]):
        avg_gain = (avg_gain * (period - 1) + g) / period
        avg_loss = (avg_loss * (period - 1) + l) / period
    if avg_loss < 1e-10:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def _feature_sma_crossovers(prices: np.ndarray) -> int:
    """
    Two crossover tests:
      5 > 20  AND  10 > 50  → bullish (+1)
      5 < 20  AND  10 < 50  → bearish (-1)
      mixed                 → neutral (0)
    """
    if len(prices) < 51:
        return 0
    sma5 = _sma(prices, 5)
    sma20 = _sma(prices, 20)
    sma10 = _sma(prices, 10)
    sma50 = _sma(prices, 50)
    cross_short = sma5[-1] > sma20[-1]   # True = bullish
    cross_long = sma10[-1] > sma50[-1]
    if cross_short and cross_long:
        return 1
    if not cross_short and not cross_long:
        return -1
    return 0


def _feature_rsi(prices: np.ndarray) -> int:
    """RSI-14: <30 → bullish (+1), >70 → bearish (-1), else 0."""
    r = _rsi(prices, 14)
    if np.isnan(r):
        return 0
    if r < 30:
        return 1
    if r > 70:
        return -1
    return 0


def _feature_volume_trend(closes: np.ndarray, volumes: np.ndarray) -> int:
    """
    On the most recent up-day, is volume above its 20-day average?
    Above average volume on an up-day → bullish (+1).
    Above average volume on a down-day → bearish (-1).
    Below average volume → neutral (0).
    """
    if len(closes) < 22 or len(volumes) < 22:
        return 0
    avg_vol = float(np.mean(volumes[-20:]))
    last_vol = float(volumes[-1])
    price_up = closes[-1] > closes[-2]
    if last_vol > avg_vol:
        return 1 if price_up else -1
    return 0


def _feature_price_momentum(prices: np.ndarray, window: int = 20) -> int:
    """Sign of log-return over `window` days."""
    if len(prices) < window + 1:
        return 0
    ret = float(np.log(prices[-1] / prices[-window - 1]))
    if ret > 0.005:
        return 1
    if ret < -0.005:
        return -1
    return 0


class AiMlPod(BaseStrategyPod):

    def __init__(self) -> None:
        super().__init__(PodName.AI_ML)
        self._svc = get_market_data_service()
        self._model_version = "feature_scorer_v1"

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def generate_signals(self, context: dict[str, Any]) -> list[dict[str, Any]]:
        regime = context.get("regime", RegimeState.BULL)
        signals: list[dict[str, Any]] = []
        ts = datetime.now(timezone.utc).isoformat()

        # AI/ML performs best in trending regimes
        regime_scale = {
            RegimeState.BULL: 1.00,
            RegimeState.RANGE: 0.60,
            RegimeState.BEAR: 0.70,
            RegimeState.CRISIS: 0.30,
        }.get(regime, 0.60)

        # Fetch SPY data
        try:
            daily = self._svc.fetch_daily(PRIMARY_SYMBOL, period="1y")
            rows = daily.get("data", [])
            if len(rows) < 55:
                logger.warning("ai_ml: insufficient SPY rows (%d)", len(rows))
                return []
            closes_raw = [r["close"] for r in rows if r.get("close")]
            volumes_raw = [r["volume"] for r in rows if r.get("volume") is not None]
        except Exception as exc:
            logger.error("ai_ml: fetch SPY failed: %s", exc)
            return []

        closes = np.array(closes_raw, dtype=float)
        volumes = np.array(volumes_raw, dtype=float)

        # Compute the four features
        f1 = _feature_sma_crossovers(closes)
        f2 = _feature_rsi(closes)
        f3 = _feature_volume_trend(closes, volumes)
        f4 = _feature_price_momentum(closes, window=20)

        total_score = f1 + f2 + f3 + f4  # range: -4 to +4

        if abs(total_score) < 2:
            # Consensus too weak — no signal
            logger.debug("ai_ml: score=%d, no signal (threshold ±2)", total_score)
            self._signal_count = 0
            return []

        direction = SignalDirection.LONG if total_score > 0 else SignalDirection.SHORT

        # Strength = fraction of maximum possible score, scaled by regime
        raw_strength = total_score / 4.0  # normalise to [-1, +1]
        strength = round(float(np.clip(raw_strength * regime_scale, -1.0, 1.0)), 4)

        # Confidence from vote agreement: 4/4 → 0.92, 3/4 → 0.75, 2/4 → 0.58
        vote_agreement = abs(total_score) / 4.0
        confidence = round(float(np.clip(0.40 + vote_agreement * 0.52, 0.40, 0.92)), 4)

        # RSI value for metadata
        rsi_value = _rsi(closes, 14)

        # 20-day momentum return for metadata
        mom_ret = float(np.log(closes[-1] / closes[-21])) if len(closes) >= 21 else 0.0

        signals.append({
            "asset": PRIMARY_SYMBOL,
            "signal_name": "feature_consensus_score",
            "direction": direction.value,
            "strength": strength,
            "confidence": confidence,
            "timestamp": ts,
            "metadata": {
                "total_score": total_score,
                "max_score": 4,
                "features": {
                    "sma_crossover": f1,
                    "rsi_signal": f2,
                    "volume_trend": f3,
                    "price_momentum_20d": f4,
                },
                "rsi_14": round(rsi_value, 2) if not np.isnan(rsi_value) else None,
                "momentum_20d_return": round(mom_ret, 4),
                "sma5": round(float(_sma(closes, 5)[-1]), 2),
                "sma20": round(float(_sma(closes, 20)[-1]), 2),
                "sma50": round(float(_sma(closes, 50)[-1]), 2),
                "regime_scale": regime_scale,
                "model": self._model_version,
                "signal_type": "feature_scorer",
            },
        })

        # Secondary breadth signals from QQQ and IWM (momentum-only, lighter weight)
        for sec_sym in SECONDARY_SYMBOLS:
            try:
                sec_daily = self._svc.fetch_daily(sec_sym, period="6mo")
                sec_rows = sec_daily.get("data", [])
                if len(sec_rows) < 25:
                    continue
                sec_closes = np.array([r["close"] for r in sec_rows if r.get("close")])
                sec_f4 = _feature_price_momentum(sec_closes, window=20)
                sec_f1 = _feature_sma_crossovers(sec_closes)
                sec_score = sec_f4 + sec_f1
                if abs(sec_score) < 2:
                    continue
                sec_dir = SignalDirection.LONG if sec_score > 0 else SignalDirection.SHORT
                sec_strength = round(float(np.clip(sec_score / 2.0 * regime_scale, -1.0, 1.0)), 4)
                sec_confidence = round(float(np.clip(0.40 + abs(sec_score) / 2.0 * 0.30, 0.40, 0.72)), 4)
                signals.append({
                    "asset": sec_sym,
                    "signal_name": "breadth_momentum_score",
                    "direction": sec_dir.value,
                    "strength": sec_strength,
                    "confidence": sec_confidence,
                    "timestamp": ts,
                    "metadata": {
                        "score": sec_score,
                        "sma_cross": sec_f1,
                        "momentum_20d": sec_f4,
                        "regime_scale": regime_scale,
                        "model": self._model_version,
                        "signal_type": "breadth",
                    },
                })
            except Exception as exc:
                logger.warning("ai_ml: breadth signal %s failed: %s", sec_sym, exc)

        self._signal_count = len(signals)
        return signals

    def get_metrics(self) -> dict[str, Any]:
        return {
            "pod_name": self.pod_name,
            "status": "active",
            "signal_count": self._signal_count,
            "model_version": self._model_version,
            "primary_symbol": PRIMARY_SYMBOL,
            "secondary_symbols": SECONDARY_SYMBOLS,
            "features": ["sma_crossover", "rsi_14", "volume_trend", "price_momentum_20d"],
            "score_threshold": 2,
            "uptime_seconds": round(self.uptime_seconds, 1),
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }
