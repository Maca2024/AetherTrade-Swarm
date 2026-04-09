# Discipline 2: Context Engineering — ORACLE SWARM
## 6 Context Layers voor de AI Orchestration Engine

> Level: L5-L7 | Schaal: uren/dagen | Pentagon mapping per laag

---

## Context Audit — 6 Lagen

### Laag 1: System Prompt → ROLE + CONTEXT

```markdown
# ORACLE SWARM — AI Orchestration Engine v1.0

You are ORACLE, the central intelligence of a multi-strategy AI trading platform.
You operate 9 strategy pods simultaneously, each generating independent signals.
Your job is to combine these signals optimally based on market regime.

## Your Identity
- Name: ORACLE (Optimized Risk-Adjusted Capital Logic Engine)
- Role: Portfolio Strategist + Risk Manager + Signal Combiner
- Authority: Full autonomous allocation within risk budget
- Escalation: Human operator for kill switch overrides and new strategy deployment

## Operating Parameters
- Target Sharpe: 1.5-2.0 (annualized)
- Max Drawdown Budget: -15% from peak
- Gross Leverage Limit: 3.0x
- Portfolio Volatility Target: 8-12% annualized
- Minimum Tail Hedge: 3% of NAV (never reduce below this)
- Rebalance Frequency: Daily (macro), Hourly (tactical), Continuous (risk)
```

### Laag 2: MCP Tool Definities → PROCESS

```yaml
tools:
  # DATA LAYER
  - name: market_data_fetch
    description: "Fetch real-time and historical market data (prices, volumes, order books)"
    parameters: {symbols: list[str], timeframe: str, lookback: int}

  - name: fundamental_data_fetch
    description: "Fetch fundamental data (earnings, financials, SEC filings)"
    parameters: {symbols: list[str], data_type: str}

  - name: sentiment_analyzer
    description: "Run NLP sentiment analysis on news/social media/earnings calls"
    parameters: {sources: list[str], lookback_hours: int}

  # SIGNAL LAYER
  - name: strategy_pod_signal
    description: "Get current signal from a specific strategy pod"
    parameters: {pod_name: str}
    returns: {asset: str, direction: str, conviction: float, horizon: str}

  - name: regime_detect
    description: "Run regime detection model on current market state"
    parameters: {indicators: dict}
    returns: {state: str, confidence: float, transition_matrix: dict}

  - name: signal_combine
    description: "Ensemble multiple pod signals into unified portfolio view"
    parameters: {signals: list[dict], weights: dict, regime: str}

  # PORTFOLIO LAYER
  - name: portfolio_optimize
    description: "Run Black-Litterman optimization with current views"
    parameters: {views: dict, uncertainty: dict, constraints: dict}

  - name: position_size
    description: "Calculate position sizes using Half-Kelly criterion"
    parameters: {expected_returns: dict, covariance: dict, max_position: float}

  # EXECUTION LAYER
  - name: execute_trades
    description: "Send orders to execution engine (IBKR/Alpaca)"
    parameters: {orders: list[dict], urgency: str, algo: str}

  - name: execution_report
    description: "Get fill quality report (slippage, market impact)"
    parameters: {order_ids: list[str]}

  # RISK LAYER
  - name: risk_dashboard
    description: "Get current 8-metric risk dashboard"
    parameters: {}
    returns: {var_99: float, cvar_99: float, max_dd: float, sharpe_60d: float, ...}

  - name: kill_switch
    description: "Activate kill switch at specified level"
    parameters: {level: str, reason: str}  # AMBER, RED, BLACK

  - name: correlation_matrix
    description: "Get current 9x9 strategy correlation matrix"
    parameters: {lookback_days: int}

  # LEARNING LAYER
  - name: pnl_attribution
    description: "Get P&L attribution per strategy pod per period"
    parameters: {period: str}

  - name: signal_decay_check
    description: "Check information coefficient decay for all pod signals"
    parameters: {lookback_days: int, threshold: float}
```

### Laag 3: RAG Documents → CONTEXT

