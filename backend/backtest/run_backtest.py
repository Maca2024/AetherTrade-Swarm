"""
AetherTrade-Swarm — Backtest Runner
=====================================
Standalone script to run a 1-year backtest and print results.

Usage:
    cd backend
    python -m backtest.run_backtest

Parameters:
    Period:   April 8 2025 → April 7 2026 (exactly 1 year)
    Capital:  $5,000
    Leverage: 3x
    Universe: SPY, QQQ, AAPL, MSFT, NVDA, GOOGL, AMZN, META, TSLA, GLD, TLT
"""
from __future__ import annotations

import json
import logging
import os
import sys
from datetime import date
from pathlib import Path

# Make sure backend/ is on sys.path when run as a module
_backend_dir = Path(__file__).resolve().parent.parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

from backtest.engine import BacktestEngine, BacktestResults

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("aethertrade.run_backtest")

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
BACKTEST_START = date(2025, 4, 8)
BACKTEST_END   = date(2026, 4, 7)
INITIAL_CAPITAL = 5_000.0
LEVERAGE        = 3.0
UNIVERSE        = ["SPY", "QQQ", "AAPL", "MSFT", "NVDA",
                   "GOOGL", "AMZN", "META", "TSLA", "GLD", "TLT"]

RESULTS_DIR = Path(__file__).parent / "results"
RESULTS_FILE = RESULTS_DIR / "backtest_results.json"


# ---------------------------------------------------------------------------
# Report printer
# ---------------------------------------------------------------------------

def _fmt_pct(v: float) -> str:
    return f"{v * 100:+.2f}%"


def _fmt_dollar(v: float) -> str:
    sign = "+" if v >= 0 else ""
    return f"${sign}{v:,.2f}"


