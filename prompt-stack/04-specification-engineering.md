# Discipline 4: Specification Engineering — ORACLE SWARM
## Self-Contained Specification voor Autonome Multi-Week Operatie

> Level: L7 (Swarm) | Schaal: weken/maanden | Volledig self-contained

---

## Pentagon Header

```yaml
specification:
  name: "ORACLE SWARM Trading Platform"
  version: "1.0.0"
  role: "Autonomous AI Trading Orchestrator"
  context: "Multi-strategy quantitative trading platform managing 9 strategy pods across 4 market regimes"
  goal: "Achieve Sharpe 1.5-2.0 with max drawdown <15% through dynamic regime-aware allocation"
  process: "7-layer architecture: Data → Signals → Orchestration → Portfolio → Execution → Risk → Learning"
  format: "JSON API responses, structured logs, real-time WebSocket streams"
  intent_reference: "03-intent-engineering.md"
  prompt_reference: "01-prompt-craft.md"
  context_reference: "02-context-engineering.md"
```

---

## Primitief 1: Self-Contained Problem Statement

### What
Build and operate an AI-driven trading platform that simultaneously runs 9 independent strategy pods (Momentum, Mean-Reversion, Global Macro, Statistical Arbitrage, Options/Volatility, Behavioral Finance, AI/ML, Multi-Factor, Market Making), detects market regimes in real-time, and dynamically allocates capital across these strategies to maximize risk-adjusted returns.

### Why
No single trading strategy works in all market conditions. By combining uncorrelated alpha sources with AI-powered regime detection, the platform captures the "Medallion Fund philosophy" — not one brilliant strategy, but an infrastructure for combining thousands of signals — at a fraction of the cost using modern AI tools (LLMs, transformers, reinforcement learning).

### Who
- **Operator**: Human portfolio manager (final authority on kill switch overrides)
- **ORACLE**: AI orchestration engine (autonomous within risk budget)
- **Strategy Pods**: 9 independent signal generators (autonomous within their domain)
- **Risk Engine**: Continuous monitoring system (autonomous with escalation)
- **Execution Engine**: Trade execution system (operates under ORACLE direction)

### Constraints
- Target Sharpe: 1.5-2.0
- Max Drawdown: -15% absolute limit (kill switch BLACK)
- Leverage: Max 3x gross
- Single Position: Max 5% of NAV
- Strategy Concentration: Max 25% per pod
- Portfolio Volatility: 8-12% target
- Tail Hedge: Minimum 3% always allocated
- Minimum Live Assets: Paper trade 30 days before live

---

## Primitief 2: Acceptance Criteria

### Functioneel
```
AC-F1: Given market data input, the system detects the correct regime
        (BULL/BEAR/CRISIS/RANGE_BOUND) with >70% accuracy on backtested data
AC-F2: Given regime change, the system adjusts strategy allocations within
        the defined regime table within 1 rebalance cycle
AC-F3: Given a drawdown exceeding -10%, the RED kill switch activates within
        60 seconds and reduces gross exposure by 50% within 4 hours
AC-F4: Given signals from all 9 pods, the Black-Litterman optimizer produces
        a portfolio that respects all constraints (leverage, concentration, vol)
AC-F5: Given a full trading day, P&L attribution is logged per pod per trade
        with 100% coverage (no unattributed P&L)
```

### Technisch
```
AC-T1: API responds to all endpoints within 200ms (p95)
AC-T2: WebSocket stream delivers updates within 100ms of market data receipt
AC-T3: System handles 1000+ concurrent API connections (pro tier)
AC-T4: All API keys are SHA-256 hashed before storage (never plaintext)
AC-T5: Database queries use parameterized queries only (no SQL injection)
AC-T6: System recovers from crash within 60 seconds (auto-restart)
AC-T7: All 8 risk metrics computed every 60 seconds
```

