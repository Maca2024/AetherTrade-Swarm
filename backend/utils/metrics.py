"""
AETHERTRADE-SWARM — Performance & Risk Metrics
Financial calculations: Sharpe, Sortino, VaR, CVaR, drawdown, etc.
"""
from __future__ import annotations

import math
from typing import Sequence

import numpy as np


TRADING_DAYS_PER_YEAR = 252
RISK_FREE_RATE_ANNUAL = 0.045  # 4.5% USD risk-free (2024 proxy)


# ---------------------------------------------------------------------------
# Return calculations
# ---------------------------------------------------------------------------

def annualized_return(returns: Sequence[float], periods_per_year: int = TRADING_DAYS_PER_YEAR) -> float:
    """Compound annualized growth rate from a series of period returns."""
    arr = np.asarray(returns, dtype=float)
    if len(arr) == 0:
        return 0.0
    cumulative = np.prod(1.0 + arr)
    n = len(arr)
    return float(cumulative ** (periods_per_year / n) - 1.0)


def annualized_volatility(returns: Sequence[float], periods_per_year: int = TRADING_DAYS_PER_YEAR) -> float:
    arr = np.asarray(returns, dtype=float)
    if len(arr) < 2:
        return 0.0
    return float(np.std(arr, ddof=1) * math.sqrt(periods_per_year))


# ---------------------------------------------------------------------------
# Risk-adjusted ratios
# ---------------------------------------------------------------------------

def sharpe_ratio(
    returns: Sequence[float],
    risk_free: float = RISK_FREE_RATE_ANNUAL,
    periods_per_year: int = TRADING_DAYS_PER_YEAR,
) -> float:
    arr = np.asarray(returns, dtype=float)
    if len(arr) < 2:
        return 0.0
    rf_per_period = (1.0 + risk_free) ** (1.0 / periods_per_year) - 1.0
    excess = arr - rf_per_period
    vol = float(np.std(excess, ddof=1))
    if vol == 0.0:
        return 0.0
    return float(np.mean(excess) / vol * math.sqrt(periods_per_year))


def sortino_ratio(
    returns: Sequence[float],
    risk_free: float = RISK_FREE_RATE_ANNUAL,
    periods_per_year: int = TRADING_DAYS_PER_YEAR,
) -> float:
    arr = np.asarray(returns, dtype=float)
    if len(arr) < 2:
        return 0.0
    rf_per_period = (1.0 + risk_free) ** (1.0 / periods_per_year) - 1.0
    excess = arr - rf_per_period
    downside = excess[excess < 0.0]
    if len(downside) == 0:
        return float("inf") if np.mean(excess) > 0 else 0.0
    downside_vol = float(np.std(downside, ddof=1) * math.sqrt(periods_per_year))
    if downside_vol == 0.0:
        return 0.0
    return float(annualized_return(arr, periods_per_year) - risk_free) / downside_vol


def calmar_ratio(returns: Sequence[float], periods_per_year: int = TRADING_DAYS_PER_YEAR) -> float:
    mdd = max_drawdown(returns)
    if mdd == 0.0:
        return float("inf")
    ann_ret = annualized_return(returns, periods_per_year)
    return float(ann_ret / abs(mdd))


# ---------------------------------------------------------------------------
# Drawdown
# ---------------------------------------------------------------------------

def max_drawdown(returns: Sequence[float]) -> float:
    """Returns max drawdown as a negative fraction (e.g. -0.12 for 12%)."""
    arr = np.asarray(returns, dtype=float)
    if len(arr) == 0:
        return 0.0
    cumulative = np.cumprod(1.0 + arr)
    running_max = np.maximum.accumulate(cumulative)
    drawdowns = cumulative / running_max - 1.0
    return float(np.min(drawdowns))


def current_drawdown(returns: Sequence[float]) -> float:
    arr = np.asarray(returns, dtype=float)
    if len(arr) == 0:
        return 0.0
    cumulative = np.cumprod(1.0 + arr)
    peak = float(np.max(cumulative))
    current = float(cumulative[-1])
    return float(current / peak - 1.0)


