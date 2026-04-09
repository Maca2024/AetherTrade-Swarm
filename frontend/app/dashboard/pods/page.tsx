'use client'

import { useState } from 'react'
import { motion } from 'framer-motion'
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Cell,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  Radar,
} from 'recharts'
import {
  TrendingUp,
  TrendingDown,
  BarChart2,
  Layers,
  SlidersHorizontal,
} from 'lucide-react'
import dynamic from 'next/dynamic'
import { STRATEGY_PODS, type StrategyPod } from '@/lib/data'
import { useStrategies } from '@/lib/hooks'
import { cn } from '@/lib/utils'

const StrategyPodsGrid = dynamic(() => import('@/components/StrategyPodsGrid'), {
  ssr: false,
  loading: () => (
    <div className="h-80 rounded-2xl bg-white/3 animate-pulse" />
  ),
})

type SortKey = 'pnl' | 'sharpe' | 'allocation' | 'signalStrength'
type SortDir = 'asc' | 'desc'

interface CustomBarTooltipProps {
  active?: boolean
  payload?: Array<{ name: string; value: number; color?: string }>
  label?: string
}

function CustomBarTooltip({ active, payload, label }: CustomBarTooltipProps) {
  if (!active || !payload?.length) return null
  return (
    <div
      className="rounded-xl px-3 py-2 text-xs"
      style={{
        background: 'rgba(7,7,15,0.95)',
        border: '1px solid rgba(124,58,237,0.2)',
        backdropFilter: 'blur(20px)',
      }}
    >
      <p className="text-white/50 mb-1 font-medium">{label}</p>
      {payload.map((entry) => (
        <div key={entry.name} className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full" style={{ background: entry.color ?? '#7C3AED' }} />
          <span className="text-white/60">{entry.name}:</span>
          <span className="font-bold text-white">{typeof entry.value === 'number' ? entry.value.toFixed(2) : entry.value}</span>
        </div>
      ))}
    </div>
  )
}

