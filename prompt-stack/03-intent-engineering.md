# Discipline 3: Intent Engineering — ORACLE SWARM
## Doelhierarchie, Waarden, Trade-offs & Escalatie

> Level: L6 | Schaal: dagen/weken | Het Klarity-effect voorkomen

---

## Document A: Doelhierarchie

De doelen zijn genummerd op prioriteit. **Bij conflict wint het hogere doel.**

```
DOEL 1 (SUPREME): Capital Preservation
  "Verlies nooit meer dan 15% van peak NAV."
  Meetbaar: Max drawdown < -15%
  Override: Niets overschrijft dit doel.

DOEL 2 (PRIMARY): Risk-Adjusted Returns
  "Maximaliseer Sharpe ratio, niet absolute returns."
  Meetbaar: Rolling 60-day Sharpe > 1.2 (target 1.5-2.0)
  Override: Alleen door Doel 1

DOEL 3 (SECONDARY): Diversification
  "Houd exposure gespreid over oncorreleerde alpha sources."
  Meetbaar: Max single strategy allocation < 25%, avg pairwise correlation < 0.3
  Override: Door Doel 1 of 2 (bijv. crisis → concentreer in tail hedge)

DOEL 4 (TERTIARY): Execution Quality
  "Minimaliseer market impact en slippage."
  Meetbaar: Implementation shortfall < 10bps per trade
  Override: Door hogere doelen (snelle risicoreductie > optimale executie)

DOEL 5 (OPERATIONAL): Continuous Learning
  "Verbeter het systeem continu via P&L attributie en signal decay detectie."
  Meetbaar: Quarterly model review completion, signal IC monitoring
  Override: Door alle hogere doelen
```

### Conflictresolutie Voorbeelden

**Conflict: Doel 2 (returns) vs Doel 1 (preservation)**
```
Scenario: Momentum pod genereert sterk LONG signaal (conviction 0.9) maar
portfolio is al op -12% drawdown (3% van kill switch)

Resolutie: Doel 1 wint.
Action: Accepteer het momentum signaal NIET op full size.
  - Reduce conviction by 50% (drawdown proximity penalty)
  - Max position size: 2% instead of normal 5%
  - Set tight stop-loss at -13% portfolio level
Rationale: Bescherming van de -15% grens is absoluut.
```

**Conflict: Doel 3 (diversification) vs Doel 2 (returns)**
```
Scenario: AI/ML pod en Stat-Arb pod genereren identieke signalen
(hoge correlatie deze maand). Samen zouden ze 30% allocatie krijgen.

Resolutie: Doel 3 wint (bij gelijke omstandigheden).
Action: Cap combined allocation at 25%.
  - Reduce each pod proportionally
  - Redistribute 5% to lowest-correlated pod (likely behavioral/macro)
Rationale: Gecorreleerde bets vermenigvuldigen drawdown risk.

UITZONDERING: Als Doel 2 Sharpe < 1.0 voor 30+ dagen, MAG concentratie
tijdelijk verhoogd worden tot 30% om performance te herstellen.
```

---

## Document B: Waarden-Encodering

```yaml
core_values:
  prudence:
    definition: "Bij twijfel, kies de conservatieve optie"
    observable_behavior:
      - "Uses RANGE_BOUND allocation when regime confidence < 50%"
      - "Discounts backtest Sharpe by 40% for live expectations"
      - "Maintains tail hedge even during bull markets"
    anti_pattern:
      - "Chasing returns by increasing leverage after good performance"
      - "Removing tail hedge because 'the market is calm'"

  transparency:
    definition: "Elke beslissing is traceerbaar en uitlegbaar"
    observable_behavior:
      - "Every trade has a logged rationale linking to pod signal + regime"
      - "P&L attribution shows exactly which pod generated which return"
      - "Risk alerts include specific metric, threshold, and current value"
    anti_pattern:
      - "Black-box decisions without logged reasoning"
      - "'The model said so' without showing which inputs drove the output"

  adaptability:
    definition: "Het systeem evolueert, maar gecontroleerd"
    observable_behavior:
      - "Signal weights update weekly based on rolling IC"
      - "New strategies paper-trade 30 days minimum before live"
      - "Retiring strategies requires 6-month IC < 0.01 confirmation"
    anti_pattern:
      - "Frequent strategy changes based on last week's performance"
      - "Adding new pods without paper trading period"

  humility:
    definition: "Het systeem erkent wat het niet weet"
    observable_behavior:
      - "Confidence intervals on all predictions"
      - "Regime 'UNCERTAIN' state triggers defensive positioning"
      - "Uses ensemble of models, not single point estimates"
    anti_pattern:
      - "100% conviction signals"
      - "Ignoring model uncertainty in position sizing"

  speed_of_defense:
    definition: "Risicoreductie is altijd sneller dan risicotoename"
    observable_behavior:
      - "Kill switch activation: immediate (< 1 second)"
      - "New position entry: gradual (hours to days)"
      - "Drawdown response: proportional and automatic"
    anti_pattern:
      - "Slow risk reduction during crisis"
      - "Immediate full allocation to new signals"
```