def print_report(r: BacktestResults) -> None:
    sep = "=" * 60
    thin = "-" * 60

    print()
    print(sep)
    print("  AETHERTRADE-SWARM — BACKTEST RESULTS")
    print(sep)
    print(f"  Run ID         : {r.run_id}")
    print(f"  Period         : {r.start_date}  to  {r.end_date}")
    print(f"  Universe       : {len(UNIVERSE)} assets")
    print(f"  Initial Capital: ${r.initial_capital:,.2f}")
    print(f"  Leverage       : 3x")
    print(f"  Run time       : {r.run_duration_ms:,.0f} ms")
    print(thin)

    print()
    print("  PERFORMANCE SUMMARY")
    print(thin)
    pnl = r.final_nav - r.initial_capital
    print(f"  Final NAV         : ${r.final_nav:,.2f}  ({_fmt_dollar(pnl)})")
    print(f"  Total Return      : {_fmt_pct(r.total_return)}")
    print(f"  Annualised Return : {_fmt_pct(r.annualized_return)}")
    print(f"  Annual Volatility : {_fmt_pct(r.volatility_annual)}")
    print(f"  Sharpe Ratio      : {r.sharpe_ratio:.4f}")
    print(f"  Sortino Ratio     : {r.sortino_ratio:.4f}")
    print(f"  Calmar Ratio      : {r.calmar_ratio:.4f}")
    print(f"  Max Drawdown      : {_fmt_pct(r.max_drawdown)}")
    print()

    print("  TRADE STATISTICS")
    print(thin)
    print(f"  Total Trades  : {r.total_trades}")
    print(f"  Win Rate      : {_fmt_pct(r.win_rate)}")
    print(f"  Profit Factor : {r.profit_factor:.4f}")
    print(f"  Avg Win       : {_fmt_dollar(r.avg_win)}")
    print(f"  Avg Loss      : {_fmt_dollar(r.avg_loss)}")
    print(f"  Best Day      : {_fmt_pct(r.best_day)}")
    print(f"  Worst Day     : {_fmt_pct(r.worst_day)}")
    print()

    print("  REGIME BREAKDOWN (% of days)")
    print(thin)
    for regime, frac in sorted(r.regime_breakdown.items(), key=lambda x: -x[1]):
        bar = "#" * int(frac * 40)
        print(f"  {regime.upper():<8} {_fmt_pct(frac):>8}  {bar}")
    print()

    print("  POD ATTRIBUTION (estimated)")
    print(thin)
    for pod, weight in sorted(r.pod_attribution.items(), key=lambda x: -x[1]):
        print(f"  {pod:<15}: {_fmt_pct(weight)}")
    print()

    print("  EQUITY CURVE (monthly snapshots)")
    print(thin)
    curve = r.equity_curve
    if curve:
        # Print every ~21st point (approximately monthly)
        step = max(len(curve) // 14, 1)
        print(f"  {'Date':<12}  {'NAV':>10}  {'Drawdown':>9}  {'Regime':<8}  Pos")
        for snap in curve[::step]:
            print(f"  {snap['date']:<12}  ${snap['nav']:>9,.2f}  "
                  f"{snap['drawdown']*100:>7.2f}%  {snap['regime']:<8}  {snap['position_count']}")
        # Always print last
        last = curve[-1]
        if curve[-1] != curve[::step][-1]:
            print(f"  {last['date']:<12}  ${last['nav']:>9,.2f}  "
                  f"{last['drawdown']*100:>7.2f}%  {last['regime']:<8}  {last['position_count']}")
    print()

    print("  LAST 10 CLOSED TRADES")
    print(thin)
    closed = [t for t in r.trade_log if t["status"] == "closed"][-10:]
    if closed:
        print(f"  {'Symbol':<6}  {'Dir':<5}  {'Entry':>10}  {'Exit':>10}  {'P&L':>9}  {'P&L%':>7}")
        for t in closed:
            sym = t["symbol"][:6]
            d = t["direction"][:5]
            ep = f"${t['entry_price']:.2f}" if t["entry_price"] else "-"
            xp = f"${t['exit_price']:.2f}" if t.get("exit_price") else "-"
            pnl = t.get("pnl", 0)
            pnl_pct = t.get("pnl_pct", 0)
            sign = "+" if pnl >= 0 else ""
            print(f"  {sym:<6}  {d:<5}  {ep:>10}  {xp:>10}  {sign}${pnl:>7.2f}  {pnl_pct*100:>+.1f}%")
    else:
        print("  No closed trades recorded.")
    print()
    print(sep)
    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    logger.info("Starting AetherTrade-Swarm backtest")
    logger.info("Period:  %s to %s", BACKTEST_START, BACKTEST_END)
    logger.info("Capital: $%.0f | Leverage: %.0fx", INITIAL_CAPITAL, LEVERAGE)
    logger.info("Universe: %s", ", ".join(UNIVERSE))

    engine = BacktestEngine(
        start=BACKTEST_START,
        end=BACKTEST_END,
        initial_capital=INITIAL_CAPITAL,
        leverage=LEVERAGE,
        universe=UNIVERSE,
    )

    results = engine.run()

    # Print formatted report to stdout
    print_report(results)

    # Save JSON results
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    # Convert dataclass to dict
    results_dict = {
        "run_id": results.run_id,
        "start_date": results.start_date,
        "end_date": results.end_date,
        "initial_capital": results.initial_capital,
        "leverage": LEVERAGE,
        "universe": UNIVERSE,
        "final_nav": results.final_nav,
        "total_return": results.total_return,
        "annualized_return": results.annualized_return,
        "sharpe_ratio": results.sharpe_ratio,
        "sortino_ratio": results.sortino_ratio,
        "calmar_ratio": results.calmar_ratio,
        "max_drawdown": results.max_drawdown,
        "win_rate": results.win_rate,
        "profit_factor": results.profit_factor,
        "avg_win": results.avg_win,
        "avg_loss": results.avg_loss,
        "total_trades": results.total_trades,
        "best_day": results.best_day,
        "worst_day": results.worst_day,
        "volatility_annual": results.volatility_annual,
        "regime_breakdown": results.regime_breakdown,
        "pod_attribution": results.pod_attribution,
        "run_duration_ms": results.run_duration_ms,
        "equity_curve": results.equity_curve,
        "trade_log": results.trade_log,
    }

    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(results_dict, f, indent=2, default=str)

    logger.info("Results saved to %s", RESULTS_FILE)
    logger.info("Backtest complete. Final NAV: $%.2f (%.2f%% total return)",
                results.final_nav,
                results.total_return * 100)


if __name__ == "__main__":
    main()