### Visueel (Frontend Dashboard)
```
AC-V1: Dashboard loads within 2 seconds on 4G connection
AC-V2: Regime indicator updates in real-time (< 1 second visual delay)
AC-V3: Strategy pod cards show sparkline charts with smooth animations
AC-V4: Risk panel shows traffic light colors matching current alert level
AC-V5: Mobile-responsive down to 375px width
AC-V6: Accessibility: WCAG 2.1 AA compliance on all interactive elements
```

---

## Primitief 3: Constraint Architecture

### MUST (Non-negotiable)
```
MUST-001: Max drawdown kill switch at -15% triggers FULL HALT
MUST-002: Tail hedge allocation >= 3% of NAV at all times
MUST-003: API keys hashed (SHA-256) before database storage
MUST-004: All trades logged with complete audit trail
MUST-005: Parameterized queries for all database operations
MUST-006: Environment variables for all secrets (never in code)
MUST-007: Rate limiting on all API endpoints
MUST-008: CORS restricted to authorized origins only
MUST-009: Kill switch activation logged with timestamp + reason
MUST-010: Human override available for all automated decisions
```

### MUST-NOT (Forbidden)
```
MUST-NOT-001: Never exceed 3x gross leverage
MUST-NOT-002: Never allocate >25% to single strategy pod
MUST-NOT-003: Never hold >5% NAV in single position
MUST-NOT-004: Never trade during kill switch RED/BLACK without human override
MUST-NOT-005: Never store API keys in plaintext
MUST-NOT-006: Never skip the paper trading period for new strategies
MUST-NOT-007: Never ignore data feed failures (freeze + alert)
MUST-NOT-008: Never use SQL string concatenation
MUST-NOT-009: Never commit secrets to version control
MUST-NOT-010: Never force-push to main branch
```

### PREFER (Best practices)
```
PREFER-001: Gradual position changes over sudden reallocation
PREFER-002: TWAP execution over market orders (except CRISIS)
PREFER-003: Ensemble models over single-model predictions
PREFER-004: Walk-forward validation over in-sample backtesting
PREFER-005: Half-Kelly sizing over full Kelly (survival > optimality)
PREFER-006: More strategy pods over deeper single-strategy bets
PREFER-007: Conservative regime classification when uncertain
PREFER-008: Structured logging over free-text
PREFER-009: Async operations over blocking calls
PREFER-010: Existing code patterns over new abstractions
```

### ESCALATE (Requires human decision)
```
ESCALATE-001: Adding or removing a strategy pod
ESCALATE-002: Changing risk parameters (leverage, vol target, drawdown limit)
ESCALATE-003: Deploying to production from paper trading
ESCALATE-004: Resuming after RED or BLACK kill switch
ESCALATE-005: Overriding regime detection during unusual markets
ESCALATE-006: Changing execution broker or adding new venues
ESCALATE-007: Any regulatory or compliance concern
ESCALATE-008: System-wide parameter changes (rebalance frequency, etc)
```

---

## Primitief 4: Decomposition

### Phase 1: Foundation (Month 1-3) — 12 Subtasks

| # | Subtask | Complexity | Dependencies | Acceptance Test |
|---|---------|-----------|--------------|-----------------|
| 1.1 | Data pipeline: Polygon.io market data → TimescaleDB | 2h | None | Tick data flowing for SPY, QQQ, IWM |
| 1.2 | Feature store: Technical indicators (50+) | 2h | 1.1 | RSI, MACD, Bollinger computed correctly |
| 1.3 | FastAPI skeleton: routes, auth, middleware | 2h | None | /health returns 200, swagger docs work |
| 1.4 | API key system: generate, validate, rate-limit | 2h | 1.3 | Can create key, authenticate, hit rate limit |
| 1.5 | Supabase schema: tables for keys, signals, trades | 1h | None | Migrations run successfully |
| 1.6 | Strategy Pod: Dual Momentum (simplest) | 2h | 1.1, 1.2 | Generates buy/sell signals matching backtest |
| 1.7 | Strategy Pod: RSI-2 Mean Reversion | 2h | 1.1, 1.2 | 70%+ win rate on paper trades |
| 1.8 | Strategy Pod: VRP Put Writing | 2h | 1.1 | Correct spread calculations, Greeks computed |
| 1.9 | Basic risk manager: position limits, drawdown | 2h | 1.3 | Kill switch triggers at thresholds |
| 1.10 | Paper trading engine | 2h | 1.6-1.8, 1.9 | Simulated fills with realistic slippage |
| 1.11 | Frontend: Dashboard MVP (Next.js) | 2h | 1.3 | Shows 3 pods, risk panel, regime indicator |
| 1.12 | Integration test: full cycle | 2h | All above | Signal → optimize → paper trade → P&L log |