function PodComparisonChart({ pods }: { pods: StrategyPod[] }) {
  const [metric, setMetric] = useState<SortKey>('pnl')

  const metricConfig: Record<SortKey, { label: string; color: string; format: (v: number) => string }> = {
    pnl: { label: 'YTD P&L (%)', color: '#00FF94', format: (v) => `${v >= 0 ? '+' : ''}${v.toFixed(1)}%` },
    sharpe: { label: 'Sharpe Ratio', color: '#00D4FF', format: (v) => v.toFixed(2) },
    allocation: { label: 'Allocation (%)', color: '#7C3AED', format: (v) => `${v.toFixed(1)}%` },
    signalStrength: { label: 'Signal Strength (%)', color: '#FFB800', format: (v) => `${v.toFixed(0)}%` },
  }

  const cfg = metricConfig[metric]
  const chartData = [...pods]
    .sort((a, b) => b[metric] - a[metric])
    .map((p) => ({
      name: p.shortName,
      value: p[metric],
      color: p.color,
      fullName: p.name,
    }))

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
      <div className="flex items-center justify-between mb-5 flex-wrap gap-3">
        <div className="flex items-center gap-2">
          <BarChart2 className="w-4 h-4 text-white/40" />
          <h3 className="text-sm font-bold text-white">Pod Performance Comparison</h3>
        </div>

        <div className="flex items-center gap-1 bg-white/5 rounded-xl p-1">
          {(Object.keys(metricConfig) as SortKey[]).map((key) => (
            <button
              key={key}
              onClick={() => setMetric(key)}
              className={cn(
                'px-3 py-1.5 rounded-lg text-[11px] font-medium transition-all',
                metric === key
                  ? 'bg-[#7C3AED] text-white'
                  : 'text-white/40 hover:text-white/70'
              )}
            >
              {metricConfig[key].label.split(' ')[0]}
            </button>
          ))}
        </div>
      </div>

      <div className="h-52">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} margin={{ top: 5, right: 5, bottom: 5, left: 0 }}>
            <XAxis
              dataKey="name"
              tick={{ fill: 'rgba(255,255,255,0.4)', fontSize: 10 }}
              tickLine={false}
              axisLine={false}
            />
            <YAxis
              tick={{ fill: 'rgba(255,255,255,0.3)', fontSize: 10 }}
              tickLine={false}
              axisLine={false}
              tickFormatter={(v) => typeof v === 'number' ? v.toFixed(metric === 'sharpe' ? 1 : 0) : v}
              width={36}
            />
            <Tooltip content={<CustomBarTooltip />} cursor={{ fill: 'rgba(255,255,255,0.03)' }} />
            <Bar dataKey="value" name={cfg.label} radius={[4, 4, 0, 0]}>
              {chartData.map((entry, i) => (
                <Cell
                  key={i}
                  fill={entry.color}
                  style={{ filter: `drop-shadow(0 0 4px ${entry.color}60)` }}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </motion.div>
  )
}

function PodRadarChart({ pods }: { pods: StrategyPod[] }) {
  const [selectedPods, setSelectedPods] = useState<string[]>(['momentum', 'ai-ml', 'options-vol'])

  const togglePod = (id: string) => {
    setSelectedPods((prev) =>
      prev.includes(id) ? prev.filter((p) => p !== id) : [...prev, id].slice(-4)
    )
  }

  // Normalize metrics to 0-100 for radar
  const maxPnl = Math.max(...pods.map((p) => p.pnl))
  const maxSharpe = Math.max(...pods.map((p) => p.sharpe))

  const radarData = [
    { metric: 'P&L', ...Object.fromEntries(pods.filter((p) => selectedPods.includes(p.id)).map((p) => [p.shortName, (p.pnl / maxPnl) * 100])) },
    { metric: 'Sharpe', ...Object.fromEntries(pods.filter((p) => selectedPods.includes(p.id)).map((p) => [p.shortName, (p.sharpe / maxSharpe) * 100])) },
    { metric: 'Signal', ...Object.fromEntries(pods.filter((p) => selectedPods.includes(p.id)).map((p) => [p.shortName, p.signalStrength])) },
    { metric: 'Alloc', ...Object.fromEntries(pods.filter((p) => selectedPods.includes(p.id)).map((p) => [p.shortName, p.allocation / 0.25])) },
    { metric: 'Win Rate', ...Object.fromEntries(pods.filter((p) => selectedPods.includes(p.id)).map((p) => [p.shortName, p.signalStrength * 0.9])) },
  ]

  const activePods = pods.filter((p) => selectedPods.includes(p.id))

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: 0.15 }}
      className="rounded-2xl p-5"
      style={{
        background: 'rgba(255,255,255,0.02)',
        border: '1px solid rgba(255,255,255,0.07)',
      }}
    >
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <SlidersHorizontal className="w-4 h-4 text-white/40" />
          <h3 className="text-sm font-bold text-white">Pod Radar</h3>
        </div>
        <span className="text-[11px] text-white/30">Select up to 4 pods</span>
      </div>

      {/* Pod toggles */}
      <div className="flex flex-wrap gap-1.5 mb-4">
        {pods.map((pod) => {
          const active = selectedPods.includes(pod.id)
          return (
            <button
              key={pod.id}
              onClick={() => togglePod(pod.id)}
              className={cn(
                'px-2.5 py-1 rounded-lg text-[11px] font-medium transition-all',
                active ? 'text-white' : 'text-white/30 hover:text-white/60 bg-white/5'
              )}
              style={active ? { background: `${pod.color}20`, border: `1px solid ${pod.color}40`, color: pod.color } : { border: '1px solid rgba(255,255,255,0.05)' }}
              aria-pressed={active}
            >
              {pod.shortName}
            </button>
          )
        })}
      </div>

      {activePods.length > 0 ? (
        <div className="h-52">
          <ResponsiveContainer width="100%" height="100%">
            <RadarChart data={radarData} margin={{ top: 5, right: 20, bottom: 5, left: 20 }}>
              <PolarGrid stroke="rgba(255,255,255,0.07)" />
              <PolarAngleAxis
                dataKey="metric"
                tick={{ fill: 'rgba(255,255,255,0.4)', fontSize: 10 }}
              />
              {activePods.map((pod) => (
                <Radar
                  key={pod.id}
                  name={pod.shortName}
                  dataKey={pod.shortName}
                  stroke={pod.color}
                  fill={pod.color}
                  fillOpacity={0.08}
                  strokeWidth={1.5}
                />
              ))}
            </RadarChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <div className="h-52 flex items-center justify-center text-sm text-white/30">
          Select at least one pod to compare
        </div>
      )}
    </motion.div>
  )
}

