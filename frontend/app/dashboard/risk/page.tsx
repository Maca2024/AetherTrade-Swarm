'use client'

import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import {
  ResponsiveContainer,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  Radar,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from 'recharts'
import {
  Shield,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Activity,
  TrendingDown,
  BarChart2,
  Info,
  Zap,
} from 'lucide-react'
import dynamic from 'next/dynamic'
import { RISK_METRICS, KILL_SWITCHES, type RiskMetric } from '@/lib/data'
import { useRiskDashboard, useKillSwitches } from '@/lib/hooks'

const RiskPanel = dynamic(() => import('@/components/RiskPanel'), {
  ssr: false,
  loading: () => (
    <div className="h-64 rounded-2xl bg-white/5 animate-pulse" />
  ),
})

// 30-day rolling VaR history (mock)
const VAR_HISTORY = Array.from({ length: 30 }, (_, i) => {
  const base = 1.42
  const wave = Math.sin(i * 0.5) * 0.18
  const noise = (((i * 7919 + 1013) % 100) / 100 - 0.5) * 0.08
  return {
    day: `D-${30 - i}`,
    var95: parseFloat(Math.max(0.8, base + wave + noise).toFixed(3)),
    cvar99: parseFloat(Math.max(1.2, (base + wave + noise) * 1.52).toFixed(3)),
  }
})

function RiskRadarChart({ metrics }: { metrics: RiskMetric[] }) {
  const radarData = metrics.map((m) => ({
    metric: m.label.split(' ')[0],
    value: parseFloat(((m.value / m.max) * 100).toFixed(1)),
  }))

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="rounded-2xl p-5"
      style={{
        background: 'rgba(255,255,255,0.02)',
        border: '1px solid rgba(255,255,255,0.07)',
      }}
    >
      <div className="flex items-center gap-2 mb-4">
        <BarChart2 className="w-4 h-4 text-white/40" />
        <h3 className="text-sm font-bold text-white">Risk Profile Radar</h3>
        <div className="ml-auto text-[11px] text-white/30 flex items-center gap-1">
          <Info className="w-3 h-3" />
          % of limit used
        </div>
      </div>

      <div className="h-48">
        <ResponsiveContainer width="100%" height="100%">
          <RadarChart data={radarData} margin={{ top: 5, right: 20, bottom: 5, left: 20 }}>
            <PolarGrid stroke="rgba(255,255,255,0.07)" />
            <PolarAngleAxis
              dataKey="metric"
              tick={{ fill: 'rgba(255,255,255,0.35)', fontSize: 9 }}
            />
            <Radar
              name="Risk Usage"
              dataKey="value"
              stroke="#00FF94"
              fill="#00FF94"
              fillOpacity={0.08}
              strokeWidth={1.5}
            />
          </RadarChart>
        </ResponsiveContainer>
      </div>

      <div className="mt-2 grid grid-cols-2 gap-2">
        {metrics.slice(0, 4).map((m) => {
          const pct = Math.round((m.value / m.max) * 100)
          return (
            <div
              key={m.label}
              className="flex items-center justify-between px-2.5 py-1.5 rounded-lg text-[11px]"
              style={{
                background: `${m.color}08`,
                border: `1px solid ${m.color}20`,
              }}
            >
              <span className="text-white/40 truncate">{m.label.split(' ')[0]}</span>
              <span className="font-bold ml-1" style={{ color: m.color }}>{pct}%</span>
            </div>
          )
        })}
      </div>
    </motion.div>
  )
}