def drawdown_series(returns: Sequence[float]) -> np.ndarray:
    arr = np.asarray(returns, dtype=float)
    cumulative = np.cumprod(1.0 + arr)
    running_max = np.maximum.accumulate(cumulative)
    return cumulative / running_max - 1.0


# ---------------------------------------------------------------------------
# Value at Risk
# ---------------------------------------------------------------------------

def historical_var(returns: Sequence[float], confidence: float = 0.95) -> float:
    """Historical simulation VaR — negative fraction (loss)."""
    arr = np.asarray(returns, dtype=float)
    if len(arr) == 0:
        return 0.0
    return float(np.percentile(arr, (1.0 - confidence) * 100))


def historical_cvar(returns: Sequence[float], confidence: float = 0.95) -> float:
    """Conditional VaR / Expected Shortfall — mean of tail losses."""
    arr = np.asarray(returns, dtype=float)
    if len(arr) == 0:
        return 0.0
    var = historical_var(arr, confidence)
    tail = arr[arr <= var]
    if len(tail) == 0:
        return var
    return float(np.mean(tail))


def parametric_var(
    returns: Sequence[float],
    confidence: float = 0.95,
    periods_per_year: int = TRADING_DAYS_PER_YEAR,
) -> float:
    """Gaussian parametric VaR (1-day)."""
    from scipy import stats  # type: ignore

    arr = np.asarray(returns, dtype=float)
    if len(arr) < 2:
        return 0.0
    mu = float(np.mean(arr))
    sigma = float(np.std(arr, ddof=1))
    z = stats.norm.ppf(1.0 - confidence)
    return float(mu + z * sigma)


# ---------------------------------------------------------------------------
# Trade statistics
# ---------------------------------------------------------------------------

def win_rate(returns: Sequence[float]) -> float:
    arr = np.asarray(returns, dtype=float)
    if len(arr) == 0:
        return 0.0
    return float(np.sum(arr > 0) / len(arr))


def profit_factor(returns: Sequence[float]) -> float:
    arr = np.asarray(returns, dtype=float)
    gains = arr[arr > 0]
    losses = arr[arr < 0]
    gross_profit = float(np.sum(gains)) if len(gains) > 0 else 0.0
    gross_loss = abs(float(np.sum(losses))) if len(losses) > 0 else 0.0
    if gross_loss == 0.0:
        return float("inf") if gross_profit > 0 else 0.0
    return gross_profit / gross_loss


def beta_alpha(
    portfolio_returns: Sequence[float],
    benchmark_returns: Sequence[float],
    risk_free: float = RISK_FREE_RATE_ANNUAL,
    periods_per_year: int = TRADING_DAYS_PER_YEAR,
) -> tuple[float, float]:
    """Returns (beta, alpha_annualized)."""
    port = np.asarray(portfolio_returns, dtype=float)
    bench = np.asarray(benchmark_returns, dtype=float)
    n = min(len(port), len(bench))
    if n < 2:
        return 1.0, 0.0
    port, bench = port[:n], bench[:n]
    cov_matrix = np.cov(port, bench, ddof=1)
    var_bench = cov_matrix[1, 1]
    if var_bench == 0.0:
        return 1.0, 0.0
    beta = float(cov_matrix[0, 1] / var_bench)
    rf_per_period = (1.0 + risk_free) ** (1.0 / periods_per_year) - 1.0
    alpha = float(
        annualized_return(port, periods_per_year)
        - risk_free
        - beta * (annualized_return(bench, periods_per_year) - risk_free)
    )
    return beta, alpha


def information_ratio(
    portfolio_returns: Sequence[float],
    benchmark_returns: Sequence[float],
    periods_per_year: int = TRADING_DAYS_PER_YEAR,
) -> float:
    port = np.asarray(portfolio_returns, dtype=float)
    bench = np.asarray(benchmark_returns, dtype=float)
    n = min(len(port), len(bench))
    if n < 2:
        return 0.0
    active = port[:n] - bench[:n]
    tracking_error = float(np.std(active, ddof=1) * math.sqrt(periods_per_year))
    if tracking_error == 0.0:
        return 0.0
    active_return = annualized_return(port[:n], periods_per_year) - annualized_return(bench[:n], periods_per_year)
    return float(active_return / tracking_error)
