// Simulated trading data generator for AETHERTRADE-SWARM

export type Regime = 'bull' | 'bear' | 'crisis' | 'range'

export interface RegimeState {
  type: Regime
  label: string
  confidence: number
  color: string
  bgColor: string
  description: string
}

export interface StrategyPod {
  id: string
  name: string
  shortName: string
  allocation: number
  signal: number // -1 to 1
  signalStrength: number // 0 to 100
  pnl: number
  sharpe: number
  sparkline: number[]
  color: string
  glowColor: string
  description: string
  regime: Regime[]
}

export interface EquityPoint {
  date: string
  oracle: number
  sp500: number
  balanced: number
  drawdown: number
}

export interface MetricCard {
  label: string
  value: string
  change: string
  positive: boolean
  suffix?: string
}

export interface RiskMetric {
  label: string
  value: number
  max: number
  unit: string
  status: 'green' | 'amber' | 'red'
  color: string
}

export interface ArchitectureLayer {
  id: number
  name: string
  subtitle: string
  description: string
  color: string
  icon: string
  metrics: string[]
}

// Seeded pseudo-random for deterministic "live" data
let seed = 42
function seededRandom(): number {
  seed = (seed * 1664525 + 1013904223) & 0xffffffff
  return (seed >>> 0) / 0xffffffff
}

function resetSeed(s = 42): void {
  seed = s
}

export function generateSparkline(length = 20, volatility = 0.015, trend = 0.002): number[] {
  const points: number[] = []
  let value = 100
  for (let i = 0; i < length; i++) {
    const change = (seededRandom() - 0.5) * 2 * volatility + trend
    value = value * (1 + change)
    points.push(parseFloat(value.toFixed(2)))
  }
  return points
}

export function generateEquityCurve(days = 365): EquityPoint[] {
  resetSeed(1337)
  const points: EquityPoint[] = []
  let oracle = 10000
  let sp500 = 10000
  let balanced = 10000

  const startDate = new Date('2023-01-01')

  for (let i = 0; i < days; i++) {
    const date = new Date(startDate)
    date.setDate(startDate.getDate() + i)

    // Oracle: higher Sharpe, controlled drawdown
    const oracleReturn = (seededRandom() - 0.46) * 0.018 + 0.0006
    // S&P 500: noisier, higher drawdowns
    const spReturn = (seededRandom() - 0.48) * 0.022 + 0.0004
    // 60/40: smoothed
    const balReturn = (seededRandom() - 0.48) * 0.012 + 0.0003

    oracle = oracle * (1 + oracleReturn)
    sp500 = sp500 * (1 + spReturn)
    balanced = balanced * (1 + balReturn)

    points.push({
      date: date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
      oracle: parseFloat(oracle.toFixed(2)),
      sp500: parseFloat(sp500.toFixed(2)),
      balanced: parseFloat(balanced.toFixed(2)),
      drawdown: parseFloat(((oracle / Math.max(...points.map(p => p.oracle), oracle) - 1) * 100).toFixed(2)),
    })
  }
  return points
}

export const REGIMES: RegimeState[] = [
  {
    type: 'bull',
    label: 'BULL MARKET',
    confidence: 78,
    color: '#00FF94',
    bgColor: 'rgba(0, 255, 148, 0.08)',
    description: 'Risk-on momentum regime detected. Trend-following strategies overweight.',
  },
  {
    type: 'bear',
    label: 'BEAR MARKET',
    confidence: 84,
    color: '#FF3366',
    bgColor: 'rgba(255, 51, 102, 0.08)',
    description: 'Defensive posture active. Short bias, mean-reversion and volatility pods elevated.',
  },
  {
    type: 'crisis',
    label: 'CRISIS MODE',
    confidence: 91,
    color: '#FFB800',
    bgColor: 'rgba(255, 184, 0, 0.08)',
    description: 'Tail-risk event detected. Kill switches active. Capital preservation priority.',
  },
  {
    type: 'range',
    label: 'RANGE-BOUND',
    confidence: 67,
    color: '#00D4FF',
    bgColor: 'rgba(0, 212, 255, 0.08)',
    description: 'Low directional bias. Mean-reversion and stat-arb strategies optimal.',
  },
]

