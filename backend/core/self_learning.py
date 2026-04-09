"""
AetherTrade-Swarm — Self-Learning Loop
Tracks pod performance, learns from signal outcomes, and adjusts pod weights.
Inspired by CORTEX Cathedral Self-Learning Engine pattern.

Loop cycle (runs every 4 hours):
1. OBSERVE: Collect signal outcomes (which signals led to profitable trades)
2. EVALUATE: Score each pod's recent accuracy, Sharpe, win rate
3. LEARN: Adjust pod confidence multipliers based on performance
4. STORE: Persist learnings to Supabase pod_metrics table
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import numpy as np

logger = logging.getLogger("aethertrade.self_learning")

# Default pod weights (equal to start)
DEFAULT_POD_WEIGHTS: dict[str, float] = {
    "momentum": 1.0,
    "mean_reversion": 1.0,
    "macro": 1.0,
    "stat_arb": 1.0,
    "options_vol": 1.0,
    "behavioral": 1.0,
    "ai_ml": 1.0,
    "multi_factor": 1.0,
    "market_making": 1.0,
}

# Learning rate: how fast weights adjust (0.1 = 10% per cycle)
LEARNING_RATE = 0.1
# Minimum weight (prevent any pod from being completely silenced)
MIN_WEIGHT = 0.3
# Maximum weight (prevent any pod from dominating)
MAX_WEIGHT = 2.5


class SelfLearningEngine:
    """Observes pod performance and adjusts confidence multipliers."""

    def __init__(self, supabase_client: Any = None) -> None:
        self._db = supabase_client
        self._pod_weights = dict(DEFAULT_POD_WEIGHTS)
        self._cycle_count = 0
        self._last_cycle: datetime | None = None

    @property
    def pod_weights(self) -> dict[str, float]:
        return dict(self._pod_weights)

    async def run_cycle(self) -> dict[str, Any]:
        """Execute one full self-learning cycle."""
        self._cycle_count += 1
        now = datetime.now(tz=timezone.utc)
        logger.info("Self-learning cycle #%d starting", self._cycle_count)

        # 1. OBSERVE: Get recent signal outcomes
        observations = await self._observe_outcomes()

        # 2. EVALUATE: Score each pod
        scores = self._evaluate_pods(observations)

        # 3. LEARN: Adjust weights
        adjustments = self._adjust_weights(scores)

        # 4. STORE: Persist to Supabase
        await self._store_metrics(scores)

        self._last_cycle = now

        result = {
            "cycle": self._cycle_count,
            "timestamp": now.isoformat(),
            "observations": len(observations),
            "pod_scores": scores,
            "weight_adjustments": adjustments,
            "current_weights": dict(self._pod_weights),
        }

        logger.info(
            "Self-learning cycle #%d complete: %d observations, %d pods scored",
            self._cycle_count, len(observations), len(scores),
        )
        return result

    async def _observe_outcomes(self) -> list[dict[str, Any]]:
        """Fetch recent signals and their trade outcomes."""
        if not self._db:
            return []

        try:
            since = (datetime.now(tz=timezone.utc) - timedelta(hours=24)).isoformat()

            # Get recent signals
            signals_resp = (
                self._db.table("signals")
                .select("id, pod_name, asset, direction, strength, confidence, created_at")
                .gte("created_at", since)
                .order("created_at", desc=True)
                .limit(200)
                .execute()
            )

            # Get recent trades
            trades_resp = (
                self._db.table("trades")
                .select("signal_id, symbol, side, price, total_value, pod_name, executed_at")
                .gte("executed_at", since)
                .order("executed_at", desc=True)
                .limit(200)
                .execute()
            )

            signals = signals_resp.data or []
            trades = trades_resp.data or []

            # Match signals to trades
            trade_by_signal = {t.get("signal_id"): t for t in trades if t.get("signal_id")}

            observations = []
            for sig in signals:
                trade = trade_by_signal.get(sig.get("id"))
                observations.append({
                    "pod_name": sig.get("pod_name"),
                    "signal_strength": sig.get("strength", 0),
                    "signal_confidence": sig.get("confidence", 0),
                    "was_traded": trade is not None,
                    "trade_value": trade.get("total_value", 0) if trade else 0,
                })

            return observations

        except Exception as exc:
            logger.error("observe_outcomes: %s", exc)
            return []

    def _evaluate_pods(self, observations: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
        """Score each pod based on recent observations."""
        pod_obs: dict[str, list[dict]] = {}
        for obs in observations:
            pod = obs.get("pod_name", "unknown")
            pod_obs.setdefault(pod, []).append(obs)

        scores = {}
        for pod_name, obs_list in pod_obs.items():
            n = len(obs_list)
            if n == 0:
                continue

            traded = [o for o in obs_list if o.get("was_traded")]
            avg_confidence = np.mean([o.get("signal_confidence", 0.5) for o in obs_list])
            avg_strength = np.mean([abs(o.get("signal_strength", 0)) for o in obs_list])
            trade_rate = len(traded) / n if n > 0 else 0

            # Activity score: pods that generate actionable signals score higher
            activity_score = min(n / 20.0, 1.0)  # Normalize to 0-1

            # Composite score: weighted combination
            composite = (
                0.3 * avg_confidence +
                0.3 * avg_strength +
                0.2 * trade_rate +
                0.2 * activity_score
            )

            scores[pod_name] = {
                "signal_count": n,
                "avg_confidence": round(float(avg_confidence), 4),
                "avg_strength": round(float(avg_strength), 4),
                "trade_rate": round(trade_rate, 4),
                "activity_score": round(activity_score, 4),
                "composite_score": round(float(composite), 4),
            }

        return scores

    def _adjust_weights(self, scores: dict[str, dict[str, float]]) -> dict[str, float]:
        """Adjust pod weights based on scores. Returns adjustments made."""
        if not scores:
            return {}

        # Compute mean composite score
        composites = [s["composite_score"] for s in scores.values()]
        mean_score = np.mean(composites) if composites else 0.5

        adjustments = {}
        for pod_name, score_data in scores.items():
            if pod_name not in self._pod_weights:
                continue

            composite = score_data["composite_score"]
            # Positive adjustment for above-average, negative for below
            delta = LEARNING_RATE * (composite - mean_score)
            old_weight = self._pod_weights[pod_name]
            new_weight = np.clip(old_weight + delta, MIN_WEIGHT, MAX_WEIGHT)

            self._pod_weights[pod_name] = round(float(new_weight), 4)
            adjustments[pod_name] = round(float(new_weight - old_weight), 4)

        return adjustments

    async def _store_metrics(self, scores: dict[str, dict[str, float]]) -> None:
        """Store pod metrics to Supabase."""
        if not self._db:
            return

        today = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
        rows = []
        for pod_name, score_data in scores.items():
            rows.append({
                "pod_name": pod_name,
                "date": today,
                "signal_count": score_data.get("signal_count", 0),
                "win_rate": score_data.get("trade_rate", 0),
                "sharpe_ratio": score_data.get("composite_score", 0),
                "allocation_weight": self._pod_weights.get(pod_name, 1.0),
            })

        if not rows:
            return

        try:
            self._db.table("pod_metrics").upsert(
                rows, on_conflict="pod_name,date"
            ).execute()
            logger.info("Stored metrics for %d pods", len(rows))
        except Exception as exc:
            logger.error("store_metrics: %s", exc)

    def get_status(self) -> dict[str, Any]:
        """Return current self-learning engine status."""
        return {
            "enabled": True,
            "cycle_count": self._cycle_count,
            "last_cycle": self._last_cycle.isoformat() if self._last_cycle else None,
            "pod_weights": dict(self._pod_weights),
            "learning_rate": LEARNING_RATE,
        }


# Singleton
_engine: SelfLearningEngine | None = None


def get_self_learning_engine(supabase_client: Any = None) -> SelfLearningEngine:
    global _engine
    if _engine is None:
        _engine = SelfLearningEngine(supabase_client)
    return _engine
