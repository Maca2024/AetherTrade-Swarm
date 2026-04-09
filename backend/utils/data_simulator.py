"""
AETHERTRADE-SWARM — Realistic Trading Data Simulator
Generates correlated strategy returns, regime transitions, positions,
and risk metrics that update over time.
"""
from __future__ import annotations

import math
import random
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

import numpy as np

from models.schemas import PodName, RegimeState, SignalDirection


# ---------------------------------------------------------------------------
# Regime parameters — (mu_daily, sigma_daily, duration_days_avg)
# ---------------------------------------------------------------------------
REGIME_PARAMS: dict[str, dict[str, float]] = {
    RegimeState.BULL: {
        "mu": 0.0008,          # ~20% annual
        "sigma": 0.007,        # ~11% annual vol
        "mean_duration": 180,  # average 6 months
        "weight": 0.60,
    },
    RegimeState.RANGE: {
        "mu": 0.0001,
        "sigma": 0.009,
        "mean_duration": 60,
        "weight": 0.20,
    },
    RegimeState.BEAR: {
        "mu": -0.0006,
        "sigma": 0.014,
        "mean_duration": 90,
        "weight": 0.15,
    },
    RegimeState.CRISIS: {
        "mu": -0.003,
        "sigma": 0.030,
        "mean_duration": 20,
        "weight": 0.05,
    },
}

# Pod correlation structure — lower triangular, then symmetrised
# Order: momentum, mean_reversion, macro, stat_arb, options_vol,
#        behavioral, ai_ml, multi_factor, market_making
_CORR_LOWER = [
    [1.0,   0.0,   0.0,   0.0,  0.0,   0.0,  0.0,  0.0,  0.0],
    [-0.2,  1.0,   0.0,   0.0,  0.0,   0.0,  0.0,  0.0,  0.0],
    [0.3,  -0.1,   1.0,   0.0,  0.0,   0.0,  0.0,  0.0,  0.0],
    [-0.1,  0.4,   0.0,   1.0,  0.0,   0.0,  0.0,  0.0,  0.0],
    [-0.3,  0.2,  -0.2,   0.1,  1.0,   0.0,  0.0,  0.0,  0.0],
    [0.4,  -0.1,   0.2,  -0.1, -0.2,   1.0,  0.0,  0.0,  0.0],
    [0.5,  -0.2,   0.3,  -0.1, -0.3,   0.4,  1.0,  0.0,  0.0],
    [0.6,  -0.1,   0.4,  -0.0, -0.2,   0.3,  0.5,  1.0,  0.0],
    [-0.1,  0.3,  -0.1,   0.3,  0.2,  -0.1,  0.0,  0.0,  1.0],
]

# Pod-specific return adjustments per regime
POD_REGIME_ALPHA: dict[str, dict[str, float]] = {
    PodName.MOMENTUM:       {RegimeState.BULL: 0.0006,  RegimeState.RANGE: -0.0004, RegimeState.BEAR: -0.0008, RegimeState.CRISIS: -0.002},
    PodName.MEAN_REVERSION: {RegimeState.BULL: -0.0002, RegimeState.RANGE:  0.0005, RegimeState.BEAR:  0.0003, RegimeState.CRISIS:  0.001},
    PodName.MACRO:          {RegimeState.BULL:  0.0003, RegimeState.RANGE:  0.0001, RegimeState.BEAR:  0.0002, RegimeState.CRISIS:  0.0005},
    PodName.STAT_ARB:       {RegimeState.BULL: -0.0001, RegimeState.RANGE:  0.0004, RegimeState.BEAR:  0.0002, RegimeState.CRISIS: -0.001},
    PodName.OPTIONS_VOL:    {RegimeState.BULL: -0.0003, RegimeState.RANGE:  0.0002, RegimeState.BEAR:  0.0005, RegimeState.CRISIS:  0.003},
    PodName.BEHAVIORAL:     {RegimeState.BULL:  0.0002, RegimeState.RANGE:  0.0001, RegimeState.BEAR: -0.0003, RegimeState.CRISIS: -0.0005},
    PodName.AI_ML:          {RegimeState.BULL:  0.0004, RegimeState.RANGE:  0.0002, RegimeState.BEAR: -0.0002, RegimeState.CRISIS: -0.001},
    PodName.MULTI_FACTOR:   {RegimeState.BULL:  0.0005, RegimeState.RANGE:  0.0000, RegimeState.BEAR: -0.0004, RegimeState.CRISIS: -0.0015},
    PodName.MARKET_MAKING:  {RegimeState.BULL:  0.0001, RegimeState.RANGE:  0.0003, RegimeState.BEAR:  0.0001, RegimeState.CRISIS: -0.002},
}

