# AetherTrade-Swarm — Implementation TODO

> Priority: P0 (must-have for MVP) · P1 (important) · P2 (nice-to-have)
> Each sprint = 1 focused deliverable, tested before commit

---

## Sprint 1: Foundation (Repo + Supabase + Branding)
- [x] Create GitHub repo `Maca2024/AetherTrade-Swarm`
- [x] Create Supabase project `sooufmgxxuirbsxouxju` (EU-West)
- [ ] **P0** Write CLAUDE.md with project context
- [ ] **P0** Write README.md with graphic badges + architecture diagram
- [ ] **P0** Create Supabase schema (migration SQL)
- [ ] **P0** Run migration on Supabase
- [ ] **P0** Update backend .env with new Supabase credentials
- [ ] **P0** Rename all "Oracle Swarm" references to "AetherTrade-Swarm"
- [ ] Commit + push sprint 1

## Sprint 2: Market Data Layer
- [ ] **P0** Create `backend/data/market_data.py` — yfinance fetcher
  - fetch_daily(symbol, period) → OHLCV DataFrame
  - fetch_batch(symbols) → dict of DataFrames
  - store_to_supabase(data) → insert into market_data_daily
- [ ] **P0** Create `backend/data/crypto_data.py` — CoinGecko fetcher
  - fetch_crypto_prices(coins) → prices dict
- [ ] **P0** Create `backend/data/cache.py` — in-memory LRU cache
- [ ] **P0** Add `/api/v1/market-data/{symbol}` endpoint
- [ ] **P0** Add `/api/v1/market-data/batch` endpoint
- [ ] Test: fetch AAPL, MSFT, BTC prices and verify response
- [ ] Commit + push sprint 2

## Sprint 3: Real Regime Detection
- [ ] **P0** Modify `regime_detector.py` to use real market returns
  - Fetch SPY daily returns from Supabase/yfinance
  - Fit HMM on rolling 252-day window
  - Predict current regime with confidence
- [ ] **P0** Store regime transitions in Supabase `regime_history`
- [ ] **P0** Update `/api/v1/regime` to return real regime state
- [ ] Test: verify regime detection on live SPY data
- [ ] Commit + push sprint 3

## Sprint 4: Real Strategy Signals
- [ ] **P0** Momentum pod: real 12-1 momentum from price data
  - Calculate returns, rank assets, generate long/short signals
- [ ] **P0** Mean Reversion pod: real RSI-2 + Bollinger Bands
  - Calculate RSI, Bollinger, generate signals on deviations
- [ ] **P1** Macro pod: real risk-parity from asset class returns
- [ ] **P1** StatArb pod: real PCA residuals from correlated assets
- [ ] **P1** AI/ML pod: connect to LiteLLM for macro analysis
- [ ] **P0** Store all signals in Supabase `signals` table
- [ ] **P0** Update signal_engine.py to aggregate real signals
- [ ] Test: verify signals are computed from real prices
- [ ] Commit + push sprint 4

## Sprint 5: Portfolio + Execution Engine
- [ ] **P0** Create `backend/execution/paper_trader.py`
  - Simulate trades based on signals (no Alpaca yet)
  - Track positions in Supabase `positions` table
  - Log trades in Supabase `trades` table
- [ ] **P0** Create `backend/execution/position_tracker.py`
  - Calculate unrealized P&L from current prices
  - Track exposure, leverage, cash
- [ ] **P0** Update `/api/v1/portfolio` to show real positions
- [ ] **P0** Store daily snapshots in `portfolio_snapshots`
- [ ] **P0** Update risk_manager.py to use real position data
- [ ] Test: simulate a trade cycle, verify P&L calculation
- [ ] Commit + push sprint 5

## Sprint 6: Frontend Dashboard Upgrade
- [ ] **P0** Create dashboard layout with sidebar navigation
- [ ] **P0** Dashboard page: live regime, top signals, portfolio summary
- [ ] **P0** Pods page: grid with real signals + per-pod charts
- [ ] **P0** Portfolio page: positions table, equity curve chart
- [ ] **P0** Risk page: live risk metrics, kill switch status
- [ ] **P0** Update API client to use new Supabase endpoints
- [ ] **P0** AetherLink branding: purple/dark theme, logo
- [ ] Test: verify all pages render with real data
- [ ] Commit + push sprint 6

## Sprint 7: Landing Page + Deploy
- [ ] **P0** Hero section with AetherTrade branding
- [ ] **P0** Feature showcase (9 pods, regime detection, risk mgmt)
- [ ] **P0** Live metrics display (real portfolio stats)
- [ ] **P0** CTA section
- [ ] **P0** Deploy frontend to Vercel
- [ ] **P0** Configure CORS for Vercel domain
- [ ] Test: full E2E from Vercel → Kathedraal API → Supabase
- [ ] Commit + push sprint 7

## Sprint 8: Polish + Documentation
- [ ] **P1** Fix chat endpoint (connect LiteLLM)
- [ ] **P1** Add WebSocket endpoint for live updates
- [ ] **P1** Performance optimization (caching, lazy loading)
- [ ] **P1** API documentation page
- [ ] **P1** Error handling + graceful degradation
- [ ] Final commit + push + tag v1.0.0

---

## Backlog (Post-MVP)
- [ ] **P2** Alpaca paper trading integration (real orders)
- [ ] **P2** Backtesting engine on historical data
- [ ] **P2** User authentication (Supabase Auth)
- [ ] **P2** Options Vol pod: real VIX + options chain data
- [ ] **P2** Behavioral pod: real sentiment from news APIs
- [ ] **P2** Market Making pod: real order book data
- [ ] **P2** Multi-Factor pod: real factor data from FRED/Quandl
- [ ] **P2** Mobile-responsive dashboard
- [ ] **P2** Email alerts for risk events
- [ ] **P2** CORTEX integration (self-learning loop)
