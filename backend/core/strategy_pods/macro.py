"""
AETHERTRADE-SWARM — Global Macro / Risk Parity Pod
Carry trades, risk parity allocation, macro trend signals.
"""
from __future__ import annotations

import random
from datetime import datetime, timezone
from typing import Any

import numpy as np

from models.schemas import PodName, RegimeState, SignalDirection
from .base import BaseStrategyPod


MACRO_ASSETS = {
    "rates": ["TLT", "IEF", "SHY"],
    "fx": ["UUP", "FXE", "FXY"],
    "commodities": ["GLD", "USO", "PDBC"],
    "equities": ["SPY", "EFA", "EEM"],
}


class MacroPod(BaseStrategyPod):

    def __init__(self, seed: int = 3) -> None:
        super().__init__(PodName.MACRO)
        self._rng = np.random.default_rng(seed)
        self._random = random.Random(seed)
        self._signal_count = 12

    def generate_signals(self, context: dict[str, Any]) -> list[dict[str, Any]]:
        regime = context.get("regime", RegimeState.BULL)
        signals = []

        # Risk parity — always active, but adjusts by regime
        rp_weights = self._risk_parity_weights(regime)
        for asset_class, weight in rp_weights.items():
            assets = MACRO_ASSETS.get(asset_class, ["SPY"])
            asset = self._random.choice(assets)
            direction = SignalDirection.LONG if weight > 0 else SignalDirection.SHORT
            signals.append({
                "asset": asset,
                "signal_name": f"risk_parity_{asset_class}",
                "direction": direction.value,
                "strength": round(float(weight), 4),
                "confidence": round(float(self._rng.uniform(0.70, 0.90)), 4),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "metadata": {
                    "asset_class": asset_class,
                    "risk_contribution": round(abs(float(weight)), 4),
                    "strategy": "risk_parity",
                },
            })

        # Carry signal — short vol in carry-friendly regimes
        if regime in (RegimeState.BULL, RegimeState.RANGE):
            carry_strength = self._rng.uniform(0.3, 0.7)
            signals.append({
                "asset": "FXE",
                "signal_name": "fx_carry",
                "direction": SignalDirection.LONG.value,
                "strength": round(float(carry_strength), 4),
                "confidence": round(float(self._rng.uniform(0.60, 0.80)), 4),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "metadata": {"carry_score": round(float(carry_strength), 4), "strategy": "carry"},
            })

        return signals

    def _risk_parity_weights(self, regime: RegimeState) -> dict[str, float]:
        if regime == RegimeState.BULL:
            return {"equities": 0.40, "commodities": 0.20, "rates": 0.25, "fx": 0.15}
        elif regime == RegimeState.BEAR:
            return {"equities": -0.10, "commodities": 0.25, "rates": 0.50, "fx": 0.35}
        elif regime == RegimeState.CRISIS:
            return {"equities": -0.30, "commodities": 0.10, "rates": 0.60, "fx": 0.60}
        else:
            return {"equities": 0.25, "commodities": 0.25, "rates": 0.25, "fx": 0.25}

    def get_metrics(self) -> dict[str, Any]:
        return {"pod_name": self.pod_name, "status": "active", "signal_count": self._signal_count}
