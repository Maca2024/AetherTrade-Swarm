<p align="center">
  <img src="https://img.shields.io/badge/AetherTrade-Swarm-7C3AED?style=for-the-badge&logo=data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyNCIgaGVpZ2h0PSIyNCIgdmlld0JveD0iMCAwIDI0IDI0IiBmaWxsPSJub25lIiBzdHJva2U9IndoaXRlIiBzdHJva2Utd2lkdGg9IjIiPjxwYXRoIGQ9Ik0yIDEyaDIwTTEyIDJsMTAgMTAtMTAgMTBMMiAxMmwxMC0xMFoiLz48L3N2Zz4=&logoColor=white" alt="AetherTrade-Swarm" />
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11-3776AB?style=flat-square&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/FastAPI-0.115-009688?style=flat-square&logo=fastapi&logoColor=white" />
  <img src="https://img.shields.io/badge/Next.js-14-000000?style=flat-square&logo=next.js&logoColor=white" />
  <img src="https://img.shields.io/badge/Supabase-EU--West-3FCF8E?style=flat-square&logo=supabase&logoColor=white" />
  <img src="https://img.shields.io/badge/Docker-Ready-2496ED?style=flat-square&logo=docker&logoColor=white" />
  <img src="https://img.shields.io/badge/Agents-16-FF3366?style=flat-square" />
  <img src="https://img.shields.io/badge/License-Proprietary-gray?style=flat-square" />
</p>

<p align="center">
  <strong>16-Agent AI Trading Platform</strong><br/>
  <em>Regime-adaptive multi-strategy portfolio management with institutional-grade risk controls</em>
</p>

---

## Architecture

```
                    ┌─────────────────────────┐
                    │    Market Data Layer     │
                    │ yfinance · CoinGecko    │
                    └───────────┬─────────────┘
                                │
                    ┌───────────▼─────────────┐
                    │    Regime Detector       │
                    │    (HMM 4-State)         │
                    │ BULL·RANGE·BEAR·CRISIS   │
                    └───────────┬─────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        │                       │                       │
   ┌────▼────┐            ┌────▼────┐            ┌────▼────┐
   │   MOM   │            │  MACRO  │            │  AI/ML  │
   │ 12-1 XS │            │  Risk   │            │  LLM +  │
   │ TSMOM   │            │ Parity  │            │   TFT   │
   └────┬────┘            └────┬────┘            └────┬────┘
        │    ┌────────┐        │    ┌────────┐        │
        │    │  MR    │        │    │  SA    │        │
        │    │ RSI-2  │        │    │  PCA   │        │
        │    │ BBands │        │    │ Pairs  │        │
        │    └───┬────┘        │    └───┬────┘        │
        │        │             │        │             │
   ┌────▼────┐   │        ┌───▼────┐   │        ┌───▼────┐
   │   VOL   │   │        │  BEH   │   │        │   MF   │
   │  VRP +  │   │        │ Senti  │   │        │ Value  │
   │  Tail   │   │        │ ment   │   │        │ Qual.  │
   └────┬────┘   │        └───┬────┘   │        └───┬────┘
        │        │             │        │             │
        └────────┴─────────────┴────────┴─────────────┘
                               │
                    ┌──────────▼──────────────┐
                    │     Signal Engine       │
                    │  Regime-Weighted Fusion  │
                    │    Black-Litterman      │
                    └──────────┬──────────────┘
                               │
                    ┌──────────▼──────────────┐
                    │   Portfolio Optimizer    │
                    │   Half-Kelly Sizing     │
                    └──────────┬──────────────┘
                               │
                    ┌──────────▼──────────────┐
                    │     Risk Manager        │
                    │  8 Metrics · 4 Kills    │
                    │  VaR · CVaR · Stress    │
                    └─────────────────────────┘
```

## The 9 Strategy Pods

| Pod | Strategy | Signal Source | Best Regime |
|-----|----------|-------------|-------------|
| **Momentum** | 12-1 cross-sectional + TSMOM | Price momentum, vol-scaled | Bull |
| **Mean Reversion** | RSI-2 + Bollinger Bands | Statistical deviations | Range |
| **Macro** | Risk parity + carry trades | Cross-asset allocation | Bear/Crisis |
| **Stat Arb** | PCA residual + pairs | Cointegration spreads | Market-neutral |
| **Options Vol** | VRP + tail hedging | Volatility surface | All (hedge) |
| **Behavioral** | Sentiment contrarian | Crowd positioning | Extremes |
| **AI/ML** | LLM macro + TFT forecasts | Claude Sonnet analysis | Adaptive |
| **Multi-Factor** | Value/quality/momentum | Factor Z-scores | Regime-tilted |
| **Market Making** | Order flow imbalance | Bid-ask dynamics | Liquid markets |

## Risk Management

| Metric | Warning | Critical | Auto-Action |
|--------|---------|----------|-------------|
| Annualized Volatility | >15% | >25% | Reduce exposure |
| Maximum Drawdown | >10% | >20% | Flatten positions |
| Gross Leverage | >1.75x | >2.5x | Reduce leverage |
| Concentration Risk | >25% | >40% | Rebalance |
| Liquidity Score | >20% | >35% | Exit illiquid |
| Tail Risk (99% VaR) | >3% | >6% | Hedge |
| Strategy Correlation | >0.5 | >0.7 | Diversify |
| Daily Loss | >2.5% | >5% | Halt trading |

## Quick Start

### Backend
```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # fill in credentials
uvicorn main:app --host 0.0.0.0 --port 8888
```

### Frontend
```bash
cd frontend
npm install
cp .env.example .env.local  # fill in API URL
npm run dev
```

### Docker
```bash
docker-compose up -d
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI + Python 3.11 |
| Frontend | Next.js 14 + React 18 + TailwindCSS |
| Database | Supabase (PostgreSQL, EU-West) |
| Market Data | yfinance + CoinGecko |
| ML/AI | hmmlearn + scikit-learn + Claude Sonnet |
| Charts | Recharts + Framer Motion |
| Deploy | Docker (Kathedraal) + Vercel (frontend) |

## API

Base URL: `https://api.aethertrade.aetherlink.ai`

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Service health |
| GET | `/api/v1/regime` | Current market regime |
| GET | `/api/v1/strategies` | All 9 strategy pods |
| GET | `/api/v1/signals/combined` | Ensemble trading signal |
| GET | `/api/v1/portfolio` | Portfolio state |
| GET | `/api/v1/portfolio/performance` | Performance metrics |
| GET | `/api/v1/risk` | Risk dashboard |
| GET | `/api/v1/market-data/{symbol}` | Price data |
| POST | `/api/v1/chat` | AI assistant |

---

<p align="center">
  <strong>AetherLink B.V.</strong> · Built with Claude Code<br/>
  <em>Multi-agent AI that trades smarter, not harder</em>
</p>
