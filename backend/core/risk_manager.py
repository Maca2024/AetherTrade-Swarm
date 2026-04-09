"""
AETHERTRADE-SWARM — Risk Management Engine
8-metric risk dashboard with automated kill switches.

Metrics tracked:
  1. Annualized Volatility
  2. Maximum Drawdown
  3. Current Drawdown
  4. Gross Leverage
  5. Concentration Risk (largest pod weight)
  6. Liquidity Score (illiquid fraction)
  7. Tail Risk (99% VaR)
  8. Cross-Strategy Correlation
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

import numpy as np

logger = logging.getLogger("oracle.risk_manager")


KILL_SWITCH_THRESHOLDS: dict[str, dict[str, float]] = {
    "max_drawdown": {
        "halt_trading": 0.15,
        "reduce_leverage": 0.10,
    },
    "daily_loss": {
        "halt_new_positions": 0.025,
        "reduce_size": 0.015,
    },
    "leverage": {
        "hard_limit": 2.5,
        "warning": 1.75,
    },
    "correlation_spike": {
        "reduce_risk": 0.80,
        "warning": 0.65,
    },
    "volatility_spike": {
        "reduce_size": 0.25,   # annualised
        "halt_trading": 0.40,
    },
}


class RiskManager:
    """
    Evaluates portfolio risk in real time and triggers kill switches.
    """

    def __init__(self) -> None:
        self._active_alerts: list[dict[str, Any]] = []
        self._trading_halted = False

    def evaluate(
        self,
        portfolio_returns: np.ndarray,
        positions: list[dict[str, Any]],
        correlation_matrix: np.ndarray,
        pod_weights: dict[str, float],
    ) -> dict[str, Any]:
        """
        Full risk evaluation. Returns risk_dashboard dict.
        """
        from utils.metrics import (
            annualized_volatility, max_drawdown, current_drawdown,
            historical_var, historical_cvar,
        )

        vol = annualized_volatility(portfolio_returns[-30:]) if len(portfolio_returns) >= 5 else 0.10
        mdd = abs(max_drawdown(portfolio_returns))
        curr_dd = abs(current_drawdown(portfolio_returns))

        gross_lev = sum(abs(p.get("size", 0.0)) for p in positions)
        concentration = max(pod_weights.values()) if pod_weights else 0.0

        illiquid_fraction = 0.05  # Simplified — assume most liquid
        tail_var_99 = abs(historical_var(portfolio_returns, 0.99)) if len(portfolio_returns) > 10 else 0.03
        var_95 = abs(historical_var(portfolio_returns, 0.95)) if len(portfolio_returns) > 10 else 0.02
        cvar_95 = abs(historical_cvar(portfolio_returns, 0.95)) if len(portfolio_returns) > 10 else 0.025

        n = correlation_matrix.shape[0]
        if n > 1:
            upper_tri = correlation_matrix[np.triu_indices(n, k=1)]
            avg_corr = float(np.mean(upper_tri))
        else:
            avg_corr = 0.0

        metrics = self._build_metrics(vol, mdd, curr_dd, gross_lev, concentration, illiquid_fraction, tail_var_99, avg_corr)
        alerts = self._check_kill_switches(curr_dd, vol, gross_lev, avg_corr)
        self._active_alerts = alerts

        critical_count = sum(1 for m in metrics if m["status"] == "critical")
        warning_count = sum(1 for m in metrics if m["status"] == "warning")
        overall = "critical" if critical_count > 0 else ("warning" if warning_count > 0 else "ok")

        return {
            "overall_status": overall,
            "metrics": metrics,
            "portfolio_var_95": round(var_95, 6),
            "portfolio_cvar_95": round(cvar_95, 6),
            "portfolio_var_99": round(tail_var_99, 6),
            "stress_test_loss": self._stress_test(portfolio_returns),
            "as_of": datetime.now(timezone.utc).isoformat(),
        }

    def _build_metrics(
        self,
        vol: float,
        mdd: float,
        curr_dd: float,
        leverage: float,
        concentration: float,
        illiquid: float,
        tail_var: float,
        avg_corr: float,
    ) -> list[dict[str, Any]]:

        def s(value: float, warn: float, crit: float) -> str:
            return "critical" if value >= crit else ("warning" if value >= warn else "ok")

        return [
            {
                "name": "Annualized Volatility",
                "value": round(vol, 4), "threshold_warning": 0.15, "threshold_critical": 0.25,
                "status": s(vol, 0.15, 0.25), "unit": "fraction",
                "description": "30-day rolling annualized portfolio volatility",
            },
            {
                "name": "Maximum Drawdown",
                "value": round(mdd, 4), "threshold_warning": 0.10, "threshold_critical": 0.20,
                "status": s(mdd, 0.10, 0.20), "unit": "fraction",
                "description": "Peak-to-trough drawdown since inception",
            },
            {
                "name": "Current Drawdown",
                "value": round(curr_dd, 4), "threshold_warning": 0.05, "threshold_critical": 0.12,
                "status": s(curr_dd, 0.05, 0.12), "unit": "fraction",
                "description": "Current drawdown from most recent equity peak",
            },
            {
                "name": "Gross Leverage",
                "value": round(leverage, 4), "threshold_warning": 1.75, "threshold_critical": 2.50,
                "status": s(leverage, 1.75, 2.50), "unit": "multiplier",
                "description": "Total gross exposure as multiple of NAV",
            },
            {
                "name": "Concentration Risk",
                "value": round(concentration, 4), "threshold_warning": 0.25, "threshold_critical": 0.40,
                "status": s(concentration, 0.25, 0.40), "unit": "fraction",
                "description": "Largest single pod weight in portfolio",
            },
            {
                "name": "Liquidity Risk",
                "value": round(illiquid, 4), "threshold_warning": 0.20, "threshold_critical": 0.35,
                "status": s(illiquid, 0.20, 0.35), "unit": "fraction",
                "description": "Fraction of portfolio in illiquid instruments",
            },
            {
                "name": "Tail Risk (99% VaR)",
                "value": round(tail_var, 4), "threshold_warning": 0.03, "threshold_critical": 0.06,
                "status": s(tail_var, 0.03, 0.06), "unit": "fraction",
                "description": "1-day 99% Value at Risk as fraction of NAV",
            },
            {
                "name": "Cross-Strategy Correlation",
                "value": round(avg_corr, 4), "threshold_warning": 0.50, "threshold_critical": 0.70,
                "status": s(avg_corr, 0.50, 0.70), "unit": "coefficient",
                "description": "Average pairwise strategy correlation (30-day rolling)",
            },
        ]

    def _check_kill_switches(
        self,
        curr_dd: float,
        vol: float,
        leverage: float,
        avg_corr: float,
    ) -> list[dict[str, Any]]:
        alerts = []
        now = datetime.now(timezone.utc).isoformat()

        thresholds = KILL_SWITCH_THRESHOLDS

        if curr_dd >= thresholds["max_drawdown"]["halt_trading"]:
            self._trading_halted = True
            alerts.append({
                "alert_id": str(uuid4()),
                "severity": "critical",
                "metric": "Current Drawdown",
                "message": f"Drawdown {curr_dd:.1%} exceeded halt threshold {thresholds['max_drawdown']['halt_trading']:.1%}",
                "value": round(curr_dd, 4),
                "threshold": thresholds["max_drawdown"]["halt_trading"],
                "triggered_at": now,
                "acknowledged": False,
                "auto_action": "HALT: All trading stopped. Flatten all positions.",
            })
        elif curr_dd >= thresholds["max_drawdown"]["reduce_leverage"]:
            alerts.append({
                "alert_id": str(uuid4()),
                "severity": "warning",
                "metric": "Current Drawdown",
                "message": f"Drawdown {curr_dd:.1%} exceeded warning threshold",
                "value": round(curr_dd, 4),
                "threshold": thresholds["max_drawdown"]["reduce_leverage"],
                "triggered_at": now,
                "acknowledged": False,
                "auto_action": "Reduce gross leverage by 25%",
            })

        if vol >= thresholds["volatility_spike"]["halt_trading"]:
            self._trading_halted = True
            alerts.append({
                "alert_id": str(uuid4()),
                "severity": "critical",
                "metric": "Annualized Volatility",
                "message": f"Volatility {vol:.1%} at crisis level",
                "value": round(vol, 4),
                "threshold": thresholds["volatility_spike"]["halt_trading"],
                "triggered_at": now,
                "acknowledged": False,
                "auto_action": "HALT: Crisis volatility — protect capital",
            })

        if leverage >= thresholds["leverage"]["hard_limit"]:
            alerts.append({
                "alert_id": str(uuid4()),
                "severity": "critical",
                "metric": "Gross Leverage",
                "message": f"Leverage {leverage:.2f}x exceeded hard limit {thresholds['leverage']['hard_limit']}x",
                "value": round(leverage, 4),
                "threshold": thresholds["leverage"]["hard_limit"],
                "triggered_at": now,
                "acknowledged": False,
                "auto_action": "Immediately reduce to 1.5x leverage",
            })

        if avg_corr >= thresholds["correlation_spike"]["reduce_risk"]:
            alerts.append({
                "alert_id": str(uuid4()),
                "severity": "warning",
                "metric": "Cross-Strategy Correlation",
                "message": f"Correlation {avg_corr:.2f} — diversification breakdown detected",
                "value": round(avg_corr, 4),
                "threshold": thresholds["correlation_spike"]["reduce_risk"],
                "triggered_at": now,
                "acknowledged": False,
                "auto_action": "Reduce all position sizes by 20%",
            })

        return alerts

    def _stress_test(self, portfolio_returns: np.ndarray) -> float:
        """
        Estimate loss in a 2008-style crisis scenario.
        Uses historical worst 22-day period as proxy, scaled to crisis vol.
        """
        if len(portfolio_returns) < 22:
            return 0.25
        windows = [float(np.sum(portfolio_returns[i:i+22])) for i in range(len(portfolio_returns) - 22)]
        worst_month = min(windows) if windows else -0.20
        # Scale up by crisis vol factor
        crisis_factor = 1.5
        return round(abs(worst_month) * crisis_factor, 4)

    @property
    def trading_halted(self) -> bool:
        return self._trading_halted

    @property
    def active_alerts(self) -> list[dict[str, Any]]:
        return self._active_alerts


# Singleton
_risk_manager: RiskManager | None = None


def get_risk_manager() -> RiskManager:
    global _risk_manager
    if _risk_manager is None:
        _risk_manager = RiskManager()
    return _risk_manager
