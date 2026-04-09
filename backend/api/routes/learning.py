"""
AetherTrade-Swarm — Self-Learning API Routes
GET /api/v1/learning/status — Current learning engine status
POST /api/v1/learning/cycle — Trigger a learning cycle manually
GET /api/v1/learning/weights — Current pod weight adjustments
"""

from __future__ import annotations

from fastapi import APIRouter

from api.deps import ApiKeyDep
from core.self_learning import get_self_learning_engine

router = APIRouter(prefix="/api/v1/learning", tags=["learning"])


@router.get("/status", summary="Self-learning engine status")
async def learning_status(_key: ApiKeyDep):
    engine = get_self_learning_engine()
    return engine.get_status()


@router.post("/cycle", summary="Trigger a learning cycle")
async def trigger_cycle(_key: ApiKeyDep):
    engine = get_self_learning_engine()
    result = await engine.run_cycle()
    return result


@router.get("/weights", summary="Current pod weight adjustments")
async def pod_weights(_key: ApiKeyDep):
    engine = get_self_learning_engine()
    return {
        "weights": engine.pod_weights,
        "description": "Weight multipliers applied to pod signals. Higher = more trusted.",
    }