### Phase 2: Core Engine (Month 4-6) — 10 Subtasks

| # | Subtask | Complexity | Dependencies | Acceptance Test |
|---|---------|-----------|--------------|-----------------|
| 2.1 | Strategy Pod: Vol-Scaled Momentum | 2h | Phase 1 | Sharpe improvement over raw momentum |
| 2.2 | Strategy Pod: Risk Parity Macro | 2h | Phase 1 | Correct risk parity weights across 4 assets |
| 2.3 | Strategy Pod: LLM Fundamental Analysis | 2h | Phase 1 | Processes 10-K, generates structured signal |
| 2.4 | Regime Detector: HMM 4-state | 2h | Phase 1 | >70% accuracy on backtested regimes |
| 2.5 | Dynamic Allocator: Black-Litterman | 2h | 2.4 | Allocation shifts correctly per regime |
| 2.6 | Signal Combiner: Ensemble engine | 2h | 2.1-2.3 | Combined signal outperforms any single pod |
| 2.7 | Execution: TWAP/VWAP algorithms | 2h | Phase 1 | Slippage < 10bps on paper trades |
| 2.8 | Risk: Full 8-metric dashboard | 2h | Phase 1 | All 8 metrics computed, alerts fire correctly |
| 2.9 | Frontend: Full dashboard with all pods | 2h | 2.1-2.8 | All sections functional, animations smooth |
| 2.10 | End-to-end backtest: 2020-2025 | 2h | All above | Sharpe > 1.0, drawdown < 20% on historical |

### Phase 3: Full Platform (Month 7-12) — 10 Subtasks

| # | Subtask | Complexity | Dependencies | Acceptance Test |
|---|---------|-----------|--------------|-----------------|
| 3.1-3.3 | Remaining strategy pods (Stat-Arb, Carry, TFT) | 2h each | Phase 2 | Each generates validated signals |
| 3.4 | RL Portfolio Optimizer | 2h | Phase 2 | Outperforms BL on walk-forward test |
| 3.5 | Tail hedge overlay (permanent) | 2h | Phase 2 | 3% always allocated, convexity verified |
| 3.6 | Crowding detection system | 2h | Phase 2 | Detects simulated crowding events |
| 3.7 | P&L attribution engine | 2h | Phase 2 | 100% P&L explained per pod per trade |
| 3.8 | Signal decay detector | 2h | Phase 2 | Flags decaying signals before Sharpe drops |
| 3.9 | WebSocket real-time streaming | 2h | Phase 2 | <100ms latency for all dashboard updates |
| 3.10 | Production deployment (Hetzner/Vercel) | 2h | All | System live with monitoring + alerting |

---

## Primitief 5: Evaluation Design

### Test Case 1: Normal Bull Market (Happy Path)
```
Input:
  - VIX: 15, Yield curve: positive, Credit spreads: tight
  - Momentum pod: LONG SPY, conviction 0.8
  - Macro pod: LONG TLT, conviction 0.5
  - Current drawdown: -2%

Expected Output:
  - Regime: BULL (confidence > 0.7)
  - Allocation: Momentum 20%, Macro 20% (normal weights)
  - Portfolio: Long SPY (3-4% position), Long TLT (2% position)
  - Risk: All GREEN, no alerts
  - Execution: TWAP over 2 hours
```

