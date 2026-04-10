# AetherTrade-Swarm v2.0 — Definitief Actieplan

> Consolidatie van 2 OSINT onderzoeksrapporten + directe web research
> Datum: 10 april 2026

---

## De 3 meest impactvolle inzichten uit het onderzoek

### 1. De architectuur is opgelost — forken niet uitvinden
4 papers (FinMem, FinAgent, FinCon, TradingAgents) convergeren op exact dezelfde 5-lagen architectuur:
```
Data Ingestion → Analyst Agents → Debate/Research Team → Risk Agents → Execution + Memory
```
**TradingAgents** (Tauric Research) implementeert dit al in LangGraph met Claude native support. We forken en passen aan.

### 2. Claude Sonnet 4.6 is de beste keuze
Vals.ai benchmark: **Sonnet 4.6 = 63,3% SOTA** op finance analyst tasks, hoger dan Opus 4.6 en GPT-5.2. Sonnet is óók 5x goedkoper dan Opus. Default: Sonnet voor alles, Opus alleen voor de debate synthesizer.

### 3. De edge is kwalitatief, niet kwantitatief
LLMs verliezen van quants op HFT, statistical arbitrage, factor models. LLMs winnen op:
- Real-time narrative detection
- Cross-referencing ongestructureerde data
- Adaptatie zonder retraining
- Novel hypothesis generation uit nieuws
- Multimodale ingestie (chart PNG lezen)
- Long-tail bronnen (messy text die quants negeren)

**Vecht niet op hun terrein. Speel op grond die zij altijd genegeerd hebben.**

---

## Realistisch vs fantasie

| | Realistisch | Fantasie |
|---|---|---|
| Sharpe | 1,0-1,5 (retail ceiling) | 2,0+ (institutional only) |
| Annual return | 10-20% | 30%+ consistent |
| Edge source | Info asymmetrie op niche data | Superieure voorspelling |
| Capital | $100K+ break-even | $5K Medallion returns |
| Timeline | 6 weken MVP | "Werkt morgen" |
| Business model | **SaaS research product** | Eigen P&L trading |

**Mijn advies blijft staan: bouw SaaS, niet trading.**

---

## De drie product-paths (kies er EEN om mee te beginnen)

### Path A: Insider Cluster Detector (eenvoudigst, snelst)
**Tijdslijn**: 2-3 dagen
**Gedocumenteerd alpha**: 22-32% annualized (SEC Form 4 cluster buys)
**Data**: Volledig gratis (SEC EDGAR)
**Tech**: Python + Supabase + dagelijkse cron

**Wat het doet**:
- Haalt dagelijks alle Form 4 filings op (insider trades)
- Filtert op: 3+ unieke insiders bij hetzelfde bedrijf binnen 10 dagen, transaction code P (open market buy), > $25K per trade
- Genereert dagelijkse "cluster buy signal" feed
- Backtest: bekende academisch gedocumenteerde alpha

**Go-to-market**:
- API: €49/mo basic, €149/mo pro (webhooks, real-time)
- Simple landingspagina: "Trade alongside insider cluster buys"
- Target: solo traders, small RIAs
- **Break-even bij 15 klanten × €49 = €735 MRR**

### Path B: LLM 10-K/10-Q Analyzer (midden, grootste markt)
**Tijdslijn**: 1 week
**Gedocumenteerd alpha**: Filing-derived NLP signals → Sharpe ~1,5
**Data**: Gratis (SEC EDGAR) + Claude Sonnet ($0,30-1,50 per filing met caching)
**Tech**: Python + Supabase pgvector + Claude API + RAG

**Wat het doet**:
- Ingest van elke nieuwe 10-K, 10-Q, 8-K van beursgenoteerde bedrijven
- Claude Sonnet 4.6 extraheert: material risks, forward guidance, unusual items, management tone
- Structured output → Supabase
- Change-detection: wat is anders dan vorig kwartaal?
- Dashboard: "Today's most concerning filings" / "Biggest guidance upgrades"

**Go-to-market**:
- SaaS: €99/mo individual, €299/mo team, €999/mo enterprise
- Verkoop aan: equity research analisten, family offices, PE due diligence teams
- Content marketing: wekelijkse "Top 10 filings deze week" nieuwsbrief
- **Break-even bij 10 klanten × €99 = €990 MRR**