export const STRATEGY_PODS: StrategyPod[] = [
  {
    id: 'momentum',
    name: 'Momentum Alpha',
    shortName: 'MOM',
    allocation: 18.4,
    signal: 0.72,
    signalStrength: 86,
    pnl: 24.3,
    sharpe: 2.14,
    sparkline: [98, 99.2, 101, 100.4, 102, 103.8, 103.1, 105, 107.2, 106.8, 109, 111, 110.4, 112, 114.2],
    color: '#00D4FF',
    glowColor: 'rgba(0, 212, 255, 0.3)',
    description: 'Cross-asset trend following across equities, FX, and commodities using adaptive momentum signals.',
    regime: ['bull'],
  },
  {
    id: 'mean-rev',
    name: 'Mean Reversion',
    shortName: 'MR',
    allocation: 14.2,
    signal: -0.31,
    signalStrength: 63,
    pnl: 11.7,
    sharpe: 1.89,
    sparkline: [100, 101.4, 100.2, 102, 101.1, 103, 102.4, 104, 103.2, 105, 104.4, 106, 105.8, 107, 108],
    color: '#8B5CF6',
    glowColor: 'rgba(139, 92, 246, 0.3)',
    description: 'Statistical mean reversion on equity pairs and ETFs with dynamic z-score thresholds.',
    regime: ['range', 'bear'],
  },
  {
    id: 'macro',
    name: 'Global Macro',
    shortName: 'GMC',
    allocation: 15.8,
    signal: 0.54,
    signalStrength: 77,
    pnl: 18.9,
    sharpe: 1.76,
    sparkline: [100, 98, 101, 102.4, 101.8, 104, 103.2, 106, 105.4, 108, 107.6, 110, 109.8, 112, 113.4],
    color: '#FFB800',
    glowColor: 'rgba(255, 184, 0, 0.3)',
    description: 'Macro regime-driven positioning across rates, FX, and commodities with geopolitical overlay.',
    regime: ['bull', 'bear', 'crisis'],
  },
  {
    id: 'stat-arb',
    name: 'Stat Arbitrage',
    shortName: 'SA',
    allocation: 11.6,
    signal: 0.12,
    signalStrength: 54,
    pnl: 8.4,
    sharpe: 2.31,
    sparkline: [100, 100.8, 101.4, 100.9, 101.8, 102.6, 102.1, 103.4, 103.0, 104.2, 103.8, 105, 104.6, 106, 106.8],
    color: '#00FF94',
    glowColor: 'rgba(0, 255, 148, 0.3)',
    description: 'High-frequency statistical arbitrage on correlated equity pairs with ML-driven pair selection.',
    regime: ['range', 'bull'],
  },
  {
    id: 'options-vol',
    name: 'Options / Vol',
    shortName: 'VOL',
    allocation: 9.3,
    signal: -0.67,
    signalStrength: 83,
    pnl: 31.2,
    sharpe: 1.94,
    sparkline: [100, 102, 101, 103.5, 102.8, 105, 104.2, 107, 106.4, 109, 108.6, 112, 111.4, 114, 116],
    color: '#FF3366',
    glowColor: 'rgba(255, 51, 102, 0.3)',
    description: 'Volatility surface arbitrage and options market-making with dynamic delta hedging.',
    regime: ['crisis', 'bear'],
  },
  {
    id: 'behavioral',
    name: 'Behavioral Alpha',
    shortName: 'BEH',
    allocation: 7.9,
    signal: 0.44,
    signalStrength: 69,
    pnl: 14.1,
    sharpe: 1.67,
    sparkline: [100, 100.6, 101.8, 101.2, 102.4, 103, 102.6, 104, 103.4, 105.2, 104.8, 106.4, 106, 107.8, 109],
    color: '#F97316',
    glowColor: 'rgba(249, 115, 22, 0.3)',
    description: 'Exploits systematic behavioral biases and sentiment anomalies using NLP and social signals.',
    regime: ['bull', 'range'],
  },
  {
    id: 'ai-ml',
    name: 'AI / ML Alpha',
    shortName: 'AI',
    allocation: 12.1,
    signal: 0.88,
    signalStrength: 94,
    pnl: 28.7,
    sharpe: 2.48,
    sparkline: [100, 101.8, 103, 102.4, 104.8, 106, 105.2, 108, 107.4, 110.6, 110, 113, 112.4, 116, 118.8],
    color: '#06B6D4',
    glowColor: 'rgba(6, 182, 212, 0.3)',
    description: 'Ensemble deep learning models with attention mechanisms trained on alternative data streams.',
    regime: ['bull', 'range', 'bear'],
  },
  {
    id: 'multi-factor',
    name: 'Multi-Factor',
    shortName: 'MF',
    allocation: 6.4,
    signal: 0.28,
    signalStrength: 61,
    pnl: 9.8,
    sharpe: 1.82,
    sparkline: [100, 100.4, 101.2, 100.8, 102, 102.8, 102.4, 103.6, 103.2, 104.8, 104.4, 105.6, 105.2, 107, 108],
    color: '#A78BFA',
    glowColor: 'rgba(167, 139, 250, 0.3)',
    description: 'Factor exposure optimization across value, quality, momentum, and low-volatility with dynamic rebalancing.',
    regime: ['bull', 'range'],
  },
  {
    id: 'market-making',
    name: 'Market Making',
    shortName: 'MM',
    allocation: 4.3,
    signal: 0.03,
    signalStrength: 41,
    pnl: 6.2,
    sharpe: 3.12,
    sparkline: [100, 100.2, 100.6, 100.4, 101, 101.4, 101.2, 101.8, 101.6, 102.2, 102, 102.6, 102.4, 103, 103.4],
    color: '#34D399',
    glowColor: 'rgba(52, 211, 153, 0.3)',
    description: 'High-frequency market making with inventory management and adverse selection controls.',
    regime: ['range', 'bull', 'bear'],
  },
]

