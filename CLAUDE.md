# AetherTrade-Swarm

## Project
- **Name**: AetherTrade-Swarm
- **Type**: 16-Agent AI Trading Platform
- **Owner**: AetherLink B.V. (Constance van der Vlist)
- **Repo**: github.com/Maca2024/AetherTrade-Swarm
- **Origin**: Forked from Oracle Swarm prototype, upgraded to production

## Stack
- **Backend**: FastAPI + Python 3.11 (Kathedraal :8888)
- **Frontend**: Next.js 14 + React 18 + TailwindCSS (Vercel)
- **Database**: Supabase `sooufmgxxuirbsxouxju` (EU-West)
- **Market Data**: yfinance (stocks), CoinGecko (crypto)
- **ML**: hmmlearn (HMM regime), scikit-learn, numpy
- **LLM**: LiteLLM proxy → Claude Sonnet (Kathedraal :4000)
- **Deploy**: Docker (backend) + Vercel (frontend)

## Architecture
9 strategy pods generate signals from real market data:
1. Momentum (12-1 cross-sectional + TSMOM)
2. Mean Reversion (RSI-2 + Bollinger Bands)
3. Macro (risk parity + carry)
4. Stat Arb (PCA residual + pairs)
5. Options Vol (VRP + tail hedge)
6. Behavioral (sentiment contrarian)
7. AI/ML (LLM macro + forecasts)
8. Multi-Factor (value/quality/momentum)
9. Market Making (order flow)

Regime Detector (HMM) → Signal Engine (ensemble) → Portfolio Optimizer (Black-Litterman) → Risk Manager (kill switches)

## Key Files
- `backend/main.py` — FastAPI entry point
- `backend/core/strategy_pods/` — 9 pod implementations
- `backend/core/regime_detector.py` — HMM regime detection
- `backend/core/signal_engine.py` — Ensemble aggregator
- `backend/data/market_data.py` — Real market data fetcher
- `backend/execution/paper_trader.py` — Paper trading engine
- `frontend/app/page.tsx` — Landing page
- `frontend/app/dashboard/` — Dashboard pages
- `docs/TECHNICAL-ARCHITECTURE.md` — Full tech doc
- `docs/TODO.md` — Sprint-based implementation plan

## Conventions
- Conventional commits: feat:, fix:, docs:, refactor:
- TypeScript strict mode in frontend
- Pydantic v2 models in backend
- All secrets in .env (never commit)
- Co-Author: Claude Opus 4.6 <noreply@anthropic.com>

## Supabase
- Project: sooufmgxxuirbsxouxju
- URL: https://sooufmgxxuirbsxouxju.supabase.co
- Region: EU-West (Ireland)
- Schema: see docs/TECHNICAL-ARCHITECTURE.md
