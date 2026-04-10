# AetherTrade-Swarm — Super System Master Plan

> From optimized quant backtest to AI-native trading intelligence
> Based on 2024-2026 research into elite quant funds, LLM trading agents, and agentic AI architectures

---

## Executive Summary

Our current v1.4.0 achieves 33.9% backtest return with 3x leverage but has **zero real alpha** — it merely leverages buy-and-hold SPY. To build a genuine edge we need to do what traditional quant cannot: process unstructured data, adapt to regime shifts in real-time, and combine multiple intelligence streams through agentic reasoning.

**The core insight**: Elite funds like Renaissance win on 50.75% of trades but execute 150,000/day — tiny statistical edges compound. We can't match that volume, but we CAN match their edge quality by using Claude's ability to read context that numerical models miss.

**Target**: Sharpe 2.0+, 20-30% annual return, max 15% drawdown, survives bear markets.

---

## Part 1: What Elite Funds Actually Do

### Renaissance Medallion (66% gross / 39% net annual)
- **Not magic** — they win 50.75% of the time
- **Volume** — 150,000 trades/day compounds tiny edges
- **Signal hunting** — p-value < 0.01 required, multiple out-of-sample tests
- **Statistical arbitrage** — patterns where asset A moves before asset B
- Source: [Quartr analysis](https://quartr.com/insights/edge/renaissance-technologies-and-the-medallion-fund)

### Alternative Data Edge
- Funds using alt-data earned **3% higher annual returns** than traditional-only
- **$2.5 billion** spent on alt-data in 2024, growing 33%/year
- Top sources: satellite imagery, credit card transactions, sentiment, web scraping
- Twitter sentiment can predict moves **6 days in advance with 87% accuracy**
- Source: [ExtractAlpha 2025 report](https://extractalpha.com/2025/07/07/5-best-alternative-data-sources-for-hedge-funds/)

### What this means for us
We can't buy satellite data ($millions/year), but we CAN:
- Scrape sentiment from free sources (Reddit, Twitter, news RSS)
- Read SEC filings with Claude Sonnet (free with our subscription)
- Aggregate macro narratives from news
- Detect regime shifts from qualitative text

---

## Part 2: The AI-Native Edge

### Recent Research Breakthroughs (2024-2026)

**1. FinAgent (KDD 2024)** — [arxiv 2402.18485](https://arxiv.org/abs/2402.18485)
- Multimodal foundation agent: numerical + textual + visual
- **92.27% return** on one dataset (84% improvement over baseline)
- **Dual-level reflection** module for rapid adaptation
- **36% average improvement** across 6 financial metrics
- Diversified memory retrieval system

**2. TradingAgents (2024)** — [arxiv 2412.20138](https://arxiv.org/abs/2412.20138) | [GitHub](https://github.com/TauricResearch/TradingAgents)
- Multi-agent firm simulation
- **Specialized roles**: fundamental/sentiment/technical analysts + bull/bear researchers + risk manager + trader
- **Debate mechanism**: bull vs bear argue, synthesize into decision
- Outperforms baselines on cumulative return, Sharpe, max drawdown

**3. FINCON (NeurIPS 2024)** — Synthesized LLM multi-agent with conceptual verbal reinforcement
- Self-critiquing agents that learn from past trades
- Natural language feedback loops

**4. FinGPT** — [arxiv 2306.06031](https://arxiv.org/html/2306.06031v2)
- **87.62% F1** on financial sentiment analysis
- **95.50% F1** on headline classification
- Open-source, finetuned for finance
- SEC filing analysis built-in

### The "AI-Native Edge" — What an LLM can do that quant cannot

1. **Real-time narrative detection**
   - Read 10,000 news articles/day, extract themes
   - Spot "AI bubble fear" trending before it hits prices
   - Track sentiment shift from positive to neutral in sector rotation

2. **Cross-referencing unstructured data**
   - "NVDA earnings call mentioned supply constraints → check TSMC filings → check ASML → short chain"
   - Connect dots no feature engineer thought of

3. **Adapting without retraining**
   - Classic quant models degrade in new regimes and need re-training
   - An LLM can reason "we're in a new regime because X, Y, Z — adjust strategy"

4. **Generating novel hypotheses**
   - "Oil prices up, Middle East tension, airline stocks haven't reacted yet — short airlines"
   - Hypothesis → backtest → deploy cycle in hours, not months

5. **Natural language explainability**
   - Every trade has a reason a human can read and verify
   - Compliance-friendly, auditable

---

## Part 3: The AetherTrade Super System Architecture

### Core Design: Multi-Agent Trading Firm (inspired by TradingAgents + FINCON)

```
                    ┌──────────────────────┐
                    │   CEO AGENT (Opus)   │
                    │  Strategic Direction │
                    │  Final Decisions     │
                    └──────────┬───────────┘
                               │
         ┌─────────────────────┼─────────────────────┐
         │                     │                     │
    ┌────▼─────┐         ┌────▼─────┐         ┌────▼─────┐
    │ RESEARCH │         │ ANALYSTS │         │   RISK   │
    │  LAYER   │         │  LAYER   │         │  AGENT   │
    └────┬─────┘         └────┬─────┘         └────┬─────┘
         │                    │                    │
    ┌────▼──────────┐    ┌───▼──────────┐    ┌────▼──────┐
    │ News Scout    │    │ Fundamental  │    │ Position  │
    │ Reddit Scout  │    │ Sentiment    │    │ Sizing    │
    │ SEC Reader    │    │ Technical    │    │ VaR       │
    │ Filings Scout │    │ Macro        │    │ Stop Loss │
    │ Macro Scout   │    │              │    │ Kill Swtch│
    └───────────────┘    └──────────────┘    └───────────┘
                               │
                    ┌──────────▼───────────┐
                    │  BULL vs BEAR DEBATE │
                    │    (Opus 4.6)         │
                    │  Synthesis → Decision │
                    └──────────┬───────────┘
                               │
                    ┌──────────▼───────────┐
                    │   EXECUTION AGENT    │
                    │   Alpaca Paper API   │
                    │   Order Management   │
                    └──────────┬───────────┘
                               │
                    ┌──────────▼───────────┐
                    │  LEARNING AGENT      │
                    │  Post-trade review   │
                    │  Self-reflection     │
                    │  Strategy evolution  │
                    └──────────────────────┘
```

### The 12 Agents

#### Research Layer (5 scouts — Haiku, cheap)
1. **News Scout** — Scrapes RSS (Bloomberg, Reuters, FT, CNBC) every 5 min, classifies bullish/bearish/neutral per ticker
2. **Reddit Scout** — Monitors r/wallstreetbets, r/stocks, r/investing for velocity of mentions
3. **SEC Filings Scout** — EDGAR API, reads 8-K (material events), 10-Q quarterly, insider Form 4 buys/sells
4. **Earnings Call Scout** — Parses transcripts for guidance changes, supply chain mentions, CEO tone
5. **Macro Scout** — Fed speeches, ECB statements, CPI releases, FOMC minutes

#### Analyst Layer (4 specialists — Sonnet)
6. **Fundamental Analyst** — Combines filings + earnings + ratios → fair value estimate
7. **Sentiment Analyst** — Aggregates news + Reddit + options flow → sentiment score
8. **Technical Analyst** — Classic TA + chart patterns from price data (our current 9 pods live here)
9. **Macro Analyst** — Regime detection, rate cycles, sector rotation, correlations

#### Decision Layer (2 debaters — Opus)
10. **Bull Researcher** — Builds case FOR each candidate position, cites evidence
11. **Bear Researcher** — Builds case AGAINST, focuses on risks and contrary indicators

#### Risk + Execution (1 each — Sonnet)
12. **Risk Manager** — Position sizing, portfolio VaR, correlation limits, kill switches
13. **Execution Agent** — Order routing, slippage minimization (Alpaca paper first)

#### Learning Layer (background — Opus weekly)
14. **Post-Mortem Agent** — Reviews closed trades, identifies what worked, updates memory
15. **Hypothesis Generator** — Proposes new strategies weekly based on recent market behavior

### Decision Flow (per trading day)

```
08:00 — Research layer wakes up
        ↓
        News/Reddit/SEC/Earnings/Macro scouts gather raw data
        ↓
09:00 — Analysts process raw data into structured signals
        ↓
        (Fundamental/Sentiment/Technical/Macro scores per ticker)
        ↓
09:15 — CEO selects top 20 candidates (highest conviction signals)
        ↓
09:30 — For each candidate: Bull vs Bear debate (3 rounds)
        Each side cites evidence from analyst reports
        Synthesizer picks winner or "no trade"
        ↓
09:45 — Risk Manager reviews proposed positions
        Checks correlation, concentration, VaR
        Final position sizing
        ↓
10:00 — Execution Agent places orders (market open liquidity)
        ↓
16:00 — Post-close review
        ↓
17:00 — Post-Mortem Agent reviews today's decisions
        Updates memory bank
        Tags lessons for future reference
```

---

## Part 4: Data Sources (Free + Cheap)

### Tier 1: Free (immediate)
| Source | Data | API |
|--------|------|-----|
| **yfinance** | OHLCV prices | Python lib |
| **SEC EDGAR** | 10-K, 10-Q, 8-K, Form 4 | Free API |
| **Yahoo Finance News** | News headlines per ticker | Python lib |
| **Reddit API** | r/wsb, r/stocks sentiment | Free tier |
| **FRED** | Macro economic data (Fed) | Free API |
| **Finnhub** | News + basic fundamentals | 60 calls/min free |
| **CoinGecko** | Crypto prices, market cap | Free tier |

### Tier 2: Cheap ($50-100/month)
| Source | Data | Cost |
|--------|------|------|
| **Polygon.io** | Real-time stocks, options | $29/mo |
| **Alpaca** | Paper + live trading + data | Free |
| **Tiingo** | Quality news + crypto | $30/mo |
| **Alpha Vantage** | Forex + commodities | $50/mo |
| **NewsAPI** | 150k articles/day | $50/mo |

### Tier 3: Premium (not yet, $500+/month)
- Bloomberg Terminal ($24k/yr — no)
- Refinitiv Eikon ($22k/yr — no)
- RavenPack sentiment ($$$$ — no)
- Quandl alternative data (varies)

**We start with Tier 1 only. That's enough to prove the edge.**

---

## Part 5: Cost Analysis (Claude API)

### Per trading day:
| Agent | Model | Tokens in | Tokens out | Cost |
|-------|-------|-----------|------------|------|
| 5 Scouts × 10 runs | Haiku | 50k each | 5k each | $0.15 |
| 4 Analysts × 3 runs | Sonnet | 20k each | 5k each | $0.45 |
| CEO selection | Opus | 15k | 3k | $0.35 |
| Bull/Bear debate × 20 | Opus | 10k each | 5k each | $7.00 |
| Risk review | Sonnet | 10k | 3k | $0.08 |
| Post-mortem | Opus | 20k | 5k | $0.50 |
| **Daily total** | | | | **~$8.50** |
| **Monthly** | | | | **~$190** |

**Return needed to break-even**: $190 × 12 = $2,280/year. On $5,000 = 45% annual return. On $50,000 = 4.6% annual return.

**This system only makes sense with $25,000+ capital. For $5,000 it's a demo.**

With a Claude Max subscription, costs drop significantly since most calls go through included quota. **Realistic: $20-50/month incremental API cost on top of Max plan.**

---

## Part 6: The 8-Week Build Plan

### Week 1: Foundation
- [ ] Alpaca paper trading account connected
- [ ] SEC EDGAR API integration
- [ ] Reddit API integration (PRAW)
- [ ] News RSS aggregator
- [ ] FRED macro data fetcher
- [ ] Supabase schema extensions (raw_news, raw_filings, raw_reddit, raw_macro)

### Week 2: Research Layer (5 scouts)
- [ ] NewsAgent (Haiku) with prompt-tuned ticker classification
- [ ] RedditAgent with velocity tracking
- [ ] SECAgent with 8-K material event detection
- [ ] EarningsAgent for transcript parsing (Whisper for audio)
- [ ] MacroAgent for Fed/ECB statement analysis
- [ ] Scheduled cron jobs on Kathedraal (every 5-15 min)

### Week 3: Analyst Layer (4 specialists)
- [ ] FundamentalAnalyst (Sonnet) combining filings + ratios
- [ ] SentimentAnalyst aggregating news + Reddit
- [ ] Keep existing 9 pods as TechnicalAnalyst
- [ ] MacroAnalyst for regime + sector rotation

### Week 4: Decision Layer (Bull/Bear debate)
- [ ] Bull agent prompt with evidence citation
- [ ] Bear agent prompt with risk focus
- [ ] Synthesizer that picks winner or "no trade"
- [ ] CEO agent for final portfolio allocation

### Week 5: Risk + Execution
- [ ] RiskManager (Sonnet) with correlation matrix, VaR
- [ ] ExecutionAgent with Alpaca integration
- [ ] Paper trading live on small universe (10 stocks)
- [ ] Real-time P&L tracking in Supabase

### Week 6: Learning Layer
- [ ] PostMortem agent weekly review
- [ ] Memory bank in Supabase (lessons, patterns, failed hypotheses)
- [ ] HypothesisGenerator proposing new strategies
- [ ] Integration with CORTEX self-learning loop

### Week 7: Walk-Forward Backtesting
- [ ] 2020-2022 (COVID crash + bear) — does it survive?
- [ ] 2022-2023 (rate hikes) — regime shift handled?
- [ ] 2024-2025 (AI bull) — does it capture upside?
- [ ] Honest Sharpe + max DD across all periods
- [ ] Target: Sharpe > 1.5, max DD < 25% in bear

### Week 8: Live Paper Trading
- [ ] Deploy to Kathedraal with cron scheduling
- [ ] Monitor 2 weeks of paper trading
- [ ] Dashboard showing every trade with Bull/Bear reasoning
- [ ] Slack notifications for significant decisions
- [ ] v2.0.0 release

---

## Part 7: Expected Performance (Honest)

### What's realistic:
- **Sharpe 1.5-2.0** (elite for retail, modest for institutional)
- **Annual return 15-25%** (before leverage)
- **With 2x leverage**: 25-40% (but with proper risk mgmt)
- **Max drawdown 15-20%** in bull, 25-35% in bear
- **Win rate 52-58%** (like Renaissance)
- **Survives bear markets** (unlike our current v1.4.0)

### What's NOT realistic:
- Renaissance-level 39% net returns (we don't have their volume)
- Zero drawdown years
- Perfect regime prediction
- Consistent outperformance in all market conditions

### The real value:
1. **Genuine alpha** from alt-data processing (not just leveraged beta)
2. **Explainability** — every trade has natural language reasoning
3. **Auditability** — full decision trail in Supabase
4. **Adaptability** — LLM reasoning beats fixed parameters in regime shifts
5. **Showcase** — proves AetherLink can build institutional-grade AI

---

## Part 8: Risk Mitigation

### Technical risks
- **LLM hallucination** → Mandatory evidence citation, fail on "no source" outputs
- **Prompt injection** (news scraping) → Sandbox, allow-list sources
- **API outages** → Fallback to cached data, graceful degradation
- **Cost overruns** → Daily budget ceiling, auto-halt at 150% of target

### Market risks
- **Black swan events** → 20% max drawdown kill switch (already implemented)
- **Flash crashes** → Circuit breakers, limit orders only (no market)
- **Overfitting** → Walk-forward testing mandatory before deployment
- **Regime shifts** → LLM reasoning layer should catch these; fallback to cash

### Operational risks
- **Key man risk** (Marco) → Full documentation, no hidden knowledge
- **Credential exposure** → Env vars only, never in code
- **Data leakage** → RLS on Supabase, separate paper/live environments
- **Regulatory** → Start paper only, live requires license for managing other people's money

---

## Part 9: What Makes This Different from v1.4.0

| Aspect | v1.4.0 (now) | v2.0.0 (super system) |
|--------|--------------|----------------------|
| **Data sources** | Only price (yfinance) | Price + news + filings + Reddit + macro |
| **Signal generation** | 9 fixed formulas | LLM reasoning over raw data |
| **Regime detection** | HMM on returns | HMM + LLM narrative analysis |
| **Decision making** | Weighted ensemble | Bull/bear debate + CEO synthesis |
| **Adaptation** | Static parameters | Self-learning memory bank |
| **Explainability** | Numerical only | Full natural language trail |
| **Edge source** | Leverage | Information asymmetry + reasoning |
| **Bear market survival** | Untested (likely fails) | Tested across 2020, 2022 |
| **Expected Sharpe** | 1.28 (backtest) | 1.5-2.0 (target) |
| **Architectural depth** | ~5K LOC | ~20K LOC (estimated) |

---

## Part 10: First Concrete Next Step

**Build the NewsScout MVP** — proves the concept in 2 days:

```python
# backend/agents/news_scout.py
1. Fetch RSS from Bloomberg, Reuters, CNBC every 15 min
2. For each article, extract tickers mentioned
3. Send to Haiku: "Is this article bullish/bearish/neutral for [ticker]?"
4. Store sentiment in Supabase with timestamp
5. Aggregate by ticker: rolling 24h sentiment score
6. Compare sentiment trajectory to price movement
7. Measure: does sentiment lead price? by how many hours?
```

If this single agent can show a **predictive lead of 4+ hours on 60%+ of moves**, we have the seed of an edge. If not, we learn fast and pivot.

**This is testable in 48 hours and tells us if the whole plan is worth executing.**

---

## Sources

- [TradingAgents GitHub](https://github.com/TauricResearch/TradingAgents)
- [FinAgent Paper (arxiv)](https://arxiv.org/abs/2402.18485)
- [TradingAgents Paper (arxiv)](https://arxiv.org/abs/2412.20138)
- [Renaissance Medallion Breakdown](https://quartr.com/insights/edge/renaissance-technologies-and-the-medallion-fund)
- [Alternative Data Survey 2025](https://extractalpha.com/2025/07/07/5-best-alternative-data-sources-for-hedge-funds/)
- [FinGPT Paper](https://arxiv.org/html/2306.06031v2)
- [FinGPT + Claude 3.7 Tutorial](https://towardsai.net/p/l/building-financial-reports-with-fingpt-and-claude-3-7-sonnet)

---

**Bottom line**: We can build a genuine AI trading edge by leveraging Claude's ability to process information that traditional quants ignore. The plan is ambitious but achievable in 8 weeks. The key is to start with ONE scout agent that proves the concept, then expand only if the alpha is real.
