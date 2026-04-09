"""
AETHERTRADE-SWARM — Multi-Factor Pod (AQR-style)
Systematic long/short across Value, Momentum, and Low-Volatility factors.

Signals driven by REAL market data from EQUITY_UNIVERSE:
1. Value factor    — price vs. 52-week high ratio (lower = cheaper = long)
2. Momentum factor — 6-month (126-day) return ranking
3. Low-vol factor  — 60-day realized volatility (lower = long)
4. Composite Z-score — equal-weight combination of all three factors
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import numpy as np

from data.market_data import EQUITY_UNIVERSE, get_market_data_service
from models.schemas import PodName, RegimeState, SignalDirection
from .base import BaseStrategyPod

logger = logging.getLogger("aethertrade.multi_factor")

TRADING_DAYS = 252

FACTORS = ["value", "momentum", "low_volatility"]


def _zscore(arr: np.ndarray) -> np.ndarray:
    """Cross-sectional Z-score. Returns zeros for degenerate arrays."""
    if len(arr) < 2:
        return np.zeros_like(arr)
    std = float(np.std(arr, ddof=1))
    if std < 1e-10:
        return np.zeros_like(arr)
    return (arr - np.mean(arr)) / std


class MultiFactorPod(BaseStrategyPod):

    def __init__(self) -> None:
        super().__init__(PodName.MULTI_FACTOR)
        self._svc = get_market_data_service()

    def generate_signals(self, context: dict[str, Any]) -> list[dict[str, Any]]:
        regime = context.get("regime", RegimeState.BULL)
        signals: list[dict[str, Any]] = []

        factor_tilts = self._regime_factor_tilts(regime)

        # ------------------------------------------------------------------ #
        # Collect raw factor values per asset                                  #
        # ------------------------------------------------------------------ #
        raw_value: dict[str, float] = {}
        raw_momentum: dict[str, float] = {}
        raw_lowvol: dict[str, float] = {}

        for symbol in EQUITY_UNIVERSE:
            try:
                result = self._svc.fetch_daily(symbol, period="1y")
            except Exception as exc:
                logger.error("multi_factor: fetch_daily(%s): %s", symbol, exc)
                continue

            rows = result.get("data", [])
            if len(rows) < 63:
                logger.warning("multi_factor: %s has %d rows, need 63+", symbol, len(rows))
                continue

            closes = np.array([r["close"] for r in rows], dtype=float)

            # Value factor: current price / 52-week high (lower = cheaper = more long)
            high_52w = float(np.max(closes))
            price_to_52w_high = closes[-1] / high_52w if high_52w > 0 else float("nan")
            if not np.isnan(price_to_52w_high):
                # Invert so that lower price/52wk-high → higher score (more attractive)
                raw_value[symbol] = 1.0 - price_to_52w_high

            # Momentum factor: 6-month (126-day) return, skipping last 21 days
            # Classic Fama-French formation: t-126 to t-21 (avoids short-term reversal)
            if len(closes) >= 126:
                mom_return = float((closes[-22] - closes[-127]) / closes[-127])
                raw_momentum[symbol] = mom_return

            # Low-vol factor: 60-day realized vol (lower → safer → more long)
            if len(closes) >= 60:
                log_returns = np.diff(np.log(closes[-61:]))
                rv_60d = float(np.std(log_returns, ddof=1) * np.sqrt(TRADING_DAYS))
                # Invert: lower vol → higher score
                raw_lowvol[symbol] = -rv_60d

        if len(raw_value) < 3:
            logger.warning("multi_factor: insufficient data for cross-sectional ranking")
            return signals

        # ------------------------------------------------------------------ #
        # Cross-sectional Z-scores per factor                                 #
        # ------------------------------------------------------------------ #
        def _factor_zscores(raw: dict[str, float]) -> dict[str, float]:
            symbols_in = list(raw.keys())
            vals = np.array([raw[s] for s in symbols_in])
            zscores = _zscore(vals)
            return {s: float(zscores[i]) for i, s in enumerate(symbols_in)}

        z_value = _factor_zscores(raw_value)
        z_momentum = _factor_zscores(raw_momentum)
        z_lowvol = _factor_zscores(raw_lowvol)

        # ------------------------------------------------------------------ #
        # Composite Z-score per asset (equal weight, regime-tilted)           #
        # ------------------------------------------------------------------ #
        all_symbols = set(z_value) | set(z_momentum) | set(z_lowvol)

        for symbol in all_symbols:
            factor_scores: dict[str, float] = {}
            components: list[float] = []

            if symbol in z_value:
                tilt = factor_tilts.get("value", 1.0)
                score = z_value[symbol] * tilt
                factor_scores["value"] = round(score, 4)
                components.append(score)

            if symbol in z_momentum:
                tilt = factor_tilts.get("momentum", 1.0)
                score = z_momentum[symbol] * tilt
                factor_scores["momentum"] = round(score, 4)
                components.append(score)

            if symbol in z_lowvol:
                tilt = factor_tilts.get("low_volatility", 1.0)
                score = z_lowvol[symbol] * tilt
                factor_scores["low_volatility"] = round(score, 4)
                components.append(score)

            if not components:
                continue

            composite_z = float(np.mean(components))

            # Only generate a signal when the composite score is material
            if abs(composite_z) < 0.40:
                continue

            direction = SignalDirection.LONG if composite_z > 0 else SignalDirection.SHORT
            # tanh scaling so extreme z-scores don't produce strength > 1
            strength = float(np.tanh(composite_z * 0.75))
            confidence = float(np.clip(0.55 + abs(composite_z) * 0.08, 0.55, 0.88))

            signals.append({
                "asset": symbol,
                "signal_name": "multi_factor_composite",
                "direction": direction.value,
                "strength": round(strength, 4),
                "confidence": round(confidence, 4),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "metadata": {
                    "composite_z": round(composite_z, 4),
                    "factor_scores": factor_scores,
                    "active_factors": list(factor_scores.keys()),
                    "regime_tilts": factor_tilts,
                    "signal_type": "multi_factor",
                    "rebalance_freq": "monthly",
                },
            })

        # ------------------------------------------------------------------ #
        # Label top/bottom decile entries                                      #
        # ------------------------------------------------------------------ #
        long_sigs = sorted(
            [s for s in signals if s["direction"] == SignalDirection.LONG.value],
            key=lambda s: s["strength"],
            reverse=True,
        )[:4]
        short_sigs = sorted(
            [s for s in signals if s["direction"] == SignalDirection.SHORT.value],
            key=lambda s: s["strength"],
        )[:4]

        for sig in long_sigs:
            sig["metadata"]["decile"] = "top_long"
        for sig in short_sigs:
            sig["metadata"]["decile"] = "top_short"

        return signals

    def _regime_factor_tilts(self, regime: RegimeState) -> dict[str, float]:
        """Regime-dependent scaling multipliers per factor."""
        tilts: dict[RegimeState, dict[str, float]] = {
            RegimeState.BULL: {"value": 0.8, "momentum": 1.2, "low_volatility": 0.7},
            RegimeState.RANGE: {"value": 1.1, "momentum": 0.6, "low_volatility": 1.1},
            RegimeState.BEAR: {"value": 1.2, "momentum": 0.4, "low_volatility": 1.4},
            RegimeState.CRISIS: {"value": 0.5, "momentum": 0.2, "low_volatility": 1.8},
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
