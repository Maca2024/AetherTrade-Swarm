"""
AETHERTRADE-SWARM — Portfolio Routes
GET /api/v1/portfolio             — current portfolio state
GET /api/v1/portfolio/performance — Sharpe, returns, drawdown, win rate
GET /api/v1/portfolio/positions   — current open positions
"""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter

from api.auth import ApiKeyDep
from api.deps import SimulatorDep
from models.schemas import PerformanceMetrics, PortfolioState, Position

router = APIRouter(prefix="/api/v1/portfolio", tags=["portfolio"])


def _parse_position(raw: dict) -> Position:
    return Position(
        asset=raw["asset"],
        direction=raw["direction"],
        size=raw["size"],
        entry_price=raw["entry_price"],
        current_price=raw["current_price"],
        unrealized_pnl=raw["unrealized_pnl"],
        unrealized_pnl_pct=raw["unrealized_pnl_pct"],
        pod_source=raw["pod_source"],
        opened_at=datetime.fromisoformat(raw["opened_at"]),
        stop_loss=raw.get("stop_loss"),
        take_profit=raw.get("take_profit"),
    )


@router.get("", response_model=PortfolioState, summary="Portfolio state")
async def get_portfolio(
    _key: ApiKeyDep,
    sim: SimulatorDep,
) -> PortfolioState:
    """
    Returns the current portfolio snapshot: NAV, cash, gross/net exposure,
    leverage, position counts, and all open positions with P&L.
    """
    data = sim.get_portfolio_state()
    positions = [_parse_position(p) for p in data["positions"]]

    return PortfolioState(
        nav=data["nav"],
        cash=data["cash"],
        gross_exposure=data["gross_exposure"],
        net_exposure=data["net_exposure"],
        position_count=data["position_count"],
        long_count=data["long_count"],
        short_count=data["short_count"],
        leverage=data["leverage"],
        positions=positions,
        as_of=datetime.fromisoformat(data["as_of"]),
    )


@router.get("/performance", response_model=PerformanceMetrics, summary="Performance metrics")
async def get_performance(
    _key: ApiKeyDep,
    sim: SimulatorDep,
) -> PerformanceMetrics:
    """
    Returns full performance attribution over the 2-year simulation history:
    Sharpe, Sortino, Calmar, drawdown, win rate, profit factor, beta/alpha,
    and information ratio vs SPY benchmark.
    """
    data = sim.get_performance_metrics()
    return PerformanceMetrics(
        total_return=data["total_return"],
        ytd_return=data["ytd_return"],
        mtd_return=data["mtd_return"],
        annualized_return=data["annualized_return"],
        sharpe_ratio=data["sharpe_ratio"],
        sortino_ratio=data["sortino_ratio"],
        calmar_ratio=data["calmar_ratio"],
        max_drawdown=data["max_drawdown"],
        current_drawdown=data["current_drawdown"],
        win_rate=data["win_rate"],
        profit_factor=data["profit_factor"],
        avg_win=data["avg_win"],
        avg_loss=data["avg_loss"],
        best_day=data["best_day"],
        worst_day=data["worst_day"],
        volatility_annual=data["volatility_annual"],
        beta=data["beta"],
        alpha=data["alpha"],
        information_ratio=data["information_ratio"],
        as_of=datetime.fromisoformat(data["as_of"]),
    )


@router.get("/positions", response_model=list[Position], summary="Open positions")
async def get_positions(
    _key: ApiKeyDep,
    sim: SimulatorDep,
) -> list[Position]:
    """
    Returns the current list of open positions with entry/current price,
    unrealised P&L, stop loss, take profit, and the originating strategy pod.
    """
    data = sim.get_portfolio_state()
    return [_parse_position(p) for p in data["positions"]]
