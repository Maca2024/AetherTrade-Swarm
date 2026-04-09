"""
AETHERTRADE-SWARM — Market Making Pod
Order flow imbalance signals + bid-ask spread capture.

Signals:
1. Order flow imbalance (OFI) — buy vs sell volume asymmetry predicts short-term direction
2. Bid-ask spread capture — quote on both sides at optimal spread
3. Inventory rebalancing — skew quotes to reduce directional risk
4. Microstructure toxicity — VPIN-based adverse selection detection
"""
from __future__ import annotations

import random
from datetime import datetime, timezone
from typing import Any

import numpy as np

from models.schemas import PodName, RegimeState, SignalDirection
from .base import BaseStrategyPod


# Liquid instruments suitable for market making
MM_UNIVERSE = ["SPY", "QQQ", "IWM", "AAPL", "MSFT", "AMZN", "NVDA", "TSLA", "BTC", "ETH"]

# Typical half-spreads (bps)
TYPICAL_SPREADS: dict[str, float] = {
    "SPY": 0.5, "QQQ": 0.6, "IWM": 0.8,
    "AAPL": 1.0, "MSFT": 1.0, "AMZN": 1.2,
    "NVDA": 1.5, "TSLA": 2.0,
    "BTC": 5.0, "ETH": 6.0,
}


class MarketMakingPod(BaseStrategyPod):

    def __init__(self, seed: int = 9) -> None:
        super().__init__(PodName.MARKET_MAKING)
        self._rng = np.random.default_rng(seed)
        self._random = random.Random(seed)
        self._signal_count = 6

    def generate_signals(self, context: dict[str, Any]) -> list[dict[str, Any]]:
        regime = context.get("regime", RegimeState.RANGE)
        signals: list[dict[str, Any]] = []

        # Market making is volume-dependent and hates crisis (toxic flow)
        active = regime not in (RegimeState.CRISIS,)
        regime_multiplier = {
            RegimeState.BULL: 0.8,    # Trending flow → more toxicity
            RegimeState.RANGE: 1.0,   # Mean-reverting flow → ideal
            RegimeState.BEAR: 0.7,
            RegimeState.CRISIS: 0.05, # Near halt — too much adverse selection
        }.get(regime, 0.5)

        if not active:
            return signals

        mm_assets = self._random.sample(MM_UNIVERSE, k=min(4, len(MM_UNIVERSE)))

        for asset in mm_assets:
            nominal_spread_bps = TYPICAL_SPREADS.get(asset, 2.0)

            # --- Order Flow Imbalance ---
            # OFI = (buy_vol - sell_vol) / total_vol ∈ [-1, 1]
            ofi = float(np.clip(self._rng.normal(0.0, 0.4), -1.0, 1.0))

            # Strong imbalance predicts short-term price direction
            if abs(ofi) > 0.25:
                direction = SignalDirection.LONG if ofi > 0 else SignalDirection.SHORT
                ofi_strength = min(abs(ofi), 1.0) * regime_multiplier
                if direction == SignalDirection.SHORT:
                    ofi_strength = -ofi_strength

                signals.append({
                    "asset": asset,
                    "signal_name": "order_flow_imbalance",
                    "direction": direction.value,
                    "strength": round(float(ofi_strength), 4),
                    "confidence": round(float(self._rng.uniform(0.52, 0.72)), 4),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "metadata": {
                        "ofi": round(float(ofi), 4),
                        "buy_volume_pct": round(float((ofi + 1.0) / 2.0), 4),
                        "signal_type": "order_flow_imbalance",
                        "holding_seconds": self._random.randint(10, 120),
                    },
                })

            # --- VPIN Toxicity (Adverse Selection) ---
            # VPIN > 0.5 → toxic flow → widen quotes / reduce size
            vpin = float(self._rng.beta(2, 5))  # Typically low, spikes in events
            if vpin > 0.45:
                # High toxicity → do not make market (or size down)
                signals.append({
                    "asset": asset,
                    "signal_name": "vpin_adverse_selection",
                    "direction": SignalDirection.NEUTRAL.value,
                    "strength": 0.0,
                    "confidence": round(float(self._rng.uniform(0.70, 0.92)), 4),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "metadata": {
                        "vpin": round(float(vpin), 4),
                        "action": "reduce_quote_size_50pct" if vpin < 0.65 else "halt_market_making",
                        "nominal_spread_bps": round(float(nominal_spread_bps), 2),
                        "signal_type": "vpin_toxicity",
                    },
                })
            else:
                # Low toxicity → post tight quotes for spread capture
                expected_pnl_bps = nominal_spread_bps * (1.0 - 2.0 * vpin) * regime_multiplier
                signals.append({
                    "asset": asset,
                    "signal_name": "spread_capture_quote",
                    "direction": SignalDirection.NEUTRAL.value,
                    "strength": round(float(min(expected_pnl_bps / 10.0, 0.5)), 4),
                    "confidence": round(float(self._rng.uniform(0.62, 0.82)), 4),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "metadata": {
                        "vpin": round(float(vpin), 4),
                        "half_spread_bps": round(float(nominal_spread_bps), 2),
                        "expected_pnl_bps_per_turn": round(float(expected_pnl_bps), 4),
                        "signal_type": "spread_capture",
                        "quote_qty_pct_adv": round(float(self._rng.uniform(0.001, 0.005)), 6),
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