export const PERFORMANCE_METRICS: MetricCard[] = [
  { label: 'Total Return', value: '+187.4%', change: '+24.3% YTD', positive: true },
  { label: 'Sharpe Ratio', value: '1.87', change: '+0.12 vs prior yr', positive: true },
  { label: 'Max Drawdown', value: '-8.3%', change: '-2.1% improvement', positive: true },
  { label: 'Win Rate', value: '64.7%', change: '+1.2% this quarter', positive: true },
  { label: 'Alpha (ann.)', value: '+11.4%', change: 'vs S&P 500', positive: true },
  { label: 'Sortino Ratio', value: '2.31', change: '+0.18 vs benchmark', positive: true },
]

export const RISK_METRICS: RiskMetric[] = [
  { label: 'Value at Risk (95%)', value: 1.42, max: 3.0, unit: '%', status: 'green', color: '#00FF94' },
  { label: 'CVaR (99%)', value: 2.18, max: 5.0, unit: '%', status: 'green', color: '#00FF94' },
  { label: 'Current Drawdown', value: 3.7, max: 15.0, unit: '%', status: 'green', color: '#00FF94' },
  { label: 'Leverage Ratio', value: 1.8, max: 4.0, unit: 'x', status: 'green', color: '#00FF94' },
  { label: 'Correlation Risk', value: 62, max: 100, unit: '%', status: 'amber', color: '#FFB800' },
  { label: 'Liquidity Score', value: 87, max: 100, unit: '%', status: 'green', color: '#00FF94' },
]

export const KILL_SWITCHES = [
  { label: 'Portfolio VaR Limit', status: 'green', threshold: '3.0%', current: '1.42%' },
  { label: 'Drawdown Circuit Breaker', status: 'green', threshold: '-15%', current: '-3.7%' },
  { label: 'Leverage Hard Cap', status: 'green', threshold: '4x', current: '1.8x' },
  { label: 'Correlation Spike Detector', status: 'amber', threshold: '0.7', current: '0.62' },
  { label: 'Flash Crash Detector', status: 'green', threshold: 'Active', current: 'Online' },
  { label: 'Liquidity Monitor', status: 'green', threshold: '70%', current: '87%' },
]

