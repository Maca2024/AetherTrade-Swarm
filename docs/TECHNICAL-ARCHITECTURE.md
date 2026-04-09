# AetherTrade-Swarm — Technical Architecture

> 16-Agent AI Trading Platform | AetherLink B.V.
> Supabase: `sooufmgxxuirbsxouxju` | Region: EU-West (Ireland)

---

## 1. System Overview

AetherTrade-Swarm is a multi-strategy AI trading platform with 9 independent strategy pods,
regime-adaptive allocation, and institutional-grade risk management. It transitions from
the Oracle Swarm simulation prototype into a production trading system with real market data.

```
┌─────────────────────────────────────────────────────────┐
│              FRONTEND (Next.js 14 on Vercel)            │
│  Dashboard · Regime · Pods · Risk · Portfolio · Chat    │
└────────────────────┬────────────────────────────────────┘
                     │ REST + WebSocket
┌────────────────────▼────────────────────────────────────┐
│              BACKEND (FastAPI on Kathedraal :8888)       │
│                                                          │
│  ┌─ Market Data Layer ──────────────────────────────┐   │
│  │  yfinance · Alpaca · CoinGecko · Alpha Vantage   │   │
│  └──────────────────────────────────────────────────┘   │
│                         ↓                                │
│  ┌─ Regime Detector (HMM) ──────────────────────────┐   │
│  │  4 states: BULL · RANGE · BEAR · CRISIS           │   │
│  └──────────────────────────────────────────────────┘   │
│                         ↓                                │
│  ┌─ 9 Strategy Pods ───────────────────────────────┐   │
│  │  Momentum · MeanRev · Macro · StatArb · OptionsVol│  │
│  │  Behavioral · AI/ML · MultiFactor · MarketMaking  │  │
│  └──────────────────────────────────────────────────┘   │
│                         ↓                                │
│  ┌─ Signal Engine (Ensemble) ───────────────────────┐   │
│  │  Regime-weighted · Black-Litterman · Half-Kelly   │   │
│  └──────────────────────────────────────────────────┘   │
│                         ↓                                │
│  ┌─ Execution Engine ──────────────────────────────┐   │
│  │  Alpaca Paper Trading · Order Management         │   │
│  └──────────────────────────────────────────────────┘   │
│                         ↓                                │
│  ┌─ Risk Manager ──────────────────────────────────┐   │
│  │  8 Metrics · 4 Kill Switches · VaR/CVaR          │   │
│  └──────────────────────────────────────────────────┘   │
│                                                          │
└──────────────────────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│              SUPABASE (EU-West)                          │
│  trades · positions · signals · performance ·            │
│  regime_history · risk_alerts · users · api_keys         │
└──────────────────────────────────────────────────────────┘
```

---

## 2. Current State (from Oracle Swarm)

### What exists and works:
| Component | Lines | Status |
|-----------|-------|--------|
| FastAPI backend | 5,098 | Runs on :8888 via Docker |
| 9 Strategy pods | ~1,200 | Generate random signals (not real) |
| Regime detector (HMM) | 190 | HMM + heuristic fallback |
| Risk manager | 288 | 8 metrics, 4 kill switches |
| Portfolio optimizer | 192 | Black-Litterman + Half-Kelly |
| Signal engine | 163 | Regime-weighted ensemble |
| Data simulator | 844 | Generates fake 2yr history |
| Auth (API keys) | 164 | SHA-256 hashed, tiered rate limiting |
| Frontend (Next.js) | 11 components | Dark theme dashboard |
| Chat endpoint | 188 | Broken (missing API key) |

### What's fake/simulated:
- ALL market data (random returns from seed)
- ALL portfolio state (NAV, positions, P&L)
- ALL strategy signals (random within regime constraints)
- ALL performance metrics (computed from simulated data)
- Regime transitions (seeded random walk)

### What's missing for production:
- Real market data feeds
- Real signal computation from price data
- Order execution (paper or live)
- Proper Supabase schema (only 2 tables exist)
- User authentication (only API keys, no user accounts)
- WebSocket for real-time updates
- Historical data storage
- Backtesting on real data

---

## 3. Target Architecture

### 3.1 Market Data Layer

| Source | Data | Cost | Use |
|--------|------|------|-----|
| **yfinance** | Stocks, ETFs, crypto (delayed) | Free | Primary price data |
| **Alpaca Markets** | Real-time US stocks, paper trading | Free tier | Execution + live data |
| **CoinGecko** | Crypto prices, market cap | Free | Crypto pod data |
| **Alpha Vantage** | Forex, commodities, technicals | Free (5 req/min) | Macro pod data |

### 3.2 Supabase Schema

```sql
-- Core tables
users                -- Supabase Auth managed
user_settings        -- Trading preferences, risk tolerance
api_keys             -- API access (existing, migrate)

-- Market data
market_data_daily    -- OHLCV daily bars (yfinance)
market_data_intraday -- 5-min bars for active trading

-- Trading engine
signals              -- Generated signals per pod
trades               -- Executed trades (paper/live)
positions            -- Current open positions
orders               -- Pending orders

-- Performance
portfolio_snapshots  -- Daily NAV, cash, exposure
performance_daily    -- Daily returns, rolling metrics
equity_curve         -- NAV timeseries

-- Intelligence
regime_history       -- HMM regime transitions (existing, migrate)
risk_alerts          -- Active/historical alerts
pod_metrics          -- Per-pod daily performance stats

-- System
system_logs          -- Backend events
cron_jobs            -- Scheduled data fetches
```

### 3.3 Backend Modules (New/Modified)