PODS_ORDER = [
    PodName.MOMENTUM, PodName.MEAN_REVERSION, PodName.MACRO,
    PodName.STAT_ARB, PodName.OPTIONS_VOL, PodName.BEHAVIORAL,
    PodName.AI_ML, PodName.MULTI_FACTOR, PodName.MARKET_MAKING,
]


def _build_corr_matrix() -> np.ndarray:
    n = len(PODS_ORDER)
    M = np.array(_CORR_LOWER, dtype=float)
    # Symmetrise
    corr = M + M.T - np.eye(n)
    # Ensure positive definite
    eigvals = np.linalg.eigvals(corr)
    if np.any(eigvals <= 0):
        corr += np.eye(n) * (abs(min(eigvals)) + 0.01)
        d = np.sqrt(np.diag(corr))
        corr = corr / np.outer(d, d)
    return corr


CORR_MATRIX: np.ndarray = _build_corr_matrix()


class DataSimulator:
    """
    Generates all simulated data consumed by the AETHERTRADE-SWARM API.
    State is deterministic from seed; call refresh() to advance time.
    """

    def __init__(self, seed: int = 42) -> None:
        self._rng = np.random.default_rng(seed)
        self._random = random.Random(seed)

        self._start_nav = 10_000_000.0
        self._nav = self._start_nav
        self._inception_date = datetime.now(timezone.utc) - timedelta(days=730)

        # Simulate 2 years of history
        self._regime_history: list[dict[str, Any]] = []
        self._equity_curve: list[dict[str, Any]] = []
        self._pod_equity: dict[str, list[float]] = {p.value: [] for p in PODS_ORDER}
        self._dates: list[datetime] = []

        self._current_regime: RegimeState = RegimeState.BULL
        self._regime_confidence: float = 0.85
        self._regime_duration: int = 0

        self._simulate_history()
        self._refresh_metrics()

    # ------------------------------------------------------------------
    # Historical generation
    # ------------------------------------------------------------------

    def _simulate_history(self) -> None:
        chol = np.linalg.cholesky(CORR_MATRIX)
        n_pods = len(PODS_ORDER)

        regime = RegimeState.BULL
        days_in_regime = 0
        current_date = self._inception_date

        regime_start = current_date
        nav = self._start_nav
        pod_navs = [nav / n_pods] * n_pods

        total_days = 730
        for day in range(total_days):
            current_date = self._inception_date + timedelta(days=day)
            params = REGIME_PARAMS[regime]

            # Regime transition probability
            mean_dur = params["mean_duration"]
            p_transition = 1.0 / mean_dur
            if self._rng.random() < p_transition and days_in_regime > 5:
                new_regime = self._sample_regime(exclude=regime)
                self._regime_history.append({
                    "from_regime": regime,
                    "to_regime": new_regime,
                    "timestamp": current_date.isoformat(),
                    "confidence": float(self._rng.uniform(0.7, 0.95)),
                    "trigger": self._random.choice([
                        "Volatility breakout", "Trend reversal", "Macro event",
                        "Liquidity squeeze", "Earnings surprise", "Fed pivot",
                    ]),
                    "duration_days": days_in_regime,
                })
                regime = new_regime
                days_in_regime = 0
                regime_start = current_date
            else:
                days_in_regime += 1

            # Generate correlated pod returns
            market_return = self._rng.normal(params["mu"], params["sigma"])
            z = self._rng.standard_normal(n_pods)
            correlated_z = chol @ z

            pod_returns = []
            for i, pod in enumerate(PODS_ORDER):
                pod_alpha = POD_REGIME_ALPHA[pod][regime]
                pod_sigma = params["sigma"] * (0.6 + 0.8 * abs(correlated_z[i]))
                pod_return = params["mu"] + pod_alpha + correlated_z[i] * pod_sigma * 0.4
                pod_returns.append(pod_return)
                pod_navs[i] *= (1.0 + pod_return)
                self._pod_equity[PODS_ORDER[i].value].append(pod_return)

            # Ensemble = weighted average
            weights = self._regime_weights(regime)
            ensemble_return = sum(w * r for w, r in zip(weights, pod_returns))
            nav *= (1.0 + ensemble_return)

            self._dates.append(current_date)
            dd = self._calc_drawdown_at(nav, self._start_nav)
            self._equity_curve.append({
                "date": current_date.strftime("%Y-%m-%d"),
                "nav": round(nav, 2),
                "return": round(ensemble_return, 6),
                "drawdown": round(dd, 6),
                "regime": regime,
            })

        self._nav = nav
        self._current_regime = regime
        self._regime_duration = days_in_regime
        self._regime_confidence = float(self._rng.uniform(0.72, 0.95))

    def _sample_regime(self, exclude: RegimeState) -> RegimeState:
        regimes = [r for r in RegimeState if r != exclude]
        weights = [REGIME_PARAMS[r]["weight"] for r in regimes]
        total = sum(weights)
        weights = [w / total for w in weights]
        idx = int(self._rng.choice(len(regimes), p=weights))
        return regimes[idx]

    def _regime_weights(self, regime: RegimeState) -> list[float]:
        """Portfolio weights per pod based on regime."""
        if regime == RegimeState.BULL:
            return [0.20, 0.05, 0.15, 0.05, 0.05, 0.10, 0.15, 0.15, 0.10]
        elif regime == RegimeState.RANGE:
            return [0.05, 0.20, 0.10, 0.20, 0.10, 0.10, 0.10, 0.05, 0.10]
        elif regime == RegimeState.BEAR:
            return [0.05, 0.15, 0.20, 0.10, 0.20, 0.05, 0.10, 0.05, 0.10]
        else:  # CRISIS
            return [0.00, 0.10, 0.30, 0.05, 0.30, 0.05, 0.05, 0.05, 0.10]

    def _calc_drawdown_at(self, current_nav: float, peak_nav: float) -> float:
        if peak_nav == 0:
            return 0.0
        return max(0.0, current_nav / peak_nav - 1.0) if current_nav > peak_nav else current_nav / peak_nav - 1.0

    def _refresh_metrics(self) -> None:
        from utils.metrics import (
            annualized_return, annualized_volatility, sharpe_ratio,
            sortino_ratio, calmar_ratio, max_drawdown, win_rate,
            profit_factor, beta_alpha, historical_var, historical_cvar,
        )
        returns = [e["return"] for e in self._equity_curve]
        self._ann_return = annualized_return(returns)
        self._ann_vol = annualized_volatility(returns)
        self._sharpe = sharpe_ratio(returns)
        self._sortino = sortino_ratio(returns)
        self._calmar = calmar_ratio(returns)
        self._mdd = max_drawdown(returns)
        self._win_rate = win_rate(returns)
        self._profit_factor = profit_factor(returns)

        # Simulate benchmark (SPY-like)
        spy_returns = [e["return"] * 0.8 + self._rng.normal(0.0002, 0.003) for e in self._equity_curve]
        self._beta, self._alpha = beta_alpha(returns, spy_returns)

        self._var_95 = historical_var(returns, 0.95)
        self._cvar_95 = historical_cvar(returns, 0.95)
        self._var_99 = historical_var(returns, 0.99)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_regime(self) -> dict[str, Any]:
        probs = self._regime_probabilities()
        regime_impact = {
            "momentum":       "overweight" if self._current_regime == RegimeState.BULL else "underweight",
            "mean_reversion": "overweight" if self._current_regime == RegimeState.RANGE else "neutral",
            "macro":          "overweight" if self._current_regime in (RegimeState.BEAR, RegimeState.CRISIS) else "neutral",
            "options_vol":    "overweight" if self._current_regime == RegimeState.CRISIS else "neutral",
            "ai_ml":          "neutral",
            "stat_arb":       "overweight" if self._current_regime == RegimeState.RANGE else "neutral",
            "behavioral":     "underweight" if self._current_regime == RegimeState.CRISIS else "neutral",
            "multi_factor":   "overweight" if self._current_regime == RegimeState.BULL else "neutral",
            "market_making":  "neutral" if self._current_regime != RegimeState.CRISIS else "halt",
        }
        last_transition = self._regime_history[-1] if self._regime_history else None
        return {
            "regime": self._current_regime,
            "confidence": self._regime_confidence,
            "probabilities": probs,
            "duration_days": self._regime_duration,
            "last_transition": last_transition["timestamp"] if last_transition else datetime.now(timezone.utc).isoformat(),
            "signal_impact": regime_impact,
        }

    def _regime_probabilities(self) -> dict[str, float]:
        conf = self._regime_confidence
        regimes = [r for r in RegimeState]
        current_idx = regimes.index(self._current_regime)
        probs = [0.0] * 4
        probs[current_idx] = conf
        remaining = 1.0 - conf
        for i, r in enumerate(regimes):
            if i != current_idx:
                weight = REGIME_PARAMS[r]["weight"]
                probs[i] = remaining * weight / sum(REGIME_PARAMS[x]["weight"] for x in regimes if x != self._current_regime)
        return {r: round(p, 4) for r, p in zip(regimes, probs)}

    def get_regime_history(self, limit: int = 20) -> list[dict[str, Any]]:
        return list(reversed(self._regime_history[-limit:]))

    def get_regime_distribution(self) -> dict[str, float]:
        counts: dict[str, int] = {r: 0 for r in RegimeState}
        for pt in self._equity_curve:
            counts[pt["regime"]] = counts.get(pt["regime"], 0) + 1
        total = len(self._equity_curve) or 1
        return {r: round(counts[r] / total, 4) for r in RegimeState}

    def get_pod_metrics(self) -> list[dict[str, Any]]:
        from utils.metrics import sharpe_ratio, max_drawdown, win_rate, annualized_return

        weights = self._regime_weights(self._current_regime)
        pods = []
        for i, pod in enumerate(PODS_ORDER):
            pod_returns = self._pod_equity[pod.value]
            ann_r = annualized_return(pod_returns)
            sr = sharpe_ratio(pod_returns)
            mdd = max_drawdown(pod_returns)
            wr = win_rate(pod_returns)

            display_names = {
                PodName.MOMENTUM: "Vol-Scaled Momentum",
                PodName.MEAN_REVERSION: "Mean Reversion",
                PodName.MACRO: "Global Macro / Risk Parity",
                PodName.STAT_ARB: "Statistical Arbitrage",
                PodName.OPTIONS_VOL: "Options & Volatility",
                PodName.BEHAVIORAL: "Behavioral / Sentiment",
                PodName.AI_ML: "AI/ML Ensemble",
                PodName.MULTI_FACTOR: "Multi-Factor (AQR-style)",
                PodName.MARKET_MAKING: "Market Making",
            }

            descriptions = {
                PodName.MOMENTUM: "Cross-sectional and time-series momentum with volatility scaling. Captures trend-following alpha across equities, futures, and crypto.",
                PodName.MEAN_REVERSION: "Statistical pairs trading + RSI-2 reversion. Profits from mean-reverting price dynamics in correlated instruments.",
                PodName.MACRO: "Risk parity, carry trades, and macro trend signals. Provides portfolio diversification across asset classes.",
                PodName.STAT_ARB: "PCA residual trading + post-earnings announcement drift. Market-neutral statistical edge.",
                PodName.OPTIONS_VOL: "Volatility risk premium harvesting + tail hedge management. Sells rich implied vol, buys cheap convexity.",
                PodName.BEHAVIORAL: "Sentiment analysis + contrarian signals from positioning data. Exploits behavioral biases.",
                PodName.AI_ML: "LLM-derived macro signals + Temporal Fusion Transformer + RL-based execution optimization.",
                PodName.MULTI_FACTOR: "AQR-style systematic long/short across value, quality, momentum, low-volatility factors.",
                PodName.MARKET_MAKING: "Order flow imbalance signals + bid-ask spread capture. Ultra-short-term liquidity provision.",
            }

            signal_counts = {
                PodName.MOMENTUM: 24, PodName.MEAN_REVERSION: 18, PodName.MACRO: 12,
                PodName.STAT_ARB: 31, PodName.OPTIONS_VOL: 8, PodName.BEHAVIORAL: 15,
                PodName.AI_ML: 10, PodName.MULTI_FACTOR: 42, PodName.MARKET_MAKING: 6,
            }

            pods.append({
                "pod_name": pod.value,
                "display_name": display_names[pod],
                "status": "active",
                "regime_allocation": round(weights[i], 4),
                "ytd_return": round(ann_r, 6),
                "sharpe_ratio": round(sr, 4),
                "max_drawdown": round(mdd, 6),
                "win_rate": round(wr, 4),
                "signal_count": signal_counts[pod],
                "last_signal_at": (datetime.now(timezone.utc) - timedelta(minutes=self._random.randint(1, 30))).isoformat(),
                "description": descriptions[pod],
            })
        return pods

    def get_pod_signals(self, pod_name: str) -> dict[str, Any]:
        assets = ["AAPL", "MSFT", "AMZN", "GOOGL", "NVDA", "TSLA", "SPY", "QQQ", "GLD", "TLT", "BTC", "ETH"]
        directions = [SignalDirection.LONG, SignalDirection.SHORT, SignalDirection.NEUTRAL]
        direction_weights = [0.45, 0.35, 0.20]

        signals = []
        n_signals = self._random.randint(3, 8)
        for _ in range(n_signals):
            direction = self._random.choices(directions, weights=direction_weights)[0]
            strength = self._rng.uniform(-0.9, 0.9)
            if direction == SignalDirection.LONG:
                strength = abs(strength)
            elif direction == SignalDirection.SHORT:
                strength = -abs(strength)
            else:
                strength = self._rng.uniform(-0.1, 0.1)

            signals.append({
                "asset": self._random.choice(assets),
                "signal_name": f"{pod_name}_signal_{self._random.randint(1, 99):02d}",
                "direction": direction.value,
                "strength": round(float(strength), 4),
                "confidence": round(float(self._rng.uniform(0.55, 0.95)), 4),
                "timestamp": (datetime.now(timezone.utc) - timedelta(minutes=self._random.randint(0, 60))).isoformat(),
                "metadata": {
                    "model_version": "v2.3",
                    "lookback_days": self._random.choice([5, 10, 21, 63]),
                },
            })

        agg_strength = float(np.mean([s["strength"] for s in signals]))
        if agg_strength > 0.1:
            agg_dir = SignalDirection.LONG
        elif agg_strength < -0.1:
            agg_dir = SignalDirection.SHORT
        else:
            agg_dir = SignalDirection.NEUTRAL

        return {
            "pod_name": pod_name,
            "signals": signals,
            "aggregate_direction": agg_dir.value,
            "aggregate_strength": round(agg_strength, 4),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    def get_combined_signal(self) -> dict[str, Any]:
        weights = self._regime_weights(self._current_regime)
        pod_contributions: dict[str, float] = {}
        all_signals = []

        for i, pod in enumerate(PODS_ORDER):
            pod_data = self.get_pod_signals(pod.value)
            contribution = weights[i] * pod_data["aggregate_strength"]
            pod_contributions[pod.value] = round(contribution, 4)
            all_signals.extend(pod_data["signals"][:2])

        ensemble_strength = sum(pod_contributions.values())
        if ensemble_strength > 0.08:
            direction = SignalDirection.LONG
        elif ensemble_strength < -0.08:
            direction = SignalDirection.SHORT
        else:
            direction = SignalDirection.NEUTRAL

        top_signals = sorted(all_signals, key=lambda s: abs(s["strength"]), reverse=True)[:5]

        return {
            "ensemble_direction": direction.value,
            "ensemble_strength": round(float(ensemble_strength), 4),
            "regime_adjusted": True,
            "pod_contributions": pod_contributions,
            "top_signals": top_signals,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "confidence": round(self._regime_confidence * 0.85, 4),
        }

    def get_allocation(self) -> dict[str, Any]:
        weights = self._regime_weights(self._current_regime)
        strategy_weights = {pod.value: round(w, 4) for pod, w in zip(PODS_ORDER, weights)}

        now = datetime.now(timezone.utc)
        return {
            "strategy_weights": strategy_weights,
            "regime": self._current_regime,
            "regime_override_active": self._current_regime in (RegimeState.CRISIS, RegimeState.BEAR),
            "rebalance_required": self._random.random() < 0.15,
            "last_rebalance": (now - timedelta(hours=self._random.randint(6, 48))).isoformat(),
            "next_rebalance": (now + timedelta(hours=self._random.randint(1, 24))).isoformat(),
        }

    def get_portfolio_state(self) -> dict[str, Any]:
        positions = self._generate_positions()
        long_count = sum(1 for p in positions if p["direction"] == SignalDirection.LONG.value)
        short_count = sum(1 for p in positions if p["direction"] == SignalDirection.SHORT.value)
        gross = sum(abs(p["size"]) for p in positions)
        net = sum(p["size"] * (1 if p["direction"] == SignalDirection.LONG.value else -1) for p in positions)
        cash_fraction = max(0.05, 1.0 - gross)

        return {
            "nav": round(self._nav, 2),
            "cash": round(self._nav * cash_fraction, 2),
            "gross_exposure": round(gross, 4),
            "net_exposure": round(net, 4),
            "position_count": len(positions),
            "long_count": long_count,
            "short_count": short_count,
            "leverage": round(gross, 4),
            "positions": positions,
            "as_of": datetime.now(timezone.utc).isoformat(),
        }

    def _generate_positions(self) -> list[dict[str, Any]]:
        assets = [
            ("AAPL", 182.50), ("MSFT", 415.30), ("NVDA", 875.20), ("GOOGL", 172.80),
            ("AMZN", 188.60), ("META", 512.40), ("TSLA", 245.70), ("SPY", 510.20),
            ("QQQ", 440.50), ("GLD", 185.30), ("TLT", 92.40), ("BTC", 68500.0),
        ]

        pods_for_positions = self._random.sample(PODS_ORDER, k=min(6, len(PODS_ORDER)))
        positions = []

        for i, pod in enumerate(pods_for_positions[:6]):
            asset, price = self._random.choice(assets)
            direction = self._random.choice([SignalDirection.LONG, SignalDirection.SHORT])
            size = round(self._rng.uniform(0.03, 0.15), 4)
            entry_price = price * self._rng.uniform(0.92, 1.08)
            pnl_pct = (price - entry_price) / entry_price
            if direction == SignalDirection.SHORT:
                pnl_pct = -pnl_pct
            pnl = pnl_pct * size * self._nav

            positions.append({
                "asset": asset,
                "direction": direction.value,
                "size": size if direction == SignalDirection.LONG else -size,
                "entry_price": round(float(entry_price), 2),
                "current_price": round(float(price), 2),
                "unrealized_pnl": round(float(pnl), 2),
                "unrealized_pnl_pct": round(float(pnl_pct), 6),
                "pod_source": pod.value,
                "opened_at": (datetime.now(timezone.utc) - timedelta(days=self._random.randint(1, 30))).isoformat(),
                "stop_loss": round(float(entry_price * (0.92 if direction == SignalDirection.LONG else 1.08)), 2),
                "take_profit": round(float(entry_price * (1.12 if direction == SignalDirection.LONG else 0.88)), 2),
            })
        return positions

    def get_performance_metrics(self) -> dict[str, Any]:
        returns = [e["return"] for e in self._equity_curve]
        recent_returns = returns[-21:]  # MTD proxy
        ytd_returns = returns[-252:]    # YTD proxy

        from utils.metrics import (
            annualized_return, annualized_volatility, sharpe_ratio,
            sortino_ratio, calmar_ratio, max_drawdown, current_drawdown,
            win_rate, profit_factor, beta_alpha, information_ratio,
        )

        spy_returns = [r * 0.8 + self._rng.normal(0.0002, 0.003) for r in returns]
        beta, alpha = beta_alpha(returns, spy_returns)
        ir = information_ratio(returns, spy_returns)

        return {
            "total_return": round(float(np.prod(1.0 + np.array(returns)) - 1.0), 6),
            "ytd_return": round(annualized_return(ytd_returns), 6),
            "mtd_return": round(float(np.prod(1.0 + np.array(recent_returns)) - 1.0), 6),
            "annualized_return": round(self._ann_return, 6),
            "sharpe_ratio": round(self._sharpe, 4),
            "sortino_ratio": round(self._sortino, 4),
            "calmar_ratio": round(self._calmar, 4),
            "max_drawdown": round(self._mdd, 6),
            "current_drawdown": round(current_drawdown(returns), 6),
            "win_rate": round(self._win_rate, 4),
            "profit_factor": round(self._profit_factor, 4),
            "avg_win": round(float(np.mean([r for r in returns if r > 0])), 6),
            "avg_loss": round(float(np.mean([r for r in returns if r < 0])), 6),
            "best_day": round(float(np.max(returns)), 6),
            "worst_day": round(float(np.min(returns)), 6),
            "volatility_annual": round(self._ann_vol, 6),
            "beta": round(float(beta), 4),
            "alpha": round(float(alpha), 6),
            "information_ratio": round(float(ir), 4),
            "as_of": datetime.now(timezone.utc).isoformat(),
        }

    def get_risk_dashboard(self) -> dict[str, Any]:
        returns = [e["return"] for e in self._equity_curve]
        recent_30 = returns[-30:]

        from utils.metrics import annualized_volatility, max_drawdown, current_drawdown

        vol = annualized_volatility(recent_30)
        mdd = abs(max_drawdown(returns))
        curr_dd = abs(current_drawdown(returns))
        leverage = 1.35  # Simulated
        concentration = float(self._rng.uniform(0.15, 0.35))
        liquidity_score = float(self._rng.uniform(0.75, 0.95))
        tail_risk = abs(self._var_99)
        correlation_risk = float(self._rng.uniform(0.3, 0.6))

        def status(value: float, warn: float, crit: float) -> str:
            if value >= crit:
                return "critical"
            if value >= warn:
                return "warning"
            return "ok"

        metrics = [
            {
                "name": "Annualized Volatility",
                "value": round(vol, 4),
                "threshold_warning": 0.15,
                "threshold_critical": 0.25,
                "status": status(vol, 0.15, 0.25),
                "unit": "fraction",
                "description": "30-day rolling annualized portfolio volatility",
            },
            {
                "name": "Maximum Drawdown",
                "value": round(mdd, 4),
                "threshold_warning": 0.10,
                "threshold_critical": 0.20,
                "status": status(mdd, 0.10, 0.20),
                "unit": "fraction",
                "description": "Peak-to-trough drawdown since inception",
            },
            {
                "name": "Current Drawdown",
                "value": round(curr_dd, 4),
                "threshold_warning": 0.05,
                "threshold_critical": 0.12,
                "status": status(curr_dd, 0.05, 0.12),
                "unit": "fraction",
                "description": "Current drawdown from most recent peak",
            },
            {
                "name": "Gross Leverage",
                "value": round(leverage, 4),
                "threshold_warning": 1.75,
                "threshold_critical": 2.50,
                "status": status(leverage, 1.75, 2.50),
                "unit": "multiplier",
                "description": "Total gross exposure as multiple of NAV",
            },
            {
                "name": "Concentration Risk",
                "value": round(concentration, 4),
                "threshold_warning": 0.25,
                "threshold_critical": 0.40,
                "status": status(concentration, 0.25, 0.40),
                "unit": "fraction",
                "description": "Largest single pod weight in portfolio",
            },
            {
                "name": "Liquidity Score",
                "value": round(1.0 - liquidity_score, 4),
                "threshold_warning": 0.20,
                "threshold_critical": 0.35,
                "status": status(1.0 - liquidity_score, 0.20, 0.35),
                "unit": "fraction",
                "description": "Fraction of portfolio in illiquid instruments",
            },
            {
                "name": "Tail Risk (99% VaR)",
                "value": round(tail_risk, 4),
                "threshold_warning": 0.03,
                "threshold_critical": 0.06,
                "status": status(tail_risk, 0.03, 0.06),
                "unit": "fraction",
                "description": "1-day 99% VaR as fraction of NAV",
            },
            {
                "name": "Cross-Strategy Correlation",
                "value": round(correlation_risk, 4),
                "threshold_warning": 0.50,
                "threshold_critical": 0.70,
                "status": status(correlation_risk, 0.50, 0.70),
                "unit": "coefficient",
                "description": "Average pairwise strategy correlation (30-day)",
            },
        ]

        critical_count = sum(1 for m in metrics if m["status"] == "critical")
        warning_count = sum(1 for m in metrics if m["status"] == "warning")

        overall = "critical" if critical_count > 0 else ("warning" if warning_count > 0 else "ok")

        return {
            "overall_status": overall,
            "metrics": metrics,
            "portfolio_var_95": round(abs(self._var_95), 6),
            "portfolio_cvar_95": round(abs(self._cvar_95), 6),
            "portfolio_var_99": round(abs(self._var_99), 6),
            "stress_test_loss": round(float(self._rng.uniform(0.18, 0.35)), 4),
            "as_of": datetime.now(timezone.utc).isoformat(),
        }

    def get_risk_alerts(self) -> list[dict[str, Any]]:
        dashboard = self.get_risk_dashboard()
        alerts = []
        for metric in dashboard["metrics"]:
            if metric["status"] in ("warning", "critical"):
                alerts.append({
                    "alert_id": str(uuid4()),
                    "severity": metric["status"],
                    "metric": metric["name"],
                    "message": f"{metric['name']} exceeded {metric['status']} threshold",
                    "value": metric["value"],
                    "threshold": metric["threshold_critical"] if metric["status"] == "critical" else metric["threshold_warning"],
                    "triggered_at": (datetime.now(timezone.utc) - timedelta(minutes=self._random.randint(1, 120))).isoformat(),
                    "acknowledged": False,
                    "auto_action": "notify_risk_manager" if metric["status"] == "warning" else "reduce_position_size",
                })
        return alerts

    def get_correlation_matrix(self) -> dict[str, Any]:
        # Add noise to base correlation matrix
        noise = self._rng.normal(0, 0.03, CORR_MATRIX.shape)
        noisy = CORR_MATRIX + noise
        np.fill_diagonal(noisy, 1.0)
        noisy = np.clip(noisy, -1.0, 1.0)

        return {
            "pods": [p.value for p in PODS_ORDER],
            "matrix": [[round(float(noisy[i, j]), 4) for j in range(len(PODS_ORDER))] for i in range(len(PODS_ORDER))],
            "lookback_days": 30,
            "as_of": datetime.now(timezone.utc).isoformat(),
        }

    def get_kill_switches(self) -> dict[str, Any]:
        returns = [e["return"] for e in self._equity_curve]
        from utils.metrics import current_drawdown, annualized_volatility

        curr_dd = abs(current_drawdown(returns))
        daily_vol = annualized_volatility(returns[-5:]) / (252 ** 0.5) if len(returns) >= 5 else 0.01
        leverage = 1.35

        switches = [
            {
                "name": "Max Drawdown Kill Switch",
                "triggered": curr_dd > 0.15,
                "threshold": 0.15,
                "current_value": round(curr_dd, 4),
                "description": "Halts all trading if portfolio drawdown exceeds 15%",
                "auto_action": "flatten_all_positions",
                "last_checked": datetime.now(timezone.utc).isoformat(),
            },
            {
                "name": "Daily Loss Limit",
                "triggered": daily_vol > 0.025,
                "threshold": 0.025,
                "current_value": round(daily_vol, 6),
                "description": "Stops new positions if daily P&L < -2.5%",
                "auto_action": "halt_new_positions",
                "last_checked": datetime.now(timezone.utc).isoformat(),
            },
            {
                "name": "Leverage Limit",
                "triggered": leverage > 2.5,
                "threshold": 2.5,
                "current_value": round(leverage, 4),
                "description": "Reduces positions if gross leverage exceeds 2.5x",
                "auto_action": "reduce_leverage",
                "last_checked": datetime.now(timezone.utc).isoformat(),
            },
            {
                "name": "Correlation Spike Alert",
                "triggered": False,
                "threshold": 0.80,
                "current_value": round(float(self._rng.uniform(0.35, 0.65)), 4),
                "description": "Reduces risk if average strategy correlation > 0.80 (diversification breakdown)",
                "auto_action": "reduce_position_size_20pct",
                "last_checked": datetime.now(timezone.utc).isoformat(),
            },
        ]

        any_triggered = any(s["triggered"] for s in switches)
        return {
            "kill_switches": switches,
            "any_triggered": any_triggered,
            "trading_halted": any_triggered and curr_dd > 0.15,
        }

    def run_backtest(self, pods: list[str], start_date: str, end_date: str, initial_capital: float) -> dict[str, Any]:
        from utils.metrics import (
            annualized_return, sharpe_ratio, sortino_ratio,
            calmar_ratio, max_drawdown, win_rate,
        )

        # Filter equity curve to date range
        try:
            start = datetime.fromisoformat(start_date)
            end = datetime.fromisoformat(end_date)
        except ValueError:
            start = self._inception_date
            end = datetime.now(timezone.utc)

        filtered = [
            e for e in self._equity_curve
            if start.strftime("%Y-%m-%d") <= e["date"] <= end.strftime("%Y-%m-%d")
        ]

        if not filtered:
            filtered = self._equity_curve[-90:]

        # Build backtest equity curve for selected pods
        pod_indices = [PODS_ORDER.index(PodName(p)) for p in pods if PodName(p) in PODS_ORDER]
        weights = [1.0 / len(pod_indices)] * len(pod_indices)

        nav = initial_capital
        equity_curve = []
        returns = []

        for day_data in filtered:
            day_returns = [self._pod_equity[PODS_ORDER[idx].value][self._equity_curve.index(day_data) % len(self._pod_equity[PODS_ORDER[idx].value])] for idx in pod_indices]
            portfolio_return = sum(w * r for w, r in zip(weights, day_returns))
            nav *= (1.0 + portfolio_return)
            returns.append(portfolio_return)
            equity_curve.append({
                "date": day_data["date"],
                "nav": round(nav, 2),
                "drawdown": round(float(self._calc_drawdown_at(nav, initial_capital)), 6),
            })

        ann_ret = annualized_return(returns)
        sr = sharpe_ratio(returns)
        sortino = sortino_ratio(returns)
        mdd = max_drawdown(returns)
        calmar = calmar_ratio(returns)
        wr = win_rate(returns)

        regime_perf: dict[str, list[float]] = {r: [] for r in RegimeState}
        for i, day in enumerate(filtered):
            if i < len(returns):
                regime_perf[day["regime"]].append(returns[i])

        regime_breakdown = {}
        for regime, r_list in regime_perf.items():
            if r_list:
                regime_breakdown[regime] = round(annualized_return(r_list), 4)
            else:
                regime_breakdown[regime] = 0.0

        pod_contribs = {pod: round(1.0 / len(pods), 4) for pod in pods}

        return {
            "run_id": str(uuid4()),
            "pods": pods,
            "start_date": start_date,
            "end_date": end_date,
            "initial_capital": initial_capital,
            "final_capital": round(nav, 2),
            "total_return": round(float(nav / initial_capital - 1.0), 6),
            "annualized_return": round(ann_ret, 6),
            "sharpe_ratio": round(sr, 4),
            "sortino_ratio": round(sortino, 4),
            "max_drawdown": round(mdd, 6),
            "calmar_ratio": round(calmar, 4),
            "win_rate": round(wr, 4),
            "total_trades": self._random.randint(200, 1500),
            "equity_curve": equity_curve[::5],  # Thin for bandwidth
            "regime_breakdown": regime_breakdown,
            "pod_contributions": pod_contribs,
            "run_duration_ms": round(float(self._rng.uniform(120, 850)), 1),
        }

    def get_equity_curve(self) -> list[dict[str, Any]]:
        return self._equity_curve


# Module-level singleton
_simulator: DataSimulator | None = None


def get_simulator() -> DataSimulator:
    global _simulator
    if _simulator is None:
        _simulator = DataSimulator()
    return _simulator


def init_simulator(seed: int = 42) -> DataSimulator:
    global _simulator
    _simulator = DataSimulator(seed=seed)
    return _simulator
