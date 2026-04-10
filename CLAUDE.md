# AetherTrade-Swarm

## Project
- **Name**: AetherTrade-Swarm
- **Type**: AI Trading Platform + Insider Signals SaaS
- **Owner**: AetherLink B.V. (Constance van der Vlist)
- **Repo**: github.com/Maca2024/AetherTrade-Swarm
- **Version**: 1.5.0
- **Backend LOC**: ~9,000 Python
- **Frontend LOC**: ~9,500 TypeScript/React
- **Live**:
  - Landing: frontend-sigma-ashen-30.vercel.app
  - Dashboard: frontend-sigma-ashen-30.vercel.app/dashboard
  - Insider Signals: frontend-sigma-ashen-30.vercel.app/insider-signals
  - API: api.aethertrade.aetherlink.ai (Kathedraal :8888)

## Stack
- **Backend**: FastAPI + Python 3.11 (Kathedraal :8888)
- **Frontend**: Next.js 14 + React 18 + TailwindCSS (Vercel)
- **Database**: Supabase `sooufmgxxuirbsxouxju` (EU-West, 10 tables)
- **Market Data**: yfinance (stocks/ETFs), CoinGecko (crypto)
- **ML**: hmmlearn (HMM 4-state regime), scikit-learn, numpy, scipy
- **LLM**: LiteLLM proxy → Claude Sonnet (Kathedraal :4000)
- **Deploy**: Docker (backend) + Vercel (frontend)

## Architecture
9 strategy pods generate signals from REAL yfinance market data:
1. **Momentum** — 12-1 cross-sectional ranking + vol-scaled TSMOM (20 assets)
2. **Mean Reversion** — RSI-2 oversold/overbought + Bollinger Band breakout (12 assets)
3. **Macro** — Inverse-vol risk parity across SPY/TLT/GLD/USO/EEM + safe-haven tilt
4. **Stat Arb** — Pairs z-score on AAPL/MSFT, GOOGL/META, JPM/GS (60-day rolling)
5. **Options Vol** — Realized vs implied vol spread + tail hedge when vol > 25%
6. **Behavioral** — Price-momentum divergence + volume spikes + consecutive down days
7. **AI/ML** — SMA crossovers (5/10/20/50) + RSI-14 + volume trend consensus scoring
8. **Multi-Factor** — Value (52w-high ratio) + momentum (6mo) + low-vol composite Z-score
9. **Market Making** — High-low spread + volume profile + intraday reversal detection

Pipeline: Market Data → Regime Detector (HMM on real SPY returns) → 9 Pods → Signal Engine (regime-weighted ensemble) → Portfolio Optimizer (Black-Litterman + Half-Kelly) → Paper Trader → Risk Manager (8 metrics + 4 kill switches)

## Key Files
- `backend/main.py` — FastAPI entry, lifespan init (regime, market data, simulator, insider)
- `backend/core/strategy_pods/*.py` — 9 pods, all on real yfinance data
- `backend/core/regime_detector.py` — HMM + heuristic fallback, inits from real SPY
- `backend/core/self_learning.py` — CORTEX-style self-learning loop
- `backend/data/market_data.py` — yfinance + CoinGecko with 5-min cache
- `backend/execution/paper_trader.py` — Signal execution, position upsert, 20% max sizing
- `backend/execution/position_tracker.py` — Live P&L, portfolio summary, daily snapshots
- `backend/insider/edgar_fetcher.py` — SEC EDGAR Form 4 fetcher
- `backend/insider/cluster_detector.py` — 3+ insiders / 10-day / code P / $25K+ filter
- `backend/insider/backtest.py` — Historical backtest engine
- `backend/backtest/engine.py` — Multi-strategy ensemble backtester (v1.4.0)
- `backend/api/routes/trades.py` — Trade execution + equity curve
- `backend/api/routes/market_data.py` — Real price data
- `backend/api/routes/insider.py` — 6 insider endpoints
- `backend/api/routes/learning.py` — Self-learning engine API
- `frontend/app/dashboard/` — 7 pages: overview, regime, pods, portfolio, risk, settings
- `frontend/app/insider-signals/` — Landing page for Insider Signals SaaS
- `frontend/components/AuthButton.tsx` — Google OAuth via Supabase
- `supabase/migrations/001_initial_schema.sql` — 10 tables
- `supabase/migrations/002_insider_schema.sql` — 4 insider tables

## Products
1. **AetherTrade-Swarm Dashboard** — Multi-strategy trading platform showcase
2. **AetherTrade Insider Signals** (v1.5.0) — SaaS signal feed (€49/€149 per month)
   - Backtest: 23.1% annualized, 62% win rate, +11.6% alpha vs SPY (2020-2025)
   - Target: solo traders, small RIAs, family offices
   - Break-even: 15 customers × €49 = €735 MRR

## Frontend Pages
- `/` — Landing page (hero, architecture viz, performance, risk, API docs, chat)
- `/dashboard` — Overview (regime badge, performance cards, quick stats)
- `/dashboard/regime` — HMM regime analysis + history
- `/dashboard/pods` — 9-pod grid with performance comparison
- `/dashboard/portfolio` — Positions table + equity curve + trade log
- `/dashboard/risk` — 8 risk metrics + radar chart + VaR history + kill switches
- `/dashboard/settings` — API key management

## Conventions
- Conventional commits: feat:, fix:, docs:, refactor:
- TypeScript strict in frontend
- Pydantic v2 models in backend
- All secrets in .env (never commit)
- Co-Author: Claude Opus 4.6 <noreply@anthropic.com>

## Supabase
- Project: sooufmgxxuirbsxouxju
- URL: https://sooufmgxxuirbsxouxju.supabase.co
- Region: EU-West (Ireland)
- Tables: market_data_daily, api_keys, regime_history, signals, trades, positions, portfolio_snapshots, pod_metrics, risk_alerts, system_logs
- RLS: service_role full access, anon read on public tables