```
backend/
├── main.py                    # FastAPI app (existing, modify)
├── config.py                  # Settings (existing, modify)
├── api/
│   ├── auth.py                # API key auth (existing)
│   ├── deps.py                # Dependencies (existing, modify)
│   └── routes/
│       ├── health.py          # Health check (existing)
│       ├── regime.py          # Regime endpoints (modify: real data)
│       ├── strategies.py      # Pod endpoints (modify: real signals)
│       ├── signals.py         # Signal endpoints (modify: real)
│       ├── portfolio.py       # Portfolio (modify: real positions)
│       ├── risk.py            # Risk dashboard (modify: real)
│       ├── keys.py            # API keys (existing)
│       ├── chat.py            # AI chat (fix: connect LiteLLM)
│       ├── market_data.py     # NEW: price data endpoints
│       └── backtest.py        # NEW: backtesting endpoints
├── core/
│   ├── regime_detector.py     # HMM regime (modify: real returns)
│   ├── signal_engine.py       # Ensemble (modify: real signals)
│   ├── portfolio_optimizer.py # BL optimizer (modify: real positions)
│   ├── risk_manager.py        # Risk (modify: real calculations)
│   └── strategy_pods/         # Each pod: real algorithms
├── data/
│   ├── market_data.py         # NEW: yfinance + Alpaca fetcher
│   ├── crypto_data.py         # NEW: CoinGecko fetcher
│   └── cache.py               # NEW: data caching layer
├── execution/
│   ├── paper_trader.py        # NEW: Alpaca paper trading
│   ├── order_manager.py       # NEW: order lifecycle
│   └── position_tracker.py    # NEW: position management
├── models/
│   ├── schemas.py             # Pydantic models (modify)
│   └── database.py            # Supabase client (modify)
└── utils/
    ├── data_simulator.py      # Keep as fallback/demo mode
    └── metrics.py             # Performance calculations (modify)
```

### 3.4 Frontend Pages

```
frontend/app/
├── page.tsx                   # Landing/hero page
├── dashboard/
│   ├── page.tsx               # Main dashboard
│   ├── regime/page.tsx        # Regime analysis
│   ├── pods/page.tsx          # Strategy pods grid
│   ├── pods/[id]/page.tsx     # Individual pod detail
│   ├── portfolio/page.tsx     # Positions + trades
│   ├── risk/page.tsx          # Risk dashboard
│   ├── backtest/page.tsx      # Backtesting UI
│   └── settings/page.tsx      # User settings
├── api-docs/page.tsx          # API documentation
└── layout.tsx                 # Shared layout + nav
```

---

## 4. API Endpoints (Target)

### Existing (keep):
- `GET /health` — Service health
- `GET /api/v1/regime` — Current regime
- `GET /api/v1/regime/history` — Regime transitions
- `GET /api/v1/strategies` — All pods
- `GET /api/v1/strategies/{pod}` — Pod detail
- `GET /api/v1/strategies/{pod}/signals` — Pod signals
- `GET /api/v1/signals/combined` — Ensemble signal
- `GET /api/v1/signals/allocation` — Allocation weights
- `GET /api/v1/portfolio` — Portfolio state
- `GET /api/v1/portfolio/performance` — Performance metrics
- `GET /api/v1/portfolio/positions` — Open positions
- `GET /api/v1/risk` — Risk dashboard
- `GET /api/v1/risk/alerts` — Risk alerts
- `GET /api/v1/risk/correlation` — Strategy correlation
- `GET /api/v1/risk/kill-switches` — Kill switches
- `POST /api/v1/keys/generate` — Create API key
- `POST /api/v1/chat` — AI chat

### New endpoints:
- `GET /api/v1/market-data/{symbol}` — Price data
- `GET /api/v1/market-data/batch` — Multi-symbol prices
- `POST /api/v1/backtest` — Run backtest
- `GET /api/v1/backtest/{id}` — Backtest results
- `GET /api/v1/trades` — Trade history
- `POST /api/v1/trades/execute` — Execute signal (paper)
- `GET /api/v1/portfolio/equity-curve` — NAV timeseries
- `WS /ws/live` — WebSocket for real-time updates

---

## 5. Technology Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Backend | FastAPI + Uvicorn | 0.115+ |
| Database | Supabase (PostgreSQL) | EU-West |
| Market Data | yfinance + Alpaca + CoinGecko | Latest |
| ML | scikit-learn + hmmlearn + numpy | 1.6+ |
| LLM | LiteLLM → Claude Sonnet | via Kathedraal :4000 |
| Frontend | Next.js 14 + React 18 | 14.2+ |
| Styling | TailwindCSS + Radix UI | 3.4+ |
| Charts | Recharts | 2.12+ |
| Animations | Framer Motion | 11+ |
| Deployment | Docker (Kathedraal) + Vercel (frontend) | |
| CI/CD | GitHub Actions | |

---

## 6. Environment Variables

### Backend (.env)
```
SUPABASE_URL=https://sooufmgxxuirbsxouxju.supabase.co
SUPABASE_KEY=<service_role_key>
ALPACA_API_KEY=<paper_trading_key>
ALPACA_SECRET_KEY=<paper_trading_secret>
ALPACA_BASE_URL=https://paper-api.alpaca.markets
LITELLM_API_BASE=http://localhost:4000
CHAT_MODEL=claude-sonnet
ENVIRONMENT=production
CORS_ORIGINS=http://localhost:3000,https://aethertrade-swarm.vercel.app
```

### Frontend (.env.local)
```
NEXT_PUBLIC_API_URL=https://api.aethertrade.aetherlink.ai
NEXT_PUBLIC_SUPABASE_URL=https://sooufmgxxuirbsxouxju.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=<anon_key>
```
