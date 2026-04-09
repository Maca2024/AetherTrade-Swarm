"""
AETHERTRADE-SWARM — Pydantic v2 Schemas
All request/response models for the API.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class RegimeState(str, Enum):
    BULL = "bull"
    RANGE = "range"
    BEAR = "bear"
    CRISIS = "crisis"


class KeyTier(str, Enum):
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class SignalDirection(str, Enum):
    LONG = "long"
    SHORT = "short"
    NEUTRAL = "neutral"


class AlertSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class PodName(str, Enum):
    MOMENTUM = "momentum"
    MEAN_REVERSION = "mean_reversion"
    MACRO = "macro"
    STAT_ARB = "stat_arb"
    OPTIONS_VOL = "options_vol"
    BEHAVIORAL = "behavioral"
    AI_ML = "ai_ml"
    MULTI_FACTOR = "multi_factor"
    MARKET_MAKING = "market_making"


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------

class OracleBaseModel(BaseModel):
    model_config = {"populate_by_name": True, "use_enum_values": True}


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

class ServiceStatus(OracleBaseModel):
    name: str
    status: str = Field(description="healthy | degraded | down")
    latency_ms: float | None = None
    detail: str | None = None


class HealthResponse(OracleBaseModel):
    status: str = Field(description="healthy | degraded | down")
    version: str
    environment: str
    uptime_seconds: float
    timestamp: datetime
    services: list[ServiceStatus]


# ---------------------------------------------------------------------------
# Regime
# ---------------------------------------------------------------------------

class RegimeResponse(OracleBaseModel):
    regime: RegimeState
    confidence: float = Field(ge=0.0, le=1.0)
    probabilities: dict[str, float] = Field(
        description="State probabilities summing to 1.0"
    )
    duration_days: int = Field(description="Days in current regime")
    last_transition: datetime
    signal_impact: dict[str, str] = Field(
        description="Recommended allocation adjustments per pod"
    )


class RegimeTransition(OracleBaseModel):
    from_regime: RegimeState
    to_regime: RegimeState
    timestamp: datetime
    confidence: float = Field(ge=0.0, le=1.0)
    trigger: str


class RegimeHistoryResponse(OracleBaseModel):
    transitions: list[RegimeTransition]
    current_regime: RegimeState
    regime_distribution: dict[str, float] = Field(
        description="Percentage of time in each regime over lookback period"
    )
    lookback_days: int


# ---------------------------------------------------------------------------
# Strategy Pods
# ---------------------------------------------------------------------------

class SignalDetail(OracleBaseModel):
    asset: str
    signal_name: str
    direction: SignalDirection
    strength: float = Field(ge=-1.0, le=1.0, description="-1=max short, +1=max long")
    confidence: float = Field(ge=0.0, le=1.0)
    timestamp: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


class PodMetrics(OracleBaseModel):
    pod_name: PodName
    display_name: str
    status: str = Field(description="active | paused | error")
    regime_allocation: float = Field(ge=0.0, le=1.0, description="Current weight in ensemble")
    ytd_return: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float = Field(ge=0.0, le=1.0)
    signal_count: int
    last_signal_at: datetime
    description: str


class PodListResponse(OracleBaseModel):
    pods: list[PodMetrics]
    total_active: int
    ensemble_allocation_sum: float


class PodSignalsResponse(OracleBaseModel):
    pod_name: PodName
    signals: list[SignalDetail]
    aggregate_direction: SignalDirection
    aggregate_strength: float = Field(ge=-1.0, le=1.0)
    generated_at: datetime


# ---------------------------------------------------------------------------
# Signals
# ---------------------------------------------------------------------------

class CombinedSignalResponse(OracleBaseModel):
    ensemble_direction: SignalDirection
    ensemble_strength: float = Field(ge=-1.0, le=1.0)
    regime_adjusted: bool
    pod_contributions: dict[str, float] = Field(
        description="Each pod's weighted contribution to ensemble"
    )
    top_signals: list[SignalDetail]
    generated_at: datetime
    confidence: float = Field(ge=0.0, le=1.0)


class AllocationResponse(OracleBaseModel):
    strategy_weights: dict[str, float] = Field(
        description="Pod name → portfolio weight"
    )
    regime: RegimeState
    regime_override_active: bool
    rebalance_required: bool
    last_rebalance: datetime
    next_rebalance: datetime


# ---------------------------------------------------------------------------
# Portfolio
# ---------------------------------------------------------------------------

class Position(OracleBaseModel):
    asset: str
    direction: SignalDirection
    size: float = Field(description="Position size as fraction of NAV")
    entry_price: float
    current_price: float
    unrealized_pnl: float
    unrealized_pnl_pct: float
    pod_source: PodName
    opened_at: datetime
    stop_loss: float | None = None
    take_profit: float | None = None


class PortfolioState(OracleBaseModel):
    nav: float = Field(description="Net Asset Value in USD")
    cash: float
    gross_exposure: float
    net_exposure: float
    position_count: int
    long_count: int
    short_count: int
    leverage: float
    positions: list[Position]
    as_of: datetime


class PerformanceMetrics(OracleBaseModel):
    total_return: float
    ytd_return: float
    mtd_return: float
    annualized_return: float
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    max_drawdown: float
    current_drawdown: float
    win_rate: float
    profit_factor: float
    avg_win: float
    avg_loss: float
    best_day: float
    worst_day: float
    volatility_annual: float
    beta: float
    alpha: float
    information_ratio: float
    as_of: datetime


# ---------------------------------------------------------------------------
# Risk
# ---------------------------------------------------------------------------

class RiskMetric(OracleBaseModel):
    name: str
    value: float
    threshold_warning: float
    threshold_critical: float
    status: str = Field(description="ok | warning | critical")
    unit: str
    description: str


class RiskDashboard(OracleBaseModel):
    overall_status: str = Field(description="ok | warning | critical")
    metrics: list[RiskMetric]
    portfolio_var_95: float = Field(description="1-day 95% VaR")
    portfolio_cvar_95: float = Field(description="1-day 95% CVaR / Expected Shortfall")
    portfolio_var_99: float
    stress_test_loss: float = Field(description="Estimated loss in 2008-style crisis")
    as_of: datetime


class RiskAlert(OracleBaseModel):
    alert_id: str
    severity: AlertSeverity
    metric: str
    message: str
    value: float
    threshold: float
    triggered_at: datetime
    acknowledged: bool = False
    auto_action: str | None = None


class RiskAlertsResponse(OracleBaseModel):
    alerts: list[RiskAlert]
    critical_count: int
    warning_count: int
    kill_switch_triggered: bool


class CorrelationMatrix(OracleBaseModel):
    pods: list[str]
    matrix: list[list[float]]
    lookback_days: int
    as_of: datetime


class KillSwitch(OracleBaseModel):
    name: str
    triggered: bool
    threshold: float
    current_value: float
    description: str
    auto_action: str
    last_checked: datetime


class KillSwitchesResponse(OracleBaseModel):
    kill_switches: list[KillSwitch]
    any_triggered: bool
    trading_halted: bool


# ---------------------------------------------------------------------------
# Backtest
# ---------------------------------------------------------------------------

class BacktestRequest(OracleBaseModel):
    pods: list[PodName] = Field(
        description="Strategy pods to include in backtest",
        min_length=1,
    )
    start_date: str = Field(description="ISO date string YYYY-MM-DD")
    end_date: str = Field(description="ISO date string YYYY-MM-DD")
    initial_capital: float = Field(default=1_000_000.0, ge=10_000.0)
    leverage_limit: float = Field(default=2.0, ge=1.0, le=10.0)

    @field_validator("pods", mode="before")
    @classmethod
    def validate_pods(cls, v: list[str]) -> list[str]:
        valid = {p.value for p in PodName}
        for pod in v:
            if pod not in valid:
                raise ValueError(f"Unknown pod: {pod}. Valid pods: {sorted(valid)}")
        return v


class BacktestResult(OracleBaseModel):
    run_id: str
    pods: list[str]
    start_date: str
    end_date: str
    initial_capital: float
    final_capital: float
    total_return: float
    annualized_return: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    calmar_ratio: float
    win_rate: float
    total_trades: int
    equity_curve: list[dict[str, Any]] = Field(
        description="List of {date, nav, drawdown} data points"
    )
    regime_breakdown: dict[str, float] = Field(
        description="Performance per regime"
    )
    pod_contributions: dict[str, float]
    run_duration_ms: float


# ---------------------------------------------------------------------------
# API Keys
# ---------------------------------------------------------------------------

class GenerateKeyRequest(OracleBaseModel):
    name: str = Field(min_length=3, max_length=64, description="Human-readable key name")
    tier: KeyTier = Field(default=KeyTier.FREE)
    owner_email: str = Field(default="anonymous@aethertrade-swarm.ai", description="Email address of key owner")
    description: str | None = Field(default=None, max_length=256)


class GenerateKeyResponse(OracleBaseModel):
    key_id: str
    api_key: str = Field(description="Full API key — shown ONCE, store securely")
    name: str
    tier: KeyTier
    rate_limit_per_minute: int
    created_at: datetime
    warning: str = "Store this key securely. It will not be shown again."


class ApiKeyInfo(OracleBaseModel):
    key_id: str
    name: str
    tier: KeyTier
    prefix: str = Field(description="First 8 chars of key for identification")
    owner_email: str
    created_at: datetime
    last_used_at: datetime | None = None
    request_count: int
    is_active: bool


class ApiKeyListResponse(OracleBaseModel):
    keys: list[ApiKeyInfo]
    total: int


class RotateKeyResponse(OracleBaseModel):
    key_id: str
    new_api_key: str = Field(description="New key — shown ONCE, store securely")
    old_key_invalidated: bool
    rotated_at: datetime


# ---------------------------------------------------------------------------
# WebSocket
# ---------------------------------------------------------------------------

class StreamMessage(OracleBaseModel):
    event: str = Field(description="regime_update | signal | risk_alert | heartbeat")
    payload: dict[str, Any]
    timestamp: datetime
    sequence: int


# ---------------------------------------------------------------------------
# Error
# ---------------------------------------------------------------------------

class ErrorDetail(OracleBaseModel):
    code: str
    message: str
    detail: str | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ErrorResponse(OracleBaseModel):
    error: ErrorDetail