### Path C: Multi-Agent Research Pipeline (meest ambitieus)
**Tijdslijn**: 6-8 weken
**Tech**: Fork TradingAgents + 5 custom data sources + Supabase memory
**Kosten**: $5-15/dag operationeel
**Waarde**: Institutioneel-grade research voor retail prijzen

**Wat het doet**:
- Volledig multi-agent systeem (12 agents zoals in master plan)
- Bull/Bear debate voor elk signaal
- Memory bank met FinCon CVRF pattern
- Paper trading + publieke track record
- Transparante beslissingsketen (elke trade heeft reasoning)

**Go-to-market**:
- "Bloomberg voor de 99%": €499-1499/mo
- Target: family offices, sophisticated retail, small funds
- Demo: paper trading track record op onze website
- **Break-even bij 5 klanten × €499 = €2.495 MRR**

---

## Mijn sterke aanbeveling: Path A → B → C (in die volgorde)

### Waarom Path A eerst?

1. **Snelst te bouwen** (2-3 dagen)
2. **Gratis data** (geen API kosten)
3. **Bewezen alpha** (academisch gedocumenteerd 22-32%)
4. **Concreet product** (geen LLM hype nodig)
5. **Simpele pricing** (€49-149 toegankelijk)
6. **Valideert markt**: als we geen 15 klanten kunnen vinden voor iets met bewezen alpha tegen €49, dan is de markt er niet voor complexere producten
7. **Financiert Path B**: MRR uit A betaalt de ontwikkeling van B

### Dan pas Path B?

Na 1-2 maanden MRR uit Path A hebben we validatie dat:
- De markt betaalt voor signals
- Ons kanaal werkt
- De infrastructuur (Supabase, Kathedraal) schaalt
- We begrijpen customer support overhead

**Dán bouwen we Path B** als upsell naar bestaande klanten + nieuwe acquisitie.

### Path C alleen als A+B werken

Path C is de "premium tier" die alleen logisch is als we al bewezen hebben dat mensen betalen voor onze signal quality.

---

## Concrete eerste 7 dagen (Path A)

### Dag 1: Data pipeline
- [ ] SEC EDGAR Form 4 bulk fetcher (Python)
- [ ] Daily cron job op Kathedraal
- [ ] Supabase `insider_trades` tabel met schema
- [ ] Backfill laatste 6 maanden data

### Dag 2: Cluster detector
- [ ] Algoritme: 3+ insiders, code P, 10-day window, $25K+
- [ ] Historische backtest op 2020-2025 (bevestig 22-32% alpha)
- [ ] Top-10 "hot" clusters view in Supabase
- [ ] Daily digest email template

### Dag 3: Signal API
- [ ] FastAPI endpoints op Kathedraal :8889
  - `GET /signals/clusters/today`
  - `GET /signals/clusters/hot` (top 10 current)
  - `GET /signals/backtest/{cluster_id}`
  - `POST /webhooks/subscribe`
- [ ] API key auth + rate limiting (Supabase)
- [ ] Swagger docs

### Dag 4: Landing page
- [ ] Next.js page: aethertrade.aetherlink.ai/insider-signals
- [ ] Value proposition + backtested equity curve
- [ ] Pricing tabel (€49/€149)
- [ ] Stripe checkout integration
- [ ] Email capture voor early access

### Dag 5: Backtest showcase
- [ ] Publieke backtest dashboard met equity curve
- [ ] "Trades van vandaag" live feed (beperkte gratis versie)
- [ ] Case studies: 3 concrete winning trades met timeline
- [ ] SEO content: "Best insider trading signals 2026"

### Dag 6: Email marketing setup
- [ ] Beehiiv/ConvertKit newsletter setup
- [ ] Welkomst autoresponder (5 emails over insider alpha)
- [ ] Wekelijkse cluster digest template
- [ ] Landing page integration

### Dag 7: Launch
- [ ] Product Hunt submit
- [ ] HackerNews "Show HN"
- [ ] X/Twitter thread met backtest results
- [ ] Reddit r/algotrading, r/stocks, r/investing posts
- [ ] LinkedIn post naar Marco's netwerk
- [ ] Monitor en support eerste klanten

**KPI na 7 dagen**: 100+ landing page visitors, 20+ email signups, eerste 3 betalende klanten.
**KPI na 30 dagen**: 15+ betalende klanten, €735+ MRR, break-even operationeel.

---

## Wat ik NIET meer aanbeveel