```yaml
rag_documents:
  always_loaded:
    - path: "research/strategy-rankings.md"
      description: "30 strategies ranked across 10 domains with performance data"
      update_frequency: monthly

    - path: "research/correlation-matrix.md"
      description: "9x9 strategy domain correlation matrix (estimated)"
      update_frequency: weekly

    - path: "config/regime-allocation-table.md"
      description: "Regime-conditional strategy allocation weights"
      update_frequency: monthly

  loaded_on_demand:
    - path: "research/agent-{1-10}-reports/"
      description: "Deep-dive reports per strategy domain"
      trigger: "When evaluating or modifying a specific strategy pod"

    - path: "research/academic-papers/"
      description: "Key academic references (Fama-French, Avellaneda, Moskowitz)"
      trigger: "When justifying a strategy decision"

    - path: "logs/pnl-attribution/"
      description: "Historical P&L attribution data"
      trigger: "During learning cycle or strategy review"
```

### Laag 4: Conversatiegeschiedenis → CONTEXT + GOAL

```yaml
conversation_management:
  retention_policy:
    - last_24h: full_detail  # All signals, trades, risk events
    - last_7d: summary       # Daily summaries with key decisions
    - last_30d: highlights   # Only regime changes, kill switches, major trades
    - older: compressed      # P&L and regime history only

  critical_events_always_retained:
    - kill_switch_activations
    - regime_transitions
    - strategy_pod_additions_removals
    - max_drawdown_events
    - human_operator_overrides

  context_budget:
    - max_tokens_per_cycle: 50000
    - reserve_for_tools: 20000
    - reserve_for_reasoning: 20000
    - reserve_for_output: 10000
```

### Laag 5: Memory Systems → ROLE + CONTEXT

```yaml
memory_systems:
  short_term:  # In-session
    type: "conversation_buffer"
    contents: ["current_positions", "pending_orders", "active_alerts", "intraday_pnl"]
    ttl: "end_of_session"

  medium_term:  # Cross-session
    type: "supabase_table"
    table: "oracle_memory"
    contents:
      - "regime_transition_log"         # When and why regimes changed
      - "strategy_performance_30d"      # Rolling 30-day pod performance
      - "signal_decay_observations"     # Which signals are degrading
      - "execution_quality_log"         # Fill quality by venue/algo
      - "risk_event_log"               # All risk threshold breaches
    ttl: "90_days"

  long_term:  # Persistent knowledge
    type: "supabase_table + vector_store"
    table: "oracle_knowledge"
    contents:
      - "strategy_lifecycle_data"       # Which strategies added/removed and why
      - "market_regime_history"         # Full regime classification history
      - "lessons_learned"              # Post-mortem from drawdown events
      - "parameter_tuning_history"     # When and why parameters changed
    ttl: "permanent"
```

### Laag 6: MCP als Live Context → PROCESS + FORMAT

```yaml
live_context_feeds:
  market_data:
    source: "polygon_websocket"
    format: "streaming_json"
    latency: "<100ms"
    contents: ["price", "volume", "bid_ask", "trades"]

  regime_indicators:
    source: "computed_realtime"
    format: "json"
    update_frequency: "1_minute"
    contents:
      vix: "CBOE VIX index"
      yield_curve: "10Y-2Y spread"
      credit_spread: "HY-IG spread"
      momentum_dispersion: "Cross-sectional momentum factor spread"
      correlation_level: "Average pairwise equity correlation"

  pod_signals:
    source: "9_strategy_pods"
    format: "standardized_signal_json"
    update_frequency: "pod_dependent"  # 1s to 1h depending on pod

  risk_metrics:
    source: "risk_engine"
    format: "8_metric_dashboard_json"
    update_frequency: "1_minute"
```

---

## Validatie Checklist — Context Engineering

- [x] Agent begrijpt project zonder extra uitleg? → System prompt is self-contained
- [x] Agent kiest juiste tools zonder sturing? → Tool descriptions are specific and non-overlapping
- [x] Kwaliteit stabiel na 50K+ tokens? → Conversation management with compression policy
- [x] Nieuwe sessie start productief? → Memory systems bridge sessions
- [x] Alleen relevante context geladen? → RAG with on-demand loading, not everything at once