export const ARCHITECTURE_LAYERS: ArchitectureLayer[] = [
  {
    id: 1,
    name: 'DATA INGESTION',
    subtitle: 'Layer 1 — Raw Intelligence',
    description: '500+ data feeds: market microstructure, alternative data, sentiment, macro indicators, satellite imagery.',
    color: '#00D4FF',
    icon: 'Database',
    metrics: ['500+ feeds', '2ms latency', '99.99% uptime'],
  },
  {
    id: 2,
    name: 'SIGNAL GENERATION',
    subtitle: 'Layer 2 — Alpha Factory',
    description: '9 independent signal generators with cross-validation. Z-score normalization, feature engineering, and alpha decay monitoring.',
    color: '#06B6D4',
    icon: 'Zap',
    metrics: ['9 signal pods', '10K+ features', 'Real-time scoring'],
  },
  {
    id: 3,
    name: 'AI ORCHESTRATION',
    subtitle: 'Layer 3 — Neural Command',
    description: 'Ensemble meta-learning layer combining pod signals. Regime-aware weights using Hidden Markov Models and Bayesian inference.',
    color: '#8B5CF6',
    icon: 'Brain',
    metrics: ['HMM regime model', 'Bayesian ensemble', 'LSTM forecaster'],
  },
  {
    id: 4,
    name: 'PORTFOLIO CONSTRUCTION',
    subtitle: 'Layer 4 — Allocation Engine',
    description: 'Black-Litterman portfolio optimization with Kelly Criterion position sizing. Factor exposure management and ESG constraints.',
    color: '#FFB800',
    icon: 'PieChart',
    metrics: ['Black-Litterman', 'Kelly sizing', 'Factor neutral'],
  },
  {
    id: 5,
    name: 'EXECUTION ENGINE',
    subtitle: 'Layer 5 — Market Interface',
    description: 'Smart order routing with VWAP/TWAP algorithms, dark pool access, and implementation shortfall minimization.',
    color: '#F97316',
    icon: 'Cpu',
    metrics: ['Smart routing', '12 venues', '<50μs latency'],
  },
  {
    id: 6,
    name: 'RISK MANAGEMENT',
    subtitle: 'Layer 6 — Guardian System',
    description: 'Real-time 4-layer risk framework: position, portfolio, factor, and tail risk. Automated kill switches with manual override.',
    color: '#FF3366',
    icon: 'Shield',
    metrics: ['4-layer risk', 'Kill switches', 'CVaR monitoring'],
  },
  {
    id: 7,
    name: 'LEARNING LOOP',
    subtitle: 'Layer 7 — Continuous Evolution',
    description: 'Continuous learning from live P&L attribution, walk-forward optimization, and strategy drift detection.',
    color: '#00FF94',
    icon: 'RefreshCw',
    metrics: ['Walk-forward opt', 'Drift detection', 'Auto-retraining'],
  },
]

// Correlation matrix for 9 strategies
export function generateCorrelationMatrix(): number[][] {
  const matrix: number[][] = []
  const baseCorrelations = [
    [1.00, 0.12, 0.34, -0.08, -0.22, 0.18, 0.41, 0.28, 0.03],
    [0.12, 1.00, 0.08, 0.31, 0.14, 0.22, 0.19, 0.35, -0.04],
    [0.34, 0.08, 1.00, 0.05, -0.11, 0.27, 0.38, 0.21, 0.09],
    [-0.08, 0.31, 0.05, 1.00, 0.09, 0.14, 0.11, 0.29, 0.17],
    [-0.22, 0.14, -0.11, 0.09, 1.00, -0.07, -0.18, 0.06, -0.12],
    [0.18, 0.22, 0.27, 0.14, -0.07, 1.00, 0.24, 0.31, 0.08],
    [0.41, 0.19, 0.38, 0.11, -0.18, 0.24, 1.00, 0.33, 0.07],
    [0.28, 0.35, 0.21, 0.29, 0.06, 0.31, 0.33, 1.00, 0.12],
    [0.03, -0.04, 0.09, 0.17, -0.12, 0.08, 0.07, 0.12, 1.00],
  ]
  return baseCorrelations
}

// Generate live-simulated "current" data that changes slightly each call
export function getLiveMetrics() {
  const base = {
    sharpe: 1.87,
    drawdown: -3.7,
    winRate: 64.7,
    dailyPnl: 0,
    totalReturn: 187.4,
  }

  // Small random walk for live feel
  const now = Date.now()
  const microNoise = Math.sin(now / 3000) * 0.02

  return {
    sharpe: parseFloat((base.sharpe + microNoise).toFixed(3)),
    drawdown: parseFloat((base.drawdown + microNoise * 0.5).toFixed(2)),
    winRate: parseFloat((base.winRate + microNoise * 0.3).toFixed(1)),
    dailyPnl: parseFloat((0.34 + Math.sin(now / 5000) * 0.08).toFixed(2)),
    totalReturn: parseFloat((base.totalReturn + microNoise * 0.4).toFixed(1)),
  }
}