- ❌ Ons v1.4.0 backtest als bewijs gebruiken (33,9% is survivorship bias op 1 jaar bull)
- ❌ $5K met 3x leverage live traden (Alpha Arena 2025 bewees: LLMs verliezen live geld)
- ❌ Eerst een "super systeem" bouwen voordat er 1 klant is
- ❌ Competen met Citadel op hun sterke punten
- ❌ De 9 huidige pods weggooien (ze worden fallback signals + technical analyst tools)

## Wat ik WEL aanbeveel

- ✅ Start met Path A: gratis data + bewezen alpha + laagste risico
- ✅ Hergebruik bestaande infrastructure (Supabase, Kathedraal, auth)
- ✅ MRR vóór perfectie — ship iets imperfects en verbeter met klant feedback
- ✅ Honest marketing: "22-32% historical alpha" met disclaimers, geen "get rich quick"
- ✅ Bouw Path B+C alleen als Path A economisch werkt

---

## Beslismoment voor Marco

Kies één:

**Optie 1**: Ik begin vandaag met Path A (Insider Cluster Detector). Over 7 dagen hebben we een launched SaaS product met eerste klanten of concrete feedback waarom niet.

**Optie 2**: We skippen naar Path B of C (ambitieuzer maar risicovoller qua timing + budget).

**Optie 3**: We doen helemaal niks met trading en gebruiken v1.4.0 alleen als showcase voor AetherLink's AI capabilities.

Mijn sterke voorkeur: **Optie 1**. Laagste risico, snelste validatie, gebruikt bestaande infrastructuur, en bewijst of er markt is voordat we grote investeringen doen.

---

## Bronnen (alle geverifieerd)

### Academic papers
- [TradingAgents (arxiv 2412.20138)](https://arxiv.org/abs/2412.20138) — [GitHub](https://github.com/TauricResearch/TradingAgents)
- [FinAgent (arxiv 2402.18485)](https://arxiv.org/abs/2402.18485)
- [FinCon (NeurIPS 2024)](https://arxiv.org/abs/2407.06567)
- [FinMem (arxiv 2311.13743)](https://arxiv.org/abs/2311.13743)
- [MarketSenseAI 2.0 (arxiv 2502.00415)](https://arxiv.org/abs/2502.00415)
- [FinGPT (arxiv 2306.06031)](https://arxiv.org/html/2306.06031v2)
- [LLM Agent Survey (arxiv 2510.05533)](https://arxiv.org/html/2510.05533v1)
- [TradeTrap reliability study (arxiv 2512.02261)](https://arxiv.org/html/2512.02261v1)

### Claude-specifiek
- [Vals.ai Finance Agent v1.1 benchmark](https://www.vals.ai/benchmarks/finance_agent)
- [Claude for Financial Services](https://www.anthropic.com/news/claude-for-financial-services)
- [EDGAR to Structured DB with Claude](https://paulgp.substack.com/p/from-edgar-filings-to-a-structured)

### Edge validation
- [Insider cluster alpha 22-32%](https://alphaarchitect.com/a-unique-insider-trading-signal-that-generates-alpha/)
- [Renaissance Medallion analysis](https://quartr.com/insights/edge/renaissance-technologies-and-the-medallion-fund)
- [Alt-data 2025 survey](https://extractalpha.com/2025/07/07/5-best-alternative-data-sources-for-hedge-funds/)

### Reality check
- [Why 90% of Backtests Fail](https://financial-hacker.com/why-90-of-backtests-fail/)
- [FailSafeQA LLM finance benchmark](https://ajithp.com/2025/02/15/failsafeqa-evaluating-ai-hallucinations-robustness-and-compliance-in-financial-llms/)

### Reference implementations
- [TradingAgents GitHub](https://github.com/TauricResearch/TradingAgents)
- [FinMem GitHub](https://github.com/pipiku915/FinMem-LLM-StockTrading)
- [LLMAlpha GitHub](https://github.com/JiangZhihao123/llmalpha)
- [PrimoAgent GitHub](https://github.com/ivebotunac/PrimoAgent)
- [NLP-10K-10Q Research](https://github.com/calebyung/NLP-10-K-10-Q-Alpha-Research)

### Hedge fund reality
- [Balyasny BAM Embeddings](https://www.efinancialcareers.com/news/balyasny-s-arcane-new-llm-enhancer-is-outperforming-open-ai)
- [How hedge funds are using AI](https://resonanzcapital.com/insights/ai-use-by-hedge-funds-made-tangible-from-lego-bots-to-alpha-assistants)
