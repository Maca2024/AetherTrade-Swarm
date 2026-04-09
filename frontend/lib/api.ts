import { apiFetch } from './fetcher'
import type {
  Regime,
  RegimeState,
  StrategyPod,
  EquityPoint,
  MetricCard,
  RiskMetric,
} from './data'

// ---------------------------------------------------------------------------
// API Response types (matching backend Pydantic schemas)
// ---------------------------------------------------------------------------

export interface ApiRegimeResponse {
  regime: string
  confidence: number
  probabilities: Record<string, number>
  duration_days: number
  last_transition: string
  signal_impact: Record<string, string>
}

export interface ApiPodMetrics {
  pod_name: string
  display_name: string
  status: string
  regime_allocation: number
  ytd_return: number
  sharpe_ratio: number
  max_drawdown: number
  win_rate: number
  signal_count: number
  last_signal_at: string
  description: string
}

export interface ApiPodListResponse {
  pods: ApiPodMetrics[]
  total_active: number
  ensemble_allocation_sum: number
}

export interface ApiPerformanceMetrics {
  total_return: number
  ytd_return: number
  mtd_return: number
  annualized_return: number
  sharpe_ratio: number
  sortino_ratio: number
  calmar_ratio: number
  max_drawdown: number
  current_drawdown: number
  win_rate: number
  profit_factor: number
  avg_win: number
  avg_loss: number
  best_day: number
  worst_day: number
  volatility_annual: number
  beta: number
  alpha: number
  information_ratio: number
  as_of: string
}

export interface ApiRiskDashboard {
  overall_status: string
  metrics: Array<{
    name: string
    value: number
    threshold_warning: number
    threshold_critical: number
    status: string
    unit: string
    description: string
  }>
  portfolio_var_95: number
  portfolio_cvar_95: number
  portfolio_var_99: number
  stress_test_loss: number
  as_of: string
}

export interface ApiKillSwitchesResponse {
  kill_switches: Array<{
    name: string
    triggered: boolean
    threshold: number
    current_value: number
    description: string
    auto_action: string
    last_checked: string
  }>
  any_triggered: boolean
  trading_halted: boolean
}

export interface ApiHealthResponse {
  status: string
  version: string
  environment: string
  uptime_seconds: number
  timestamp: string
  services: Array<{
    name: string
    status: string
    latency_ms?: number
    detail?: string
  }>
}

export interface ApiGenerateKeyResponse {
  key_id: string
  api_key: string
  name: string
  tier: string
  rate_limit_per_minute: number
  created_at: string
  warning: string
}

export interface ChatMessage {
  role: 'user' | 'assistant' | 'system'
  content: string
}

export interface ChatResponse {
  reply: string
  regime_context?: string
}

// ---------------------------------------------------------------------------
// Color/styling maps for regime → frontend display
// ---------------------------------------------------------------------------

const REGIME_STYLE: Record<string, { color: string; bgColor: string; label: string; description: string }> = {
  bull: {
    color: '#00FF94',
    bgColor: 'rgba(0, 255, 148, 0.08)',
    label: 'BULL MARKET',
    description: 'Risk-on momentum regime detected. Trend-following strategies overweight.',
  },
  bear: {
    color: '#FF3366',
    bgColor: 'rgba(255, 51, 102, 0.08)',
    label: 'BEAR MARKET',
    description: 'Defensive posture active. Short bias, mean-reversion and volatility pods elevated.',
  },
  crisis: {
    color: '#FFB800',
    bgColor: 'rgba(255, 184, 0, 0.08)',
    label: 'CRISIS MODE',
    description: 'Tail-risk event detected. Kill switches active. Capital preservation priority.',
  },
  range: {
    color: '#00D4FF',
    bgColor: 'rgba(0, 212, 255, 0.08)',
    label: 'RANGE-BOUND',
    description: 'Low directional bias. Mean-reversion and stat-arb strategies optimal.',
  },
}

const POD_COLORS: Record<string, { color: string; glowColor: string }> = {
  momentum: { color: '#00D4FF', glowColor: 'rgba(0, 212, 255, 0.3)' },
  mean_reversion: { color: '#8B5CF6', glowColor: 'rgba(139, 92, 246, 0.3)' },
  macro: { color: '#FFB800', glowColor: 'rgba(255, 184, 0, 0.3)' },
  stat_arb: { color: '#00FF94', glowColor: 'rgba(0, 255, 148, 0.3)' },
  options_vol: { color: '#FF3366', glowColor: 'rgba(255, 51, 102, 0.3)' },
  behavioral: { color: '#F97316', glowColor: 'rgba(249, 115, 22, 0.3)' },
  ai_ml: { color: '#06B6D4', glowColor: 'rgba(6, 182, 212, 0.3)' },
  multi_factor: { color: '#A78BFA', glowColor: 'rgba(167, 139, 250, 0.3)' },
  market_making: { color: '#34D399', glowColor: 'rgba(52, 211, 153, 0.3)' },
}

const POD_SHORT_NAMES: Record<string, string> = {
  momentum: 'MOM',
  mean_reversion: 'MR',
  macro: 'GMC',
  stat_arb: 'SA',
  options_vol: 'VOL',
  behavioral: 'BEH',
  ai_ml: 'AI',
  multi_factor: 'MF',
  market_making: 'MM',
}

// ---------------------------------------------------------------------------
// API functions
// ---------------------------------------------------------------------------

export async function fetchRegime(apiKey: string): Promise<RegimeState> {
  const data = await apiFetch<ApiRegimeResponse>('/api/v1/regime', { apiKey })
  const style = REGIME_STYLE[data.regime] ?? REGIME_STYLE.range
  return {
    type: data.regime as Regime,
    label: style.label,
    confidence: Math.round(data.confidence * 100),
    color: style.color,
    bgColor: style.bgColor,
    description: style.description,
  }
}

