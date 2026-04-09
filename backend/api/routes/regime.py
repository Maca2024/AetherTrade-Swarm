"""
AETHERTRADE-SWARM — Regime Routes
GET /api/v1/regime         — current regime state + confidence
GET /api/v1/regime/history — last 30 regime transitions
"""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter

from api.auth import ApiKeyDep
from api.deps import SimulatorDep
from models.schemas import RegimeHistoryResponse, RegimeResponse, RegimeTransition

router = APIRouter(prefix="/api/v1/regime", tags=["regime"])


@router.get("", response_model=RegimeResponse, summary="Current market regime")
async def get_current_regime(
    _key: ApiKeyDep,
    sim: SimulatorDep,
) -> RegimeResponse:
    """
    Returns the current HMM-detected market regime (bull/range/bear/crisis),
    confidence score, state probabilities, duration, and per-pod allocation impact.
    """
    data = sim.get_regime()
    return RegimeResponse(
        regime=data["regime"],
        confidence=data["confidence"],
        probabilities=data["probabilities"],
        duration_days=data["duration_days"],
        last_transition=datetime.fromisoformat(data["last_transition"]),
        signal_impact=data["signal_impact"],
    )


@router.get("/history", response_model=RegimeHistoryResponse, summary="Regime transition history")
async def get_regime_history(
    _key: ApiKeyDep,
    sim: SimulatorDep,
) -> RegimeHistoryResponse:
    """
    Returns the last 30 regime transitions with timestamps, triggers, and
    confidence scores. Also includes the full regime time-distribution over
    the 2-year lookback window.
    """
    transitions_raw = sim.get_regime_history(limit=30)
    transitions = [
        RegimeTransition(
            from_regime=t["from_regime"],
            to_regime=t["to_regime"],
            timestamp=datetime.fromisoformat(t["timestamp"]),
            confidence=t["confidence"],
            trigger=t["trigger"],
        )
        for t in transitions_raw
    ]

    current_data = sim.get_regime()
    distribution = sim.get_regime_distribution()

    return RegimeHistoryResponse(
        transitions=transitions,
        current_regime=current_data["regime"],
        regime_distribution=distribution,
        lookback_days=730,
    )