function PodLeaderboard({ pods }: { pods: StrategyPod[] }) {
  const [sortKey, setSortKey] = useState<SortKey>('pnl')
  const [sortDir, setSortDir] = useState<SortDir>('desc')

  const sorted = [...pods].sort((a, b) => {
    const diff = a[sortKey] - b[sortKey]
    return sortDir === 'desc' ? -diff : diff
  })

  const handleSort = (key: SortKey) => {
    if (key === sortKey) {
      setSortDir((d) => (d === 'desc' ? 'asc' : 'desc'))
    } else {
      setSortKey(key)
      setSortDir('desc')
    }
  }

  const ColHeader = ({ k, label }: { k: SortKey; label: string }) => (
    <button
      onClick={() => handleSort(k)}
      className={cn(
        'text-[10px] uppercase tracking-widest transition-colors text-right',
        sortKey === k ? 'text-[#7C3AED]' : 'text-white/20 hover:text-white/40'
      )}
    >
      {label}
      {sortKey === k && (sortDir === 'desc' ? ' ↓' : ' ↑')}
    </button>
  )

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: 0.2 }}
      className="rounded-2xl overflow-hidden"
      style={{
        background: 'rgba(255,255,255,0.02)',
        border: '1px solid rgba(255,255,255,0.07)',
      }}
    >
      <div className="flex items-center justify-between px-5 py-4 border-b border-white/5">
        <div className="flex items-center gap-2">
          <Layers className="w-4 h-4 text-white/40" />
          <h3 className="text-sm font-bold text-white">Pod Leaderboard</h3>
        </div>
        <span className="text-[11px] text-white/20">Click headers to sort</span>
      </div>

      {/* Column headers */}
      <div className="grid grid-cols-5 px-5 py-2.5 border-b border-white/5">
        <span className="text-[10px] uppercase tracking-widest text-white/20">Pod</span>
        <ColHeader k="allocation" label="Alloc" />
        <ColHeader k="signalStrength" label="Signal" />
        <ColHeader k="sharpe" label="Sharpe" />
        <ColHeader k="pnl" label="YTD P&L" />
      </div>

      {/* Rows */}
      <div className="divide-y divide-white/5">
        {sorted.map((pod, i) => (
          <motion.div
            key={pod.id}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.25 + i * 0.05 }}
            className="grid grid-cols-5 px-5 py-3 items-center text-xs hover:bg-white/[0.02] transition-colors"
          >
            {/* Pod name */}
            <div className="flex items-center gap-2 min-w-0">
              <div
                className="w-1.5 h-4 rounded-full flex-shrink-0"
                style={{ background: pod.color, boxShadow: `0 0 4px ${pod.color}60` }}
              />
              <div className="min-w-0">
                <div className="font-bold text-white/80 truncate">{pod.shortName}</div>
                <div className="text-[10px] text-white/30 truncate hidden sm:block">{pod.name}</div>
              </div>
            </div>

            {/* Allocation */}
            <span className="text-right text-white/50 tabular-nums">
              {pod.allocation.toFixed(1)}%
            </span>

            {/* Signal strength */}
            <div className="text-right">
              <div className="inline-flex items-center gap-1">
                <div
                  className="h-1 rounded-full"
                  style={{
                    width: `${Math.round(pod.signalStrength * 0.32)}px`,
                    background: pod.color,
                    minWidth: '8px',
                  }}
                />
                <span className="text-white/50 tabular-nums">{pod.signalStrength}%</span>
              </div>
            </div>

            {/* Sharpe */}
            <span className="text-right font-bold tabular-nums" style={{ color: pod.sharpe >= 2 ? '#00FF94' : pod.sharpe >= 1.5 ? '#FFB800' : '#FF3366' }}>
              {pod.sharpe.toFixed(2)}
            </span>

            {/* YTD P&L */}
            <div className="flex items-center justify-end gap-1">
              {pod.pnl >= 0
                ? <TrendingUp className="w-3 h-3 text-[#00FF94]" />
                : <TrendingDown className="w-3 h-3 text-[#FF3366]" />}
              <span
                className="font-black tabular-nums"
                style={{ color: pod.pnl >= 0 ? '#00FF94' : '#FF3366' }}
              >
                {pod.pnl >= 0 ? '+' : ''}{pod.pnl.toFixed(1)}%
              </span>
            </div>
          </motion.div>
        ))}
      </div>
    </motion.div>
  )
}

export default function PodsPage() {
  const { data: apiStrategies } = useStrategies()

  // Map API data to StrategyPod shape, or fall back to static
  const pods: StrategyPod[] = apiStrategies
    ? apiStrategies.pods.map((p) => {
        const staticPod = STRATEGY_PODS.find((s) => s.id === p.pod_name || s.id === p.pod_name.replace('_', '-'))
        return {
          id: p.pod_name,
          name: p.display_name,
          shortName: staticPod?.shortName ?? p.pod_name.slice(0, 3).toUpperCase(),
          allocation: p.regime_allocation * 100,
          signal: staticPod?.signal ?? 0,
          signalStrength: Math.round(p.win_rate * 100),
          pnl: p.ytd_return,
          sharpe: p.sharpe_ratio,
          sparkline: staticPod?.sparkline ?? [],
          color: staticPod?.color ?? '#888',
          glowColor: staticPod?.glowColor ?? 'rgba(136,136,136,0.3)',
          description: p.description,
          regime: staticPod?.regime ?? [],
        }
      })
    : STRATEGY_PODS

  return (
    <div className="p-4 sm:p-6 space-y-6">
      {/* Page header */}
      <div>
        <h1 className="text-xl font-black text-white tracking-tight">Strategy Pods</h1>
        <p className="text-xs text-white/30 mt-0.5">
          9 independent alpha engines with regime-adaptive weights
        </p>
      </div>

      {/* Charts row */}
      <div className="grid lg:grid-cols-2 gap-4">
        <PodComparisonChart pods={pods} />
        <PodRadarChart pods={pods} />
      </div>

      {/* Leaderboard */}
      <PodLeaderboard pods={pods} />

      {/* Full pods grid (reused component) */}
      <div>
        <h2 className="text-base font-bold text-white mb-4 px-1">Pod Detail Cards</h2>
        <StrategyPodsGrid />
      </div>
    </div>
  )
}