export async function fetchStrategies(apiKey: string): Promise<StrategyPod[]> {
  const data = await apiFetch<ApiPodListResponse>('/api/v1/strategies', { apiKey })
  return data.pods.map((pod) => {
    const colors = POD_COLORS[pod.pod_name] ?? { color: '#888', glowColor: 'rgba(136,136,136,0.3)' }
    return {
      id: pod.pod_name,
      name: pod.display_name,
      shortName: POD_SHORT_NAMES[pod.pod_name] ?? pod.pod_name.slice(0, 3).toUpperCase(),
      allocation: pod.regime_allocation * 100,
      signal: 0, // Not returned from list endpoint
      signalStrength: Math.round(pod.win_rate * 100),
      pnl: pod.ytd_return,
      sharpe: pod.sharpe_ratio,
      sparkline: generateFakeSparkline(pod.ytd_return),
      color: colors.color,
      glowColor: colors.glowColor,
      description: pod.description,
      regime: [], // Would need separate endpoint to populate
    }
  })
}

export async function fetchPerformance(apiKey: string): Promise<{
  metrics: MetricCard[]
  performance: ApiPerformanceMetrics
}> {
  const data = await apiFetch<ApiPerformanceMetrics>('/api/v1/portfolio/performance', { apiKey })
  const metrics: MetricCard[] = [
    {
      label: 'Total Return',
      value: `${data.total_return >= 0 ? '+' : ''}${data.total_return.toFixed(1)}%`,
      change: `${data.ytd_return >= 0 ? '+' : ''}${data.ytd_return.toFixed(1)}% YTD`,
      positive: data.total_return >= 0,
    },
    {
      label: 'Sharpe Ratio',
      value: data.sharpe_ratio.toFixed(2),
      change: `Sortino ${data.sortino_ratio.toFixed(2)}`,
      positive: data.sharpe_ratio >= 1.0,
    },
    {
      label: 'Max Drawdown',
      value: `${data.max_drawdown.toFixed(1)}%`,
      change: `Current ${data.current_drawdown.toFixed(1)}%`,
      positive: data.max_drawdown > -10,
    },
    {
      label: 'Win Rate',
      value: `${(data.win_rate * 100).toFixed(1)}%`,
      change: `PF ${data.profit_factor.toFixed(2)}`,
      positive: data.win_rate > 0.5,
    },
    {
      label: 'Alpha (ann.)',
      value: `${data.alpha >= 0 ? '+' : ''}${data.alpha.toFixed(1)}%`,
      change: 'vs S&P 500',
      positive: data.alpha >= 0,
    },
    {
      label: 'Sortino Ratio',
      value: data.sortino_ratio.toFixed(2),
      change: `Beta ${data.beta.toFixed(2)}`,
      positive: data.sortino_ratio >= 1.5,
    },
  ]
  return { metrics, performance: data }
}

export async function fetchRisk(apiKey: string): Promise<{
  metrics: RiskMetric[]
  killSwitches: Array<{ label: string; status: string; threshold: string; current: string }>
  overallStatus: string
  var95: number
}> {
  const data = await apiFetch<ApiRiskDashboard>('/api/v1/risk', { apiKey })
  const ksData = await apiFetch<ApiKillSwitchesResponse>('/api/v1/risk/kill-switches', { apiKey })

  const metrics: RiskMetric[] = data.metrics.map((m) => {
    const status = m.status === 'ok' ? 'green' : m.status === 'warning' ? 'amber' : 'red'
    const colorMap = { green: '#00FF94', amber: '#FFB800', red: '#FF3366' }
    return {
      label: m.name,
      value: m.value,
      max: m.threshold_critical,
      unit: m.unit,
      status: status as 'green' | 'amber' | 'red',
      color: colorMap[status as keyof typeof colorMap],
    }
  })

  const killSwitches = ksData.kill_switches.map((ks) => ({
    label: ks.name,
    status: ks.triggered ? 'red' : 'green',
    threshold: `${ks.threshold}`,
    current: `${ks.current_value}`,
  }))

  return {
    metrics,
    killSwitches,
    overallStatus: data.overall_status,
    var95: data.portfolio_var_95,
  }
}

export async function fetchHealth(): Promise<ApiHealthResponse> {
  return apiFetch<ApiHealthResponse>('/health')
}

export async function generateApiKeyFromApi(
  apiKey: string,
  name: string,
  email: string,
  tier: string = 'free'
): Promise<ApiGenerateKeyResponse> {
  return apiFetch<ApiGenerateKeyResponse>('/api/v1/keys/generate', {
    method: 'POST',
    apiKey,
    body: JSON.stringify({ name, owner_email: email, tier }),
  })
}

export async function sendChatMessage(
  messages: ChatMessage[],
  apiKey?: string
): Promise<ChatResponse> {
  return apiFetch<ChatResponse>('/api/v1/chat', {
    method: 'POST',
    apiKey,
    body: JSON.stringify({ messages }),
  })
}

// ---------------------------------------------------------------------------
// Helper: generate a fake sparkline based on return value
// ---------------------------------------------------------------------------

function generateFakeSparkline(returnPct: number, length = 15): number[] {
  const points: number[] = []
  let val = 100
  const trend = returnPct / length / 100
  for (let i = 0; i < length; i++) {
    val += val * (trend + (Math.random() - 0.48) * 0.02)
    points.push(parseFloat(val.toFixed(2)))
  }
  return points
}
