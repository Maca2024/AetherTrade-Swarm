"""
AETHERTRADE-SWARM — Signal Routes
GET /api/v1/signals/combined   — ensemble signal from all pods
GET /api/v1/signals/allocation — current regime-adjusted allocation weights
"""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter

from api.auth import ApiKeyDep
from api.deps import SimulatorDep
from models.schemas import AllocationResponse, CombinedSignalResponse, SignalDetail

router = APIRouter(prefix="/api/v1/signals", tags=["signals"])


@router.get("/combined", response_model=CombinedSignalResponse, summary="Ensemble signal")
async def get_combined_signal(
    _key: ApiKeyDep,
    sim: SimulatorDep,
) -> CombinedSignalResponse:
    """
    Returns the regime-adjusted ensemble signal aggregated across all 9
    strategy pods, including per-pod contribution weights and top 5
    individual signals ranked by absolute strength.
    """
    data = sim.get_combined_signal()

    top_signals = [
        SignalDetail(
            asset=s["asset"],
            signal_name=s["signal_name"],
            direction=s["direction"],
            strength=s["strength"],
            confidence=s["confidence"],
            timestamp=datetime.fromisoformat(s["timestamp"]),
            metadata=s.get("metadata", {}),
        )
        for s in data["top_signals"]
    ]

    return CombinedSignalResponse(
        ensemble_direction=data["ensemble_direction"],
        ensemble_strength=data["ensemble_strength"],
        regime_adjusted=data["regime_adjusted"],
        pod_contributions=data["pod_contributions"],
        top_signals=top_signals,
        generated_at=datetime.fromisoformat(data["generated_at"]),
        confidence=data["confidence"],
    )


@router.get("/allocation", response_model=AllocationResponse, summary="Allocation weights")
async def get_allocation(
    _key: ApiKeyDep,
    sim: SimulatorDep,
) -> AllocationResponse:
    """
    Returns the current regime-conditioned portfolio allocation weights across
    all 9 strategy pods. Includes rebalance schedule and override flags.
    """
    data = sim.get_allocation()
    return AllocationResponse(
        strategy_weights=data["strategy_weights"],
        regime=data["regime"],
        regime_override_active=data["regime_override_active"],
        rebalance_required=data["rebalance_required"],
        last_rebalance=datetime.fromisoformat(data["last_rebalance"]),
        next_rebalance=datetime.fromisoformat(data["next_rebalance"]),
    )
