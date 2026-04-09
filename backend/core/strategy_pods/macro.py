"""
AETHERTRADE-SWARM — Global Macro / Risk Parity Pod
Real market data: inverse-volatility risk parity + momentum tilt + safe-haven overlay.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import numpy as np

from data.market_data import get_market_data_service
from models.schemas import PodName, RegimeState, SignalDirection
from .base import BaseStrategyPod

logger = logging.getLogger("aethertrade.macro")

# Five liquid proxies for risk-parity allocation
RISK_PARITY_ASSETS = ["SPY", "TLT", "GLD", "USO", "EEM"]

# Annualisation factor for daily log-return vol
ANNUALISE = np.sqrt(252)

# SPY annualised vol threshold for triggering safe-haven overlay
SAFE_HAVEN_VOL_THRESHOLD = 0.20


def _annualised_vol(returns: np.ndarray) -> float:
    """Annualised volatility from a daily log-return array. Returns NaN on bad input."""
    if len(returns) < 5:
        return float("nan")
    return float(np.std(returns, ddof=1)) * ANNUALISE


def _three_month_return(closes: list[float]) -> float:
    """Approximate 3-month return from the most recent 63 trading days."""
    window = closes[-63:] if len(closes) >= 63 else closes
    if len(window) < 2:
        return 0.0
    return float(window[-1] / window[0] - 1.0)


class MacroPod(BaseStrategyPod):

    def __init__(self) -> None:
        super().__init__(PodName.MACRO)
        self._svc = get_market_data_service()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def generate_signals(self, context: dict[str, Any]) -> list[dict[str, Any]]:
        regime = context.get("regime", RegimeState.BULL)
        signals: list[dict[str, Any]] = []
        ts = datetime.now(timezone.utc).isoformat()

        # 1. Fetch real data for each risk-parity asset
        vols: dict[str, float] = {}
        mom: dict[str, float] = {}
        closes_map: dict[str, list[float]] = {}

        for sym in RISK_PARITY_ASSETS:
            try:
                daily = self._svc.fetch_daily(sym, period="1y")
                rows = daily.get("data", [])
                if not rows:
                    logger.warning("macro: no data for %s", sym)
                    continue
                closes = [r["close"] for r in rows if r.get("close")]
                closes_map[sym] = closes
                if len(closes) < 2:
                    continue
                log_rets = np.diff(np.log(np.array(closes)))
                vols[sym] = _annualised_vol(log_rets)
                mom[sym] = _three_month_return(closes)
            except Exception as exc:
                logger.error("macro: fetch %s failed: %s", sym, exc)

        if not vols:
            logger.error("macro: no volatility data available — returning empty signals")
            return []

        # 2. Inverse-volatility weights
        inv_vol = {sym: 1.0 / v for sym, v in vols.items() if not np.isnan(v) and v > 0}
        if not inv_vol:
            return []
        total_inv = sum(inv_vol.values())
        iv_weights = {sym: w / total_inv for sym, w in inv_vol.items()}

        # 3. Momentum tilt: scale up assets with positive 3-month return by 20%
        raw_weights: dict[str, float] = {}
        for sym, w in iv_weights.items():
            m = mom.get(sym, 0.0)
            tilt = 1.20 if m > 0 else 0.80
            raw_weights[sym] = w * tilt

        # Renormalise after tilt
        total_raw = sum(raw_weights.values())
        weights = {sym: w / total_raw for sym, w in raw_weights.items()}

        # 4. Safe-haven overlay: when SPY annualised vol > 20%, shift 15 pp to GLD+TLT
        spy_vol = vols.get("SPY", 0.0)
        safe_haven_active = (not np.isnan(spy_vol)) and (spy_vol > SAFE_HAVEN_VOL_THRESHOLD)

        if safe_haven_active:
            shift = 0.075  # 7.5 pp each to GLD and TLT
            for safe_sym in ("GLD", "TLT"):
                if safe_sym in weights:
                    weights[safe_sym] = weights.get(safe_sym, 0.0) + shift
            # Absorb the shift from equities and commodities
            for reduce_sym in ("SPY", "EEM", "USO"):
                if reduce_sym in weights:
                    weights[reduce_sym] = max(0.0, weights[reduce_sym] - shift * 2 / 3)
            # Renormalise once more
            total_w = sum(weights.values())
            if total_w > 0:
                weights = {sym: w / total_w for sym, w in weights.items()}

        # 5. Emit one signal per asset
        for sym in RISK_PARITY_ASSETS:
            if sym not in weights:
                continue
            w = weights[sym]
            current_vol = vols.get(sym, float("nan"))
            three_m = mom.get(sym, 0.0)

            # Regime dampening: pull back gross allocations in crisis
            regime_scale = {
                RegimeState.BULL: 1.0,
                RegimeState.RANGE: 0.85,
                RegimeState.BEAR: 0.70,
                RegimeState.CRISIS: 0.40,
            }.get(regime, 0.75)

            scaled_weight = round(w * regime_scale, 4)
            direction = SignalDirection.LONG if scaled_weight >= 0 else SignalDirection.SHORT

            # Confidence inversely proportional to vol (higher vol → lower confidence)
            if not np.isnan(current_vol) and current_vol > 0:
                confidence = round(float(np.clip(1.0 - current_vol, 0.40, 0.92)), 4)
            else:
                confidence = 0.55

            signals.append({
                "asset": sym,
                "signal_name": "risk_parity_iv_weight",
                "direction": direction.value,
                "strength": scaled_weight,
                "confidence": confidence,
                "timestamp": ts,
                "metadata": {
                    "raw_iv_weight": round(iv_weights.get(sym, 0.0), 4),
                    "momentum_tilt": round(three_m, 4),
                    "annualised_vol": round(current_vol, 4) if not np.isnan(current_vol) else None,
                    "safe_haven_active": safe_haven_active,
                    "spy_annualised_vol": round(spy_vol, 4) if not np.isnan(spy_vol) else None,
                    "regime_scale": regime_scale,
                    "strategy": "risk_parity",
                },
            })

        self._signal_count = len(signals)
        return signals

    def get_metrics(self) -> dict[str, Any]:
        return {
            "pod_name": self.pod_name,
            "status": "active",
            "signal_count": self._signal_count,
            "assets": RISK_PARITY_ASSETS,
            "safe_haven_threshold_vol": SAFE_HAVEN_VOL_THRESHOLD,
            "uptime_seconds": round(self.uptime_seconds, 1),
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }
