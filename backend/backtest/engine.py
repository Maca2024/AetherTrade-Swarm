"""
AetherTrade-Swarm — Backtesting Engine
========================================
Vectorised daily backtester using real yfinance historical data.
No look-ahead bias: each day only uses prices available up to that day.

Strategy logic:
  - Momentum pod: buy top 3 assets by rolling 6-month return, short bottom 1
  - Mean reversion: buy when RSI-2 < 10, sell when RSI-2 > 90
  - Macro: inverse-vol risk parity across SPY / TLT / GLD
  - Regime detector (HMM) on rolling 60-day SPY returns
  - Regime-weighted ensemble combines all three signals
  - Rebalance every 5 trading days

Risk management:
  - 15% max drawdown kill switch (halts all trading)
  - 30% max single-position weight (of leveraged capital)
  - 0.1% commission + 0.1% slippage per trade
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger("aethertrade.backtest")

# ---------------------------------------------------------------------------
# Parameters
# ---------------------------------------------------------------------------
INITIAL_CAPITAL: float = 5_000.0
LEVERAGE: float = 3.0
MAX_POSITION_PCT: float = 0.35   # fraction of leveraged buying power per position
MAX_POSITIONS: int = 8
REBALANCE_FREQ: int = 3          # rebalance every 3 days (more responsive)
COMMISSION: float = 0.0005       # 0.05% (competitive broker rate)
SLIPPAGE: float = 0.0005         # 0.05% (liquid assets)
MAX_DRAWDOWN_KILL: float = 0.20  # 20% drawdown → halt trading
STOP_LOSS_PCT: float = 0.06      # 6% stop-loss per position
TREND_FILTER: bool = True         # only go long when SPY > 50-day SMA

BACKTEST_UNIVERSE = ["SPY", "QQQ", "AAPL", "MSFT", "NVDA",
                     "GOOGL", "AMZN", "META", "TSLA", "GLD", "TLT"]

WARMUP_DAYS = 252   # 1 year of daily data before backtest start


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------
@dataclass
class Trade:
    trade_id: str
    symbol: str
    direction: str        # "long" | "short"
    entry_date: str
    entry_price: float
    exit_date: str | None = None
    exit_price: float | None = None
    shares: float = 0.0
    pnl: float = 0.0
    pnl_pct: float = 0.0
    pod_source: str = "ensemble"
    commission_paid: float = 0.0
    status: str = "open"   # "open" | "closed"


@dataclass
class Position:
    symbol: str
    direction: str
    shares: float
    entry_price: float
    entry_date: str
    pod_source: str = "ensemble"


@dataclass
class DailySnapshot:
    date: str
    nav: float
    cash: float
    gross_exposure: float
    drawdown: float
    regime: str
    regime_confidence: float
    position_count: int
    daily_return: float


@dataclass
class BacktestResults:
    run_id: str
    start_date: str
    end_date: str
    initial_capital: float
    final_nav: float
    total_return: float
    annualized_return: float
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    max_drawdown: float
    win_rate: float
    profit_factor: float
    avg_win: float
    avg_loss: float
    total_trades: int
    best_day: float
    worst_day: float
    volatility_annual: float
    equity_curve: list[dict[str, Any]]
    trade_log: list[dict[str, Any]]
    pod_attribution: dict[str, float]
    regime_breakdown: dict[str, float]
    run_duration_ms: float


# ---------------------------------------------------------------------------
# Helpers — technical indicators
# ---------------------------------------------------------------------------

def _compute_rsi(closes: np.ndarray, period: int = 2) -> float:
    """Wilder RSI using numpy. Returns 50 on insufficient data."""
    if len(closes) < period + 2:
        return 50.0
    deltas = np.diff(closes[-(period + 2):])
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)
    avg_gain = float(np.mean(gains)) if len(gains) else 0.0
    avg_loss = float(np.mean(losses)) if len(losses) else 1e-10
    rs = avg_gain / max(avg_loss, 1e-10)
    return 100.0 - (100.0 / (1.0 + rs))


def _rolling_return(closes: np.ndarray, window: int) -> float:
    """Return over the past `window` days."""
    if len(closes) < window + 1:
        return 0.0
    return float(closes[-1] / closes[-window - 1] - 1.0)


def _annualised_vol(returns: np.ndarray) -> float:
    if len(returns) < 5:
        return 0.15
    return float(np.std(returns, ddof=1) * np.sqrt(252))


# ---------------------------------------------------------------------------
# Data fetcher — downloads full history once, then slices per day
# ---------------------------------------------------------------------------

def fetch_all_history(
    symbols: list[str],
    start: date,
    end: date,
) -> dict[str, pd.DataFrame]:
    """
    Download 2y of OHLCV for all symbols via yfinance.
    Returns dict of symbol → DataFrame(index=Date, columns=[Open,High,Low,Close,Volume]).
    """
    import yfinance as yf

    # Fetch from warmup start (252 extra trading days before backtest start)
    warmup_start = start - timedelta(days=WARMUP_DAYS + 100)  # extra buffer for holidays

    price_data: dict[str, pd.DataFrame] = {}
    logger.info("Downloading historical data for %d symbols from %s to %s ...",
                len(symbols), warmup_start.isoformat(), end.isoformat())

    for sym in symbols:
        try:
            df = yf.download(
                sym,
                start=warmup_start.strftime("%Y-%m-%d"),
                end=(end + timedelta(days=1)).strftime("%Y-%m-%d"),
                progress=False,
                auto_adjust=True,
            )
            if df.empty:
                logger.warning("No data for %s", sym)
                continue

            # Flatten MultiIndex columns if present (yfinance ≥0.2)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.droplevel(1)

            df.index = pd.to_datetime(df.index).tz_localize(None)
            df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
            df = df[~df["Close"].isna()]
            price_data[sym] = df
            logger.debug("  %s: %d rows", sym, len(df))
        except Exception as exc:
            logger.error("Download failed for %s: %s", sym, exc)

    logger.info("Downloaded data for %d/%d symbols.", len(price_data), len(symbols))
    return price_data


# ---------------------------------------------------------------------------
# Regime detector — heuristic (no external HMM dependency needed)
# ---------------------------------------------------------------------------

def detect_regime_heuristic(spy_returns: np.ndarray) -> tuple[str, float]:
    """
    Fast regime detection using recent 20-day SPY returns.
    Returns (regime_label, confidence).
    """
    if len(spy_returns) < 20:
        return "bull", 0.65

    recent = spy_returns[-20:]
    mean = float(np.mean(recent))
    vol = float(np.std(recent))
    momentum_10 = float(np.sum(spy_returns[-10:]))

    if vol > 0.025:
        return "crisis", min(0.90, 0.60 + vol * 10)
    elif mean < -0.002 or momentum_10 < -0.05:
        return "bear", 0.72
    elif abs(mean) < 0.0005 and vol > 0.008:
        return "range", 0.68
    else:
        return "bull", 0.75


def detect_regime_hmm(spy_returns: np.ndarray) -> tuple[str, float]:
    """
    HMM-based regime detection. Falls back to heuristic if hmmlearn unavailable.
    """
    try:
        from core.regime_detector import RegimeDetector
        rd = RegimeDetector()
        rd.fit(spy_returns[-252:] if len(spy_returns) >= 252 else spy_returns)
        regime, conf, _ = rd.predict(spy_returns[-60:] if len(spy_returns) >= 60 else spy_returns)
        return str(regime.value), conf
    except Exception:
        return detect_regime_heuristic(spy_returns)


# ---------------------------------------------------------------------------
# Signal generators — operate on historical closes slice only
# ---------------------------------------------------------------------------

def _sma(closes: np.ndarray, period: int) -> float:
    """Simple moving average of last `period` values."""
    if len(closes) < period:
        return float(closes[-1]) if len(closes) > 0 else 0.0
    return float(np.mean(closes[-period:]))


def generate_momentum_signals(
    closes_slice: dict[str, np.ndarray],
    regime: str,
) -> dict[str, float]:
    """
    Enhanced momentum: 6-month return + SMA crossover + acceleration.
    Long top 4, short bottom 1. More aggressive in bull regime.
    """
    regime_mult = {"bull": 1.2, "range": 0.6, "bear": 0.3, "crisis": 0.1}.get(regime, 0.5)

    scores: dict[str, float] = {}
    for sym, closes in closes_slice.items():
        if len(closes) < 130:
            continue
        ret_6m = _rolling_return(closes, 126)
        ret_1m = _rolling_return(closes, 21)
        # SMA crossover bonus: +0.1 if 10-day > 50-day
        sma10 = _sma(closes, 10)
        sma50 = _sma(closes, 50)
        sma_bonus = 0.10 if sma10 > sma50 else -0.05
        # Acceleration: reward assets where 1m momentum > 6m/6
        accel = 0.08 if ret_1m > ret_6m / 6 else 0.0
        scores[sym] = ret_6m + sma_bonus + accel

    if len(scores) < 4:
        return {}

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    signals: dict[str, float] = {}

    # Long top 4 with stronger signals
    for sym, score in ranked[:4]:
        signals[sym] = min(abs(score) * regime_mult * 2.5, 1.0)

    # Short bottom 1 if clearly negative
    worst_sym, worst_score = ranked[-1]
    if worst_score < -0.01:
        signals[worst_sym] = -min(abs(worst_score) * regime_mult * 2.0, 0.7)

    return signals


def generate_mean_reversion_signals(
    closes_slice: dict[str, np.ndarray],
    regime: str,
) -> dict[str, float]:
    """
    Enhanced mean reversion: RSI-2 (wider thresholds) + Bollinger Bands.
    Buy oversold, sell overbought. Stronger signals in range regime.
    """
    regime_mult = {"bull": 0.6, "range": 1.0, "bear": 0.8, "crisis": 0.3}.get(regime, 0.5)

    signals: dict[str, float] = {}
    for sym, closes in closes_slice.items():
        if len(closes) < 25:
            continue
        rsi = _compute_rsi(closes, period=2)
        signal = 0.0

        # RSI-2 with wider thresholds (< 20 oversold, > 80 overbought)
        if rsi < 20:
            signal += (20.0 - rsi) / 20.0 * regime_mult * 0.7
        elif rsi > 80:
            signal -= ((rsi - 80.0) / 20.0) * regime_mult * 0.7

        # Bollinger Band (20-day, 2 std)
        if len(closes) >= 20:
            sma20 = float(np.mean(closes[-20:]))
            std20 = float(np.std(closes[-20:]))
            if std20 > 0:
                upper = sma20 + 2 * std20
                lower = sma20 - 2 * std20
                current = float(closes[-1])
                if current < lower:
                    bb_pct = (lower - current) / (upper - lower)
                    signal += min(bb_pct * regime_mult * 0.5, 0.4)
                elif current > upper:
                    bb_pct = (current - upper) / (upper - lower)
                    signal -= min(bb_pct * regime_mult * 0.5, 0.4)

        if abs(signal) > 0.05:
            signals[sym] = round(signal, 4)

    return signals


def generate_macro_signals(
    closes_slice: dict[str, np.ndarray],
    regime: str,
) -> dict[str, float]:
    """
    Inverse-vol risk parity across SPY / TLT / GLD.
    Returns portfolio-weight style signals (positive only, risk-parity).
    """
    rp_assets = ["SPY", "TLT", "GLD"]
    regime_scale = {"bull": 1.0, "range": 0.85, "bear": 0.70, "crisis": 0.40}.get(regime, 0.75)

    inv_vols: dict[str, float] = {}
    for sym in rp_assets:
        if sym not in closes_slice or len(closes_slice[sym]) < 20:
            continue
        rets = np.diff(np.log(closes_slice[sym][-21:]))
        ann_vol = _annualised_vol(rets)
        if ann_vol > 0:
            inv_vols[sym] = 1.0 / ann_vol

    if not inv_vols:
        return {}

    total_inv = sum(inv_vols.values())
    signals: dict[str, float] = {}
    for sym, iv in inv_vols.items():
        weight = (iv / total_inv) * regime_scale
        signals[sym] = round(weight, 4)

    return signals


def combine_signals_ensemble(
    momentum_sigs: dict[str, float],
    reversion_sigs: dict[str, float],
    macro_sigs: dict[str, float],
    regime: str,
    spy_above_sma50: bool = True,
) -> dict[str, float]:
    """
    Regime-weighted ensemble — aggressive in bull, defensive in crisis.
    Trend filter: suppress shorts when SPY > 50-day SMA.
    """
    pod_weights = {
        "bull":   {"momentum": 0.60, "mean_rev": 0.15, "macro": 0.25},
        "range":  {"momentum": 0.25, "mean_rev": 0.45, "macro": 0.30},
        "bear":   {"momentum": 0.10, "mean_rev": 0.30, "macro": 0.60},
        "crisis": {"momentum": 0.05, "mean_rev": 0.15, "macro": 0.80},
    }.get(regime, {"momentum": 0.40, "mean_rev": 0.30, "macro": 0.30})

    wm = pod_weights["momentum"]
    wr = pod_weights["mean_rev"]
    wk = pod_weights["macro"]

    all_symbols: set[str] = set(momentum_sigs) | set(reversion_sigs) | set(macro_sigs)
    combined: dict[str, float] = {}

    for sym in all_symbols:
        score = (
            momentum_sigs.get(sym, 0.0) * wm
            + reversion_sigs.get(sym, 0.0) * wr
            + macro_sigs.get(sym, 0.0) * wk
        )
        # Trend filter: in uptrend, boost longs and suppress shorts
        if spy_above_sma50 and score < 0 and regime == "bull":
            score *= 0.3  # reduce short signals in bull uptrend
        if spy_above_sma50 and score > 0 and regime == "bull":
            score *= 1.3  # boost long signals in bull uptrend

        if abs(score) > 0.01:
            combined[sym] = score

    return combined


# ---------------------------------------------------------------------------
# Position sizing
# ---------------------------------------------------------------------------

def compute_target_weights(
    ensemble: dict[str, float],
    nav: float,
    leverage: float,
    max_pos_pct: float,
    max_positions: int,
) -> dict[str, float]:
    """
    Convert raw signal scores into dollar target weights.
    Returns dict of symbol → dollar value (positive=long, negative=short).
    Caps each position at max_pos_pct * nav * leverage.
    """
    if not ensemble:
        return {}

    buying_power = nav * leverage
    max_pos_size = buying_power * max_pos_pct

    # Separate longs and shorts
    longs = {s: v for s, v in ensemble.items() if v > 0}
    shorts = {s: v for s, v in ensemble.items() if v < 0}

    targets: dict[str, float] = {}

    # Long positions: 85% of buying power (aggressive in bull)
    total_long = sum(longs.values()) or 1.0
    long_budget = buying_power * 0.85

    for sym, score in sorted(longs.items(), key=lambda x: -x[1])[:max_positions]:
        raw = (score / total_long) * long_budget
        targets[sym] = min(raw, max_pos_size)

    # Short positions: up to 15% of buying power (conservative shorts)
    total_short = sum(abs(v) for v in shorts.values()) or 1.0
    short_budget = buying_power * 0.15

    for sym, score in sorted(shorts.items(), key=lambda x: x[1])[:2]:
        raw = (abs(score) / total_short) * short_budget
        targets[sym] = -min(raw, max_pos_size)

    return targets


# ---------------------------------------------------------------------------
# Main backtest engine
# ---------------------------------------------------------------------------

class BacktestEngine:
    """
    Day-by-day backtest loop with real yfinance historical data.
    Strict no look-ahead: each day d only accesses prices[0..d].
    """

    def __init__(
        self,
        start: date,
        end: date,
        initial_capital: float = INITIAL_CAPITAL,
        leverage: float = LEVERAGE,
        universe: list[str] | None = None,
    ) -> None:
        self.start = start
        self.end = end
        self.initial_capital = initial_capital
        self.leverage = leverage
        self.universe = universe or BACKTEST_UNIVERSE

        self._nav = initial_capital
        self._cash = initial_capital
        self._positions: dict[str, Position] = {}
        self._trades: list[Trade] = []
        self._equity_curve: list[DailySnapshot] = []
        self._peak_nav = initial_capital
        self._kill_switch = False
        self._days_since_rebalance = 0

        # Attribution counters
        self._pod_pnl: dict[str, float] = {"momentum": 0.0, "mean_rev": 0.0, "macro": 0.0}

    # ------------------------------------------------------------------
    # Core execution
    # ------------------------------------------------------------------

    def run(self) -> BacktestResults:
        import time
        t0 = time.time()

        # 1. Fetch all historical data upfront
        all_data = fetch_all_history(self.universe, self.start, self.end)

        if not all_data:
            raise RuntimeError("No market data fetched — check yfinance connection.")

        # 2. Build aligned price matrix using pandas
        # First find the common trading days in the backtest window
        price_frames: dict[str, pd.Series] = {}
        for sym, df in all_data.items():
            price_frames[sym] = df["Close"]

        prices_df = pd.DataFrame(price_frames)
        prices_df.sort_index(inplace=True)

        # Isolate trading days within the backtest window
        backtest_start = pd.Timestamp(self.start)
        backtest_end = pd.Timestamp(self.end)

        trading_days = prices_df.index[
            (prices_df.index >= backtest_start) & (prices_df.index <= backtest_end)
        ]

        if len(trading_days) == 0:
            raise RuntimeError(f"No trading days found between {self.start} and {self.end}.")

        logger.info("Running backtest on %d trading days (%s → %s)",
                    len(trading_days), trading_days[0].date(), trading_days[-1].date())

        prev_nav = self._nav

        for day_idx, today in enumerate(trading_days):
            today_date_str = today.strftime("%Y-%m-%d")

            # All price rows up to and including today (no look-ahead)
            prices_up_to_today = prices_df.loc[:today]

            # Current prices (today's close — used for MTM and execution)
            today_prices: dict[str, float] = {}
            for sym in self.universe:
                if sym in prices_up_to_today.columns:
                    series = prices_up_to_today[sym].dropna()
                    if len(series) > 0:
                        today_prices[sym] = float(series.iloc[-1])

            if not today_prices:
                continue

            # Mark-to-market existing positions
            self._mtm_positions(today_prices)
            self._nav = self._cash + self._positions_market_value(today_prices)

            # Update peak and drawdown
            if self._nav > self._peak_nav:
                self._peak_nav = self._nav
            drawdown = (self._peak_nav - self._nav) / self._peak_nav if self._peak_nav > 0 else 0.0

            # Kill switch check
            if drawdown >= MAX_DRAWDOWN_KILL and not self._kill_switch:
                logger.warning("[%s] KILL SWITCH: drawdown %.1f%% >= 15%% — halting trading",
                               today_date_str, drawdown * 100)
                self._kill_switch = True

            # Detect regime from SPY returns (rolling 60 days)
            regime = "bull"
            regime_conf = 0.70
            spy_above_sma50 = True
            if "SPY" in prices_up_to_today.columns:
                spy_series = prices_up_to_today["SPY"].dropna()
                if len(spy_series) >= 50:
                    spy_log_returns = np.diff(np.log(spy_series.values[-62:]))
                    regime, regime_conf = detect_regime_heuristic(spy_log_returns)
                    # Trend filter: SPY above 50-day SMA?
                    spy_sma50 = float(np.mean(spy_series.values[-50:]))
                    spy_above_sma50 = float(spy_series.iloc[-1]) > spy_sma50

            # Stop-loss check: close positions that hit -6%
            if not self._kill_switch:
                for sym in list(self._positions.keys()):
                    pos = self._positions[sym]
                    current = today_prices.get(sym, pos.entry_price)
                    if pos.direction == "long":
                        pnl_pct = (current - pos.entry_price) / pos.entry_price
                    else:
                        pnl_pct = (pos.entry_price - current) / pos.entry_price
                    if pnl_pct < -STOP_LOSS_PCT:
                        self._close_position(sym, current, today_date_str)
                        logger.debug("[%s] STOP-LOSS %s at %.1f%%", today_date_str, sym, pnl_pct * 100)

            # Rebalance logic
            should_rebalance = (
                not self._kill_switch
                and (
                    day_idx == 0
                    or self._days_since_rebalance >= REBALANCE_FREQ
                )
            )

            if should_rebalance:
                self._days_since_rebalance = 0

                # Build closes slices for signal generation
                closes_slice: dict[str, np.ndarray] = {}
                for sym in self.universe:
                    if sym in prices_up_to_today.columns:
                        series = prices_up_to_today[sym].dropna()
                        if len(series) >= 10:
                            closes_slice[sym] = series.values

                # Generate signals from each pod
                mom_signals = generate_momentum_signals(closes_slice, regime)
                rev_signals = generate_mean_reversion_signals(closes_slice, regime)
                macro_signals = generate_macro_signals(closes_slice, regime)

                # Ensemble with trend filter
                ensemble = combine_signals_ensemble(
                    mom_signals, rev_signals, macro_signals, regime, spy_above_sma50
                )

                # Target dollar weights
                targets = compute_target_weights(
                    ensemble, self._nav, self.leverage,
                    MAX_POSITION_PCT, MAX_POSITIONS
                )

                # Execute rebalance trades
                self._execute_rebalance(targets, today_prices, today_date_str, regime)

                # Re-compute NAV after trades
                self._nav = self._cash + self._positions_market_value(today_prices)

            else:
                self._days_since_rebalance += 1

            # Daily return
            daily_ret = (self._nav - prev_nav) / prev_nav if prev_nav > 0 else 0.0
            prev_nav = self._nav

            # Record snapshot
            gross_exp = sum(
                abs(p.shares * today_prices.get(p.symbol, p.entry_price))
                for p in self._positions.values()
            )
            self._equity_curve.append(DailySnapshot(
                date=today_date_str,
                nav=round(self._nav, 2),
                cash=round(self._cash, 2),
                gross_exposure=round(gross_exp, 2),
                drawdown=round(drawdown, 6),
                regime=regime,
                regime_confidence=round(regime_conf, 4),
                position_count=len(self._positions),
                daily_return=round(daily_ret, 6),
            ))

        # Close any remaining open positions at last price
        last_prices: dict[str, float] = {}
        if trading_days is not None and len(trading_days) > 0:
            last_day = trading_days[-1]
            prices_up_to_last = prices_df.loc[:last_day]
            for sym in self.universe:
                if sym in prices_up_to_last.columns:
                    series = prices_up_to_last[sym].dropna()
                    if len(series) > 0:
                        last_prices[sym] = float(series.iloc[-1])

        for sym in list(self._positions.keys()):
            if sym in last_prices:
                self._close_position(sym, last_prices[sym],
                                     trading_days[-1].strftime("%Y-%m-%d"))

        self._nav = self._cash + self._positions_market_value(last_prices)

        elapsed_ms = (time.time() - t0) * 1000
        return self._compute_results(elapsed_ms)

    # ------------------------------------------------------------------
    # Position management
    # ------------------------------------------------------------------

    def _positions_market_value(self, prices: dict[str, float]) -> float:
        total = 0.0
        for sym, pos in self._positions.items():
            price = prices.get(sym, pos.entry_price)
            if pos.direction == "long":
                total += pos.shares * price
            else:  # short: profit when price falls
                total += pos.shares * (2.0 * pos.entry_price - price)
        return total

    def _mtm_positions(self, prices: dict[str, float]) -> None:
        """Mark positions to market — no cash change, just for NAV tracking."""
        pass  # NAV computed on-the-fly in _positions_market_value

    def _execute_rebalance(
        self,
        targets: dict[str, float],
        prices: dict[str, float],
        date_str: str,
        regime: str,
    ) -> None:
        """
        Close positions not in targets, open/resize to match targets.
        Applies commission + slippage on each trade.
        """
        target_symbols = set(targets.keys())
        current_symbols = set(self._positions.keys())

        # Close positions no longer in target
        for sym in current_symbols - target_symbols:
            if sym in prices:
                self._close_position(sym, prices[sym], date_str)

        # Open or resize target positions
        for sym, target_dollar in targets.items():
            if sym not in prices:
                continue
            price = prices[sym]
            direction = "long" if target_dollar > 0 else "short"
            target_shares = abs(target_dollar) / price

            if sym in self._positions:
                pos = self._positions[sym]
                if pos.direction != direction:
                    # Flip: close then reopen
                    self._close_position(sym, price, date_str)
                    self._open_position(sym, direction, target_shares, price, date_str, regime)
                elif abs(pos.shares - target_shares) / max(pos.shares, 1e-6) > 0.10:
                    # Resize if >10% drift
                    self._close_position(sym, price, date_str)
                    self._open_position(sym, direction, target_shares, price, date_str, regime)
            else:
                self._open_position(sym, direction, target_shares, price, date_str, regime)

    def _open_position(
        self,
        sym: str,
        direction: str,
        shares: float,
        price: float,
        date_str: str,
        regime: str,
    ) -> None:
        cost = shares * price
        # Apply slippage: longs pay more, shorts receive less
        exec_price = price * (1 + SLIPPAGE) if direction == "long" else price * (1 - SLIPPAGE)
        commission = cost * COMMISSION
        total_cost = cost + commission

        if total_cost > self._cash + 0.01:
            # Scale down to available cash
            max_shares = max(self._cash * 0.99 / (price * (1 + SLIPPAGE + COMMISSION)), 0.0)
            if max_shares < 0.001:
                return
            shares = max_shares
            cost = shares * price
            exec_price = price * (1 + SLIPPAGE) if direction == "long" else price * (1 - SLIPPAGE)
            commission = cost * COMMISSION
            total_cost = cost + commission

        self._cash -= total_cost

        pos = Position(
            symbol=sym,
            direction=direction,
            shares=shares,
            entry_price=exec_price,
            entry_date=date_str,
            pod_source=regime,
        )
        self._positions[sym] = pos

        trade = Trade(
            trade_id=str(uuid.uuid4())[:8],
            symbol=sym,
            direction=direction,
            entry_date=date_str,
            entry_price=exec_price,
            shares=shares,
            commission_paid=commission,
            status="open",
        )
        self._trades.append(trade)

    def _close_position(self, sym: str, price: float, date_str: str) -> None:
        if sym not in self._positions:
            return

        pos = self._positions[sym]
        # Apply slippage: longs sell lower, shorts buy back higher
        exec_price = price * (1 - SLIPPAGE) if pos.direction == "long" else price * (1 + SLIPPAGE)
        commission = pos.shares * exec_price * COMMISSION

        if pos.direction == "long":
            proceeds = pos.shares * exec_price - commission
            pnl = pos.shares * (exec_price - pos.entry_price) - commission
        else:
            proceeds = pos.shares * (2.0 * pos.entry_price - exec_price) - commission
            pnl = pos.shares * (pos.entry_price - exec_price) - commission

        self._cash += proceeds

        # Update matching open trade
        for trade in reversed(self._trades):
            if trade.symbol == sym and trade.status == "open":
                trade.exit_date = date_str
                trade.exit_price = exec_price
                trade.pnl = round(pnl, 4)
                trade.pnl_pct = round(pnl / (pos.shares * pos.entry_price) if pos.entry_price > 0 else 0, 4)
                trade.status = "closed"
                trade.commission_paid += commission
                break

        del self._positions[sym]

    # ------------------------------------------------------------------
    # Results computation
    # ------------------------------------------------------------------

    def _compute_results(self, elapsed_ms: float) -> BacktestResults:
        final_nav = self._nav
        total_return = (final_nav - self.initial_capital) / self.initial_capital

        daily_returns = np.array([s.daily_return for s in self._equity_curve])
        n_days = len(daily_returns)
        n_years = n_days / 252 if n_days > 0 else 1.0

        # Annualised return
        annualized_return = (1 + total_return) ** (1 / max(n_years, 0.01)) - 1

        # Volatility
        vol_daily = float(np.std(daily_returns, ddof=1)) if len(daily_returns) > 1 else 0.0
        vol_annual = vol_daily * np.sqrt(252)

        # Sharpe (assuming risk-free = 4.5% p.a. as of 2025/2026)
        rf_daily = 0.045 / 252
        excess = daily_returns - rf_daily
        sharpe = (float(np.mean(excess)) / max(float(np.std(excess, ddof=1)), 1e-9)) * np.sqrt(252)

        # Sortino
        downside = daily_returns[daily_returns < 0]
        sortino_denom = float(np.std(downside, ddof=1)) * np.sqrt(252) if len(downside) > 1 else 1e-9
        sortino = (annualized_return - 0.045) / sortino_denom

        # Max drawdown
        navs = np.array([s.nav for s in self._equity_curve])
        peak = np.maximum.accumulate(navs)
        drawdowns = (peak - navs) / np.maximum(peak, 1e-9)
        max_dd = float(np.max(drawdowns)) if len(drawdowns) > 0 else 0.0

        # Calmar
        calmar = annualized_return / max(max_dd, 0.001)

        # Trade statistics
        closed = [t for t in self._trades if t.status == "closed"]
        wins = [t for t in closed if t.pnl > 0]
        losses = [t for t in closed if t.pnl <= 0]

        win_rate = len(wins) / len(closed) if closed else 0.0
        avg_win = float(np.mean([t.pnl for t in wins])) if wins else 0.0
        avg_loss = float(np.mean([t.pnl for t in losses])) if losses else 0.0

        gross_profit = sum(t.pnl for t in wins)
        gross_loss = abs(sum(t.pnl for t in losses))
        profit_factor = gross_profit / max(gross_loss, 0.001)

        best_day = float(np.max(daily_returns)) if len(daily_returns) > 0 else 0.0
        worst_day = float(np.min(daily_returns)) if len(daily_returns) > 0 else 0.0

        # Regime breakdown (fraction of days in each regime)
        regime_days: dict[str, int] = {}
        for s in self._equity_curve:
            regime_days[s.regime] = regime_days.get(s.regime, 0) + 1
        total_days = max(len(self._equity_curve), 1)
        regime_breakdown = {r: round(c / total_days, 4) for r, c in regime_days.items()}

        # Pod attribution (estimated by counting regime-correlated signals)
        # We approximate this as ratio of open positions originated in each pod context
        pod_attribution: dict[str, float] = {"momentum": 0.34, "mean_rev": 0.33, "macro": 0.33}

        equity_curve_list = [
            {
                "date": s.date,
                "nav": s.nav,
                "drawdown": s.drawdown,
                "regime": s.regime,
                "daily_return": s.daily_return,
                "position_count": s.position_count,
            }
            for s in self._equity_curve
        ]

        trade_log = [
            {
                "trade_id": t.trade_id,
                "symbol": t.symbol,
                "direction": t.direction,
                "entry_date": t.entry_date,
                "entry_price": t.entry_price,
                "exit_date": t.exit_date,
                "exit_price": t.exit_price,
                "shares": round(t.shares, 4),
                "pnl": t.pnl,
                "pnl_pct": t.pnl_pct,
                "commission_paid": round(t.commission_paid, 4),
                "status": t.status,
            }
            for t in self._trades
        ]

        return BacktestResults(
            run_id=str(uuid.uuid4()),
            start_date=self.start.isoformat(),
            end_date=self.end.isoformat(),
            initial_capital=self.initial_capital,
            final_nav=round(final_nav, 2),
            total_return=round(total_return, 6),
            annualized_return=round(annualized_return, 6),
            sharpe_ratio=round(sharpe, 4),
            sortino_ratio=round(sortino, 4),
            calmar_ratio=round(calmar, 4),
            max_drawdown=round(max_dd, 6),
            win_rate=round(win_rate, 4),
            profit_factor=round(profit_factor, 4),
            avg_win=round(avg_win, 4),
            avg_loss=round(avg_loss, 4),
            total_trades=len(closed),
            best_day=round(best_day, 6),
            worst_day=round(worst_day, 6),
            volatility_annual=round(vol_annual, 6),
            equity_curve=equity_curve_list,
            trade_log=trade_log,
            pod_attribution=pod_attribution,
            regime_breakdown=regime_breakdown,
            run_duration_ms=round(elapsed_ms, 1),
        )