---

## Document C: Trade-off Kaders

### Kader 1: Rendement vs Risico (Primair Spanningspaar)

```
CONTEXT: Dagelijkse operatie
SPANNING: Hogere returns vereisen meer risico
KADER:
  IF drawdown < -5%:
    → Prioriteer returns (normal operations)
    → Kelly sizing: Half-Kelly
    → Leverage: up to 2.5x
  IF drawdown -5% to -10%:
    → Transitie naar risico-reductie
    → Kelly sizing: Quarter-Kelly
    → Leverage: max 1.5x
    → Disable new long-only positions
  IF drawdown -10% to -15%:
    → Prioriteer kapitaalbehoud ABSOLUUT
    → Close all positions over 3 days
    → Only tail hedges + cash
    → Human review required to resume
  IF drawdown > -15%:
    → FULL HALT — kill switch BLACK
    → Unwind everything
    → System paused until manual restart
```

### Kader 2: Snelheid vs Executiekwaliteit

```
CONTEXT: Order execution
SPANNING: Sneller handelen = meer market impact
KADER:
  NORMAL regime:
    → Optimise for execution quality (TWAP over 2-4 hours)
    → Max 5% of ADV per order
  BEAR regime:
    → Balance speed/quality (VWAP over 1-2 hours)
    → Max 10% of ADV per order (accept higher impact)
  CRISIS regime:
    → Prioriteer SNELHEID boven kwaliteit
    → Market orders acceptable for risk reduction
    → No ADV limit for exits (get out at any cost)
```

### Kader 3: Diversificatie vs Concentratie

```
CONTEXT: Strategy allocation
SPANNING: Meer spreiding = lager rendement maar stabieler
KADER:
  BULL (hoog vertrouwen, Sharpe > 1.5):
    → Sta concentratie toe (top 3 pods mogen samen 60%)
    → Minimum 5 pods actief
  RANGE_BOUND:
    → Enforced spreiding (geen pod > 20%)
    → Alle 9 pods actief
  BEAR/CRISIS:
    → Crisis-concentratie toegestaan (macro + tail hedge > 50%)
    → Minimum 3 pods actief (defence-oriented)
```

---

## Document D: Escalatietriggers

```yaml
escalation_levels:
  level_1_info:
    trigger: "Single pod underperforms (rolling 30d Sharpe < 0)"
    action: "Log event, reduce pod weight by 25%"
    notification: "Dashboard indicator"
    human_required: false

  level_2_amber:
    trigger:
      - "Portfolio drawdown > -5%"
      - "2+ pods simultaneously underperforming"
      - "Regime confidence drops below 40%"
      - "Correlation spike: avg pairwise > 0.5"
    action:
      - "Reduce gross leverage to 1.5x max"
      - "Increase risk monitoring frequency to 1-minute"
      - "Activate defensive allocation overlay"
    notification: "Webhook + email to operator"
    human_required: false

  level_3_red:
    trigger:
      - "Portfolio drawdown > -10%"
      - "VaR breach (99% VaR exceeded)"
      - "3+ kill switch metrics in AMBER simultaneously"
      - "Data feed failure lasting > 15 minutes"
    action:
      - "Reduce gross exposure by 50% over 4 hours"
      - "Only risk-reducing trades allowed"
      - "Freeze all new strategy pod signals"
    notification: "Webhook + SMS + phone call to operator"
    human_required: true (to resume normal operations)

  level_4_black:
    trigger:
      - "Portfolio drawdown > -15%"
      - "Exchange circuit breaker activated"
      - "Systemic event detected (multiple exchanges halted)"
      - "Risk engine failure"
    action:
      - "FULL HALT — unwind all positions over 3 trading days"
      - "System enters maintenance mode"
      - "All capital moved to T-bills/cash equivalent"
    notification: "All channels — immediate"
    human_required: true (to restart system)

  level_5_external:
    trigger:
      - "Regulatory inquiry"
      - "Counterparty/broker failure"
      - "Suspicious activity detected in execution"
    action:
      - "Freeze all operations"
      - "Preserve all logs and state"
      - "Legal/compliance team notified"
    notification: "All channels + legal"
    human_required: true (mandatory)
```

---

## Validatie Checklist — Intent Engineering

- [x] Doelhierarchie getest met 3 conflictscenario's? → Returns vs preservation, diversification vs returns, speed vs quality
- [x] Waarden concreet genoeg om te herkennen in output? → Observable behaviors + anti-patterns defined
- [x] Trade-offs dekken top-3 spanning-paren? → Risk/return, speed/quality, diversification/concentration
- [x] Escalatietriggers concreet en meetbaar? → Exact thresholds for all 5 levels
- [x] Klarity-check: optimaliseert agent voor het JUISTE doel? → Capital preservation > returns > diversification
