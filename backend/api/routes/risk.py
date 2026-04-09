"""
AETHERTRADE-SWARM — Risk Routes
GET /api/v1/risk              — 8-metric risk dashboard
GET /api/v1/risk/alerts       — active risk alerts
GET /api/v1/risk/correlation  — 9x9 strategy correlation matrix
GET /api/v1/risk/kill-switches — kill switch statuses
"""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter

from api.auth import ApiKeyDep
from api.deps import SimulatorDep
from models.schemas import (
    CorrelationMatrix,
    KillSwitch,
    KillSwitchesResponse,
    RiskAlert,
    RiskAlertsResponse,
    RiskDashboard,
    RiskMetric,
)

router = APIRouter(prefix="/api/v1/risk", tags=["risk"])


@router.get("", response_model=RiskDashboard, summary="Risk dashboard")
async def get_risk_dashboard(
    _key: ApiKeyDep,
    sim: SimulatorDep,
) -> RiskDashboard:
    """
    Returns the 8-metric risk dashboard covering volatility, drawdowns,
    leverage, concentration, liquidity, tail risk, and cross-strategy
    correlation. Includes 95/99% VaR, CVaR, and 2008-style stress test loss.
    """
    data = sim.get_risk_dashboard()

    metrics = [
        RiskMetric(
            name=m["name"],
            value=m["value"],
            threshold_warning=m["threshold_warning"],
            threshold_critical=m["threshold_critical"],
            status=m["status"],
            unit=m["unit"],
            description=m["description"],
        )
        for m in data["metrics"]
    ]

    return RiskDashboard(
        overall_status=data["overall_status"],
        metrics=metrics,
        portfolio_var_95=data["portfolio_var_95"],
        portfolio_cvar_95=data["portfolio_cvar_95"],
        portfolio_var_99=data["portfolio_var_99"],
        stress_test_loss=data["stress_test_loss"],
        as_of=datetime.fromisoformat(data["as_of"]),
    )


@router.get("/alerts", response_model=RiskAlertsResponse, summary="Active risk alerts")
async def get_risk_alerts(
    _key: ApiKeyDep,
    sim: SimulatorDep,
) -> RiskAlertsResponse:
    """
    Returns all active risk alerts ordered by severity. Includes automatic
    remediation action labels and kill switch trigger status.
    """
    alerts_raw = sim.get_risk_alerts()

    alerts = [
        RiskAlert(
            alert_id=a["alert_id"],
            severity=a["severity"],
            metric=a["metric"],
            message=a["message"],
            value=a["value"],
            threshold=a["threshold"],
            triggered_at=datetime.fromisoformat(a["triggered_at"]),
            acknowledged=a["acknowledged"],
            auto_action=a.get("auto_action"),
        )
        for a in alerts_raw
    ]

    critical_count = sum(1 for a in alerts if a.severity == "critical")
    warning_count = sum(1 for a in alerts if a.severity == "warning")

    kill_data = sim.get_kill_switches()

    return RiskAlertsResponse(
        alerts=alerts,
        critical_count=critical_count,
        warning_count=warning_count,
        kill_switch_triggered=kill_data["any_triggered"],
    )


@router.get("/correlation", response_model=CorrelationMatrix, summary="Strategy correlation matrix")
async def get_correlation(
    _key: ApiKeyDep,
    sim: SimulatorDep,
) -> CorrelationMatrix:
    """
    Returns the 9x9 rolling 30-day correlation matrix across all strategy pods.
    Low cross-strategy correlation is a key diversification health signal.
    """
    data = sim.get_correlation_matrix()
    return CorrelationMatrix(
        pods=data["pods"],
        matrix=data["matrix"],
        lookback_days=data["lookback_days"],
        as_of=datetime.fromisoformat(data["as_of"]),
    )


@router.get("/kill-switches", response_model=KillSwitchesResponse, summary="Kill switch statuses")
async def get_kill_switches(
    _key: ApiKeyDep,
    sim: SimulatorDep,
) -> KillSwitchesResponse:
    """
    Returns the status of all automated kill switches (max drawdown, daily
    loss limit, leverage limit, correlation spike). Trading is halted if any
    critical switch fires.
    """
    data = sim.get_kill_switches()

    switches = [
        KillSwitch(
            name=ks["name"],
            triggered=ks["triggered"],
            threshold=ks["threshold"],
            current_value=ks["current_value"],
            description=ks["description"],
            auto_action=ks["auto_action"],
            last_checked=datetime.fromisoformat(ks["last_checked"]),
        )
        for ks in data["kill_switches"]
    ]

    return KillSwitchesResponse(
        kill_switches=switches,
        any_triggered=data["any_triggered"],
        trading_halted=data["trading_halted"],
    )