function VarHistoryChart() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: 0.1 }}
      className="rounded-2xl p-5"
      style={{
        background: 'rgba(255,255,255,0.02)',
        border: '1px solid rgba(255,255,255,0.07)',
      }}
    >
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <TrendingDown className="w-4 h-4 text-white/40" />
          <h3 className="text-sm font-bold text-white">30-Day VaR History</h3>
        </div>
        <div className="flex items-center gap-3 text-[11px]">
          <div className="flex items-center gap-1.5">
            <div className="w-3 h-0.5 bg-[#00FF94] rounded-full" />
            <span className="text-white/40">VaR 95%</span>
          </div>
          <div className="flex items-center gap-1.5">
            <div className="w-3 h-0.5 bg-[#FFB800] rounded-full" />
            <span className="text-white/40">CVaR 99%</span>
          </div>
        </div>
      </div>

      <div className="h-48">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={VAR_HISTORY} margin={{ top: 5, right: 5, bottom: 5, left: 5 }}>
            <defs>
              <linearGradient id="varGradRisk" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#00FF94" stopOpacity={0.2} />
                <stop offset="100%" stopColor="#00FF94" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="cvarGradRisk" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#FFB800" stopOpacity={0.15} />
                <stop offset="100%" stopColor="#FFB800" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" vertical={false} />
            <XAxis
              dataKey="day"
              tick={{ fill: 'rgba(255,255,255,0.25)', fontSize: 9 }}
              tickLine={false}
              axisLine={false}
              interval={4}
            />
            <YAxis
              tick={{ fill: 'rgba(255,255,255,0.25)', fontSize: 9 }}
              tickLine={false}
              axisLine={false}
              tickFormatter={(v: number) => `${v.toFixed(1)}%`}
              domain={[0, 4]}
            />
            <Tooltip
              contentStyle={{
                background: 'rgba(7,7,15,0.95)',
                border: '1px solid rgba(0,255,148,0.2)',
                borderRadius: '10px',
                fontSize: '11px',
              }}
              formatter={(value: number, name: string) => [`${value.toFixed(3)}%`, name]}
              labelStyle={{ color: 'rgba(255,255,255,0.4)' }}
            />
            <Area
              type="monotone"
              dataKey="cvar99"
              name="CVaR 99%"
              stroke="#FFB800"
              strokeWidth={1.5}
              fill="url(#cvarGradRisk)"
              dot={false}
            />
            <Area
              type="monotone"
              dataKey="var95"
              name="VaR 95%"
              stroke="#00FF94"
              strokeWidth={2}
              fill="url(#varGradRisk)"
              dot={false}
              style={{ filter: 'drop-shadow(0 0 3px rgba(0,255,148,0.4))' }}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      <div className="mt-3 pt-3 border-t border-white/5 flex items-center justify-between text-xs">
        <span className="text-white/30">Hard limit: 3.0%</span>
        <div className="flex items-center gap-1.5 text-[#00FF94]">
          <CheckCircle className="w-3.5 h-3.5" />
          <span className="font-medium">Well within limits</span>
        </div>
      </div>
    </motion.div>
  )
}