### Test Case 2: Regime Transition (Bear → Crisis)
```
Input:
  - VIX spikes from 25 to 45 in one day
  - Credit spreads widen 200bps
  - All equity pods signal SHORT
  - Current drawdown: -8%

Expected Output:
  - Regime: CRISIS (confidence > 0.8)
  - Allocation shift: Macro TSM → 30%, Tail hedge → 15%, cash → 40%
  - Kill switch: AMBER → RED (drawdown > -5% + VIX > 40)
  - Execution: Accelerated (VWAP 1 hour, market orders for exits)
  - Notification: Webhook + SMS to operator
  - Leverage: Reduced to 0.5x within 4 hours
```

### Test Case 3: Kill Switch BLACK (Edge Case)
```
Input:
  - Portfolio drawdown hits -15.1%
  - Multiple exchanges halted
  - Data feeds intermittent

Expected Output:
  - Kill switch: BLACK — IMMEDIATE
  - All trading HALTED within 1 second
  - Unwind plan generated (3-day timeline)
  - Only T-bill/cash positions after unwind
  - Full log dump + state preservation
  - Human override required to restart
  - Email + SMS + phone call to operator
```

### Test Case 4: Signal Conflict (Integration)
```
Input:
  - Momentum pod: LONG AAPL (conviction 0.9)
  - Mean-Reversion pod: SHORT AAPL (conviction 0.7)
  - AI/ML pod: NEUTRAL AAPL (conviction 0.3)
  - Regime: RANGE_BOUND

Expected Output:
  - Weighted signal: Momentum IC 0.04, Mean-Rev IC 0.06 this month
  - Mean-Rev wins (higher recent IC)
  - Net position: SHORT AAPL, but reduced size (offsetting signals)
  - Position size: 1% max (not full 5%, due to conflict discount)
  - Log: "Signal conflict on AAPL — IC-weighted resolution, size reduced"
```

### Test Case 5: API Security (Boundary)
```
Input:
  - Request to /api/v1/portfolio without API key
  - Request with expired API key
  - Request with valid key but rate limit exceeded
  - SQL injection attempt in query parameter

Expected Output:
  - No key: 401 Unauthorized, "Missing API key"
  - Expired: 401 Unauthorized, "API key expired"
  - Rate limited: 429 Too Many Requests, retry-after header
  - SQL injection: 400 Bad Request, input sanitized, attempt logged
  - NEVER: Database error exposed, actual SQL in response
```

---

## Assemblage — Complete Specification

```
┌─────────────────────────────────────────────────────┐
│              ORACLE SWARM v1.0 SPEC                  │
│                                                      │
│  Pentagon:     01-prompt-craft.md                     │
│  Context:      02-context-engineering.md              │
│  Intent:       03-intent-engineering.md               │
│  Spec:         04-specification-engineering.md (this) │
│                                                      │
│  32 subtasks across 3 phases (12 months)             │
│  10 MUST constraints                                 │
│  10 MUST-NOT constraints                             │
│  10 PREFER guidelines                                │
│  8 ESCALATE triggers                                 │
│  5 evaluation test cases                             │
│                                                      │
│  Acceptance: Sharpe > 1.2 on 6-month live            │
│  Target: Sharpe 1.5-2.0 at steady state              │
│  Kill switch: -15% max drawdown, NEVER exceeded      │
└─────────────────────────────────────────────────────┘
```

---

## Validatie Checklist — Specification Engineering

- [x] Self-contained? → Ja, iemand kan dit uitvoeren zonder vragen
- [x] Acceptance criteria ja/nee verifieerbaar? → Alle AC-F/T/V zijn binair testbaar
- [x] Constraints dekken alle 4 categorieen? → MUST(10), MUST-NOT(10), PREFER(10), ESCALATE(8)
- [x] Subtaken ≤2 uur en onafhankelijk commitbaar? → Alle 32 subtasks ≤2h, dependencies expliciet
- [x] Evaluatie ≥3 testcases met bekende output? → 5 testcases (happy path, regime change, kill switch, conflict, security)
- [x] Pentagon compleet? → Ja, alle 5 atomen
- [x] Intent gelinkt? → Ja, referentie naar 03-intent-engineering.md
- [x] Klarity-check → Optimaliseert voor JUISTE doel: Capital Preservation > Returns > Diversification