function KillSwitchPanel() {
  const { data: apiKs } = useKillSwitches()
  const [liveVaR, setLiveVaR] = useState(1.42)

  useEffect(() => {
    if (apiKs) return
    const id = setInterval(() => {
      setLiveVaR((prev) => parseFloat((prev + (Math.random() - 0.5) * 0.04).toFixed(3)))
    }, 3000)
    return () => clearInterval(id)
  }, [apiKs])

  const switches = apiKs
    ? apiKs.kill_switches.map((ks) => ({
        label: ks.name,
        status: ks.triggered ? ('red' as const) : ('green' as const),
        threshold: `${ks.threshold}`,
        current: `${ks.current_value}`,
        description: ks.description,
      }))
    : KILL_SWITCHES.map((ks) => ({ ...ks, description: '' }))

  const anyTriggered = apiKs?.any_triggered ?? false
  const tradingHalted = apiKs?.trading_halted ?? false

  const statusColor = { green: '#00FF94', amber: '#FFB800', red: '#FF3366' }

  const statusIcon = {
    green: <CheckCircle className="w-4 h-4 text-[#00FF94]" />,
    amber: <AlertTriangle className="w-4 h-4 text-[#FFB800]" />,
    red: <XCircle className="w-4 h-4 text-[#FF3366]" />,
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: 0.15 }}
      className="rounded-2xl overflow-hidden"
      style={{
        background: 'rgba(255,255,255,0.02)',
        border: '1px solid rgba(255,255,255,0.07)',
      }}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-4 border-b border-white/5">
        <div className="flex items-center gap-2">
          <Zap className="w-4 h-4 text-white/40" />
          <h3 className="text-sm font-bold text-white">Kill Switches</h3>
        </div>
        {tradingHalted ? (
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[11px] font-bold text-[#FF3366] bg-[#FF3366]/10 border border-[#FF3366]/20">
            <XCircle className="w-3 h-3" />
            TRADING HALTED
          </div>
        ) : anyTriggered ? (
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[11px] font-bold text-[#FFB800] bg-[#FFB800]/10 border border-[#FFB800]/20">
            <AlertTriangle className="w-3 h-3" />
            WARNING
          </div>
        ) : (
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[11px] font-medium text-[#00FF94] bg-[#00FF94]/10 border border-[#00FF94]/20">
            <div className="w-1.5 h-1.5 rounded-full bg-[#00FF94] animate-pulse" />
            ALL CLEAR
          </div>
        )}
      </div>

      {/* Live VaR banner */}
      <div
        className="flex items-center justify-between px-5 py-3 border-b border-white/5"
        style={{ background: 'rgba(0,255,148,0.03)' }}
      >
        <div className="flex items-center gap-3">
          <Shield className="w-4 h-4 text-[#00FF94]" />
          <div>
            <div className="text-[10px] text-white/30 uppercase tracking-widest">Live 95% VaR</div>
            <div className="flex items-center gap-2">
              <motion.span
                key={liveVaR}
                initial={{ y: -6, opacity: 0 }}
                animate={{ y: 0, opacity: 1 }}
                className="text-xl font-black text-[#00FF94] tabular-nums"
              >
                {liveVaR.toFixed(3)}%
              </motion.span>
              <Activity className="w-3.5 h-3.5 text-[#00FF94] animate-pulse" />
            </div>
          </div>
        </div>
        <div className="text-right">
          <div className="text-[10px] text-white/30">Hard limit</div>
          <div className="text-sm font-bold text-white/60">3.000%</div>
        </div>
      </div>

      {/* Kill switch rows */}
      <div className="p-4 space-y-2">
        {switches.map((sw, i) => {
          const color = statusColor[sw.status as keyof typeof statusColor]
          const icon = statusIcon[sw.status as keyof typeof statusIcon]

          return (
            <motion.div
              key={sw.label}
              initial={{ opacity: 0, x: 12 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.2 + i * 0.06 }}
              className="flex items-center justify-between p-3 rounded-xl"
              style={{
                background: `${color}08`,
                border: `1px solid ${color}20`,
              }}
            >
              <div className="flex items-center gap-2.5 min-w-0">
                {icon}
                <div className="min-w-0">
                  <div className="text-xs font-medium text-white/70 truncate">{sw.label}</div>
                  {sw.description && (
                    <div className="text-[10px] text-white/30 truncate hidden sm:block">
                      {sw.description}
                    </div>
                  )}
                </div>
              </div>
              <div className="flex items-center gap-4 flex-shrink-0 ml-2">
                <div className="text-right hidden sm:block">
                  <div className="text-[10px] text-white/30">Threshold</div>
                  <div className="text-xs font-medium text-white/50">{sw.threshold}</div>
                </div>
                <div className="text-right">
                  <div className="text-[10px] text-white/30">Current</div>
                  <div className="text-xs font-black tabular-nums" style={{ color }}>
                    {sw.current}
                  </div>
                </div>
              </div>
            </motion.div>
          )
        })}
      </div>
    </motion.div>
  )
}

function StressTestPanel() {
  const scenarios = [
    {
      name: '2008 Financial Crisis',
      period: 'Sep 2008 – Mar 2009',
      loss: '-11.2%',
      status: 'PASS',
      statusColor: '#00FF94',
      detail: 'Defensive positioning and vol strategies offset equity losses',
    },
    {
      name: 'COVID-19 Crash',
      period: 'Feb 2020 – Mar 2020',
      loss: '-6.8%',
      status: 'PASS',
      statusColor: '#00FF94',
      detail: 'Crisis regime triggered early, drawdown contained',
    },
    {
      name: '2022 Rate Shock',
      period: 'Jan 2022 – Oct 2022',
      loss: '-9.4%',
      status: 'PASS',
      statusColor: '#00FF94',
      detail: 'Macro and carry strategies partially hedged rate exposure',
    },
    {
      name: 'Flash Crash Scenario',
      period: 'Synthetic -20% intraday',
      loss: '-4.1%',
      status: 'PASS',
      statusColor: '#00FF94',
      detail: 'Kill switches trigger at -5% intraday, halting new orders',
    },
    {
      name: 'Liquidity Crisis',
      period: 'Synthetic bid-ask +500bps',
      loss: '-7.3%',
      status: 'WARN',
      statusColor: '#FFB800',
      detail: 'Market making pod exposed to slippage; stop-loss may gap',
    },
  ]

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: 0.25 }}
      className="rounded-2xl overflow-hidden"
      style={{
        background: 'rgba(255,255,255,0.02)',
        border: '1px solid rgba(255,255,255,0.07)',
      }}
    >
      <div className="flex items-center justify-between px-5 py-4 border-b border-white/5">
        <div className="flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 text-white/40" />
          <h3 className="text-sm font-bold text-white">Stress Tests</h3>
        </div>
        <span className="text-[11px] text-white/30 bg-white/5 px-2 py-0.5 rounded-full">
          Historical + synthetic scenarios
        </span>
      </div>

      <div className="divide-y divide-white/5">
        {scenarios.map((sc, i) => (
          <motion.div
            key={sc.name}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.3 + i * 0.06 }}
            className="px-5 py-3.5 hover:bg-white/[0.02] transition-colors"
          >
            <div className="flex items-start justify-between gap-4">
              <div className="min-w-0">
                <div className="flex items-center gap-2 mb-0.5">
                  <span className="text-xs font-bold text-white/80">{sc.name}</span>
                  <span
                    className="text-[10px] font-bold px-1.5 py-0.5 rounded"
                    style={{
                      color: sc.statusColor,
                      background: `${sc.statusColor}15`,
                    }}
                  >
                    {sc.status}
                  </span>
                </div>
                <div className="text-[10px] text-white/30 mb-1">{sc.period}</div>
                <div className="text-[11px] text-white/40">{sc.detail}</div>
              </div>
              <div className="text-right flex-shrink-0">
                <div className="text-base font-black text-[#FF3366]">{sc.loss}</div>
                <div className="text-[10px] text-white/30">simulated loss</div>
              </div>
            </div>
          </motion.div>
        ))}
      </div>
    </motion.div>
  )
}

export default function RiskPage() {
  const { data: apiRisk } = useRiskDashboard()

  const displayMetrics: RiskMetric[] = apiRisk
    ? apiRisk.metrics.map((m) => {
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
    : RISK_METRICS

  return (
    <div className="p-4 sm:p-6 space-y-6">
      {/* Page header */}
      <div>
        <h1 className="text-xl font-black text-white tracking-tight">Risk Dashboard</h1>
        <p className="text-xs text-white/30 mt-0.5">
          4-layer real-time risk framework with automated circuit breakers
        </p>
      </div>

      {/* Top row: radar + VaR history */}
      <div className="grid lg:grid-cols-2 gap-4">
        <RiskRadarChart metrics={displayMetrics} />
        <VarHistoryChart />
      </div>

      {/* Kill switches */}
      <KillSwitchPanel />

      {/* Stress tests */}
      <StressTestPanel />

      {/* Full RiskPanel component (reused) */}
      <div>
        <h2 className="text-base font-bold text-white mb-4 px-1">Detailed Risk Panel</h2>
        <RiskPanel />
      </div>
    </div>
  )
}
