'use client'

import { useState } from 'react'
import { motion } from 'framer-motion'
import {
  TrendingUp,
  TrendingDown,
  Minus,
  AlertTriangle,
  Clock,
  Calendar,
  BarChart2,
  Info,
} from 'lucide-react'
import dynamic from 'next/dynamic'
import { REGIMES, type RegimeState } from '@/lib/data'
import { useRegime } from '@/lib/hooks'
import { cn } from '@/lib/utils'

const RegimeIndicator = dynamic(() => import('@/components/RegimeIndicator'), { ssr: false })

// Mock regime history — will connect to API later
const REGIME_HISTORY: Array<{
  from: string
  to: string
  regime: string
  label: string
  duration: string
  return: string
  color: string
}> = [
  {
    from: '2026-01-02',
    to: '2026-02-14',
    regime: 'bull',
    label: 'BULL MARKET',
    duration: '43 days',
    return: '+12.4%',
    color: '#00FF94',
  },
  {
    from: '2026-02-15',
    to: '2026-02-28',
    regime: 'range',
    label: 'RANGE-BOUND',
    duration: '13 days',
    return: '+1.2%',
    color: '#00D4FF',
  },
  {
    from: '2026-03-01',
    to: '2026-03-12',
    regime: 'bear',
    label: 'BEAR MARKET',
    duration: '12 days',
    return: '-2.8%',
    color: '#FF3366',
  },
  {
    from: '2026-03-13',
    to: '2026-03-18',
    regime: 'crisis',
    label: 'CRISIS MODE',
    duration: '5 days',
    return: '-1.1%',
    color: '#FFB800',
  },
  {
    from: '2026-03-19',
    to: '2026-04-07',
    regime: 'bull',
    label: 'BULL MARKET',
    duration: '19 days',
    return: '+6.7%',
    color: '#00FF94',
  },
  {
    from: '2026-04-08',
    to: 'Present',
    regime: 'bull',
    label: 'BULL MARKET',
    duration: 'Current',
    return: '+2.1%',
    color: '#00FF94',
  },
]

const REGIME_ICONS = {
  bull: TrendingUp,
  bear: TrendingDown,
  crisis: AlertTriangle,
  range: Minus,
}

const REGIME_DESCRIPTIONS: Record<string, string> = {
  bull: 'Trend-following and momentum strategies are overweighted. Risk-on allocation with elevated equity exposure. Mean-reversion pods operate at reduced capacity.',
  bear: 'Defensive posture with short bias. Volatility and options strategies elevated. Capital preservation via reduced gross exposure and inverse positions.',
  crisis: 'Tail-risk event protocol active. Kill switches engaged. Maximum capital preservation mode with near-zero directional exposure.',
  range: 'Low directional bias environment. Mean-reversion and statistical arbitrage strategies optimal. Tight range-bound signals dominate.',
}

function RegimeProbabilityBreakdown({
  apiRegime,
}: {
  apiRegime: ReturnType<typeof useRegime>['data']
}) {
  // Build probabilities — from API or derived from static demo
  const probabilities: Record<string, number> = apiRegime?.probabilities ?? {
    bull: 0.61,
    range: 0.22,
    bear: 0.12,
    crisis: 0.05,
  }

  const entries = Object.entries(probabilities).sort(([, a], [, b]) => b - a)

  const colorMap: Record<string, string> = {
    bull: '#00FF94',
    range: '#00D4FF',
    bear: '#FF3366',
    crisis: '#FFB800',
  }
  const labelMap: Record<string, string> = {
    bull: 'BULL MARKET',
    range: 'RANGE-BOUND',
    bear: 'BEAR MARKET',
    crisis: 'CRISIS MODE',
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: 0.2 }}
      className="rounded-2xl p-5"
      style={{
        background: 'rgba(255,255,255,0.02)',
        border: '1px solid rgba(255,255,255,0.07)',
      }}
    >
      <div className="flex items-center gap-2 mb-5">
        <BarChart2 className="w-4 h-4 text-white/40" />
        <h3 className="text-sm font-bold text-white">Regime Probabilities</h3>
        <div className="ml-auto flex items-center gap-1 text-[11px] text-white/30">
          <Info className="w-3 h-3" />
          HMM posterior
        </div>
      </div>

      <div className="space-y-4">
        {entries.map(([regime, prob], i) => {
          const pct = Math.round(prob * 100)
          const color = colorMap[regime] ?? '#888'
          const label = labelMap[regime] ?? regime.toUpperCase()
          const Icon = REGIME_ICONS[regime as keyof typeof REGIME_ICONS] ?? Minus

          return (
            <motion.div
              key={regime}
              initial={{ opacity: 0, x: -12 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.25 + i * 0.08 }}
              className="space-y-1.5"
            >
              <div className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-2">
                  <Icon className="w-3.5 h-3.5" style={{ color }} />
                  <span className="text-white/60 font-medium">{label}</span>
                </div>
                <span className="font-black tabular-nums" style={{ color }}>
                  {pct}%
                </span>
              </div>
              <div className="h-2 bg-white/5 rounded-full overflow-hidden">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${pct}%` }}
                  transition={{ duration: 1, delay: 0.3 + i * 0.08, ease: 'easeOut' }}
                  className="h-full rounded-full"
                  style={{
                    background: `linear-gradient(90deg, ${color}80, ${color})`,
                    boxShadow: `0 0 8px ${color}50`,
                  }}
                />
              </div>
            </motion.div>
          )
        })}
      </div>

      {/* Explanation */}
      <div
        className="mt-5 p-3 rounded-xl text-[11px] text-white/40 leading-relaxed"
        style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.05)' }}
      >
        Posterior probabilities from the Hidden Markov Model (HMM) regime classifier. Updated every 10 seconds using real-time market microstructure and factor signals.
      </div>
    </motion.div>
  )
}

function RegimeHistoryTable() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: 0.3 }}
      className="rounded-2xl overflow-hidden"
      style={{
        background: 'rgba(255,255,255,0.02)',
        border: '1px solid rgba(255,255,255,0.07)',
      }}
    >
      <div className="flex items-center justify-between px-5 py-4 border-b border-white/5">
        <div className="flex items-center gap-2">
          <Calendar className="w-4 h-4 text-white/40" />
          <h3 className="text-sm font-bold text-white">Regime History</h3>
        </div>
        <span className="text-[11px] text-white/30 bg-white/5 px-2 py-0.5 rounded-full">
          YTD 2026
        </span>
      </div>

      {/* Table header */}
      <div className="grid grid-cols-5 px-5 py-2 text-[10px] text-white/20 uppercase tracking-widest border-b border-white/5">
        <span>Regime</span>
        <span>From</span>
        <span>To</span>
        <span className="text-center">Duration</span>
        <span className="text-right">Return</span>
      </div>

      {/* Table rows */}
      <div className="divide-y divide-white/5">
        {REGIME_HISTORY.map((row, i) => {
          const Icon = REGIME_ICONS[row.regime as keyof typeof REGIME_ICONS] ?? Minus
          const isCurrent = row.to === 'Present'

          return (
            <motion.div
              key={`${row.from}-${row.regime}`}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.35 + i * 0.06 }}
              className={cn(
                'grid grid-cols-5 px-5 py-3 items-center text-xs',
                isCurrent && 'bg-white/[0.02]'
              )}
            >
              {/* Regime */}
              <div className="flex items-center gap-2">
                <div
                  className="w-1.5 h-1.5 rounded-full flex-shrink-0"
                  style={{ background: row.color, boxShadow: `0 0 4px ${row.color}` }}
                />
                <Icon className="w-3.5 h-3.5" style={{ color: row.color }} />
                <span className="font-medium text-white/70 hidden sm:inline">{row.label}</span>
                <span className="font-medium sm:hidden" style={{ color: row.color }}>
                  {row.regime.toUpperCase()}
                </span>
              </div>

              {/* From */}
              <span className="text-white/40 tabular-nums">
                {new Intl.DateTimeFormat('en-US', {
                  month: 'short',
                  day: 'numeric',
                  timeZone: 'Europe/Amsterdam',
                }).format(new Date(row.from))}
              </span>

              {/* To */}
              <span className="text-white/40 tabular-nums">
                {isCurrent ? (
                  <span className="flex items-center gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-[#00FF94] animate-pulse inline-block" />
                    Now
                  </span>
                ) : (
                  new Intl.DateTimeFormat('en-US', {
                    month: 'short',
                    day: 'numeric',
                    timeZone: 'Europe/Amsterdam',
                  }).format(new Date(row.to))
                )}
              </span>

              {/* Duration */}
              <div className="flex items-center justify-center gap-1 text-white/40">
                <Clock className="w-3 h-3 flex-shrink-0" />
                {row.duration}
              </div>

              {/* Return */}
              <span
                className="text-right font-black tabular-nums"
                style={{
                  color: row.return.startsWith('+') ? '#00FF94' : '#FF3366',
                }}
              >
                {row.return}
              </span>
            </motion.div>
          )
        })}
      </div>
    </motion.div>
  )
}

function CurrentRegimeDetail({
  apiRegime,
}: {
  apiRegime: ReturnType<typeof useRegime>['data']
}) {
  const regime = apiRegime?.regime ?? 'bull'
  const confidence = apiRegime ? Math.round(apiRegime.confidence * 100) : 61
  const durationDays = apiRegime?.duration_days ?? 1

  const colorMap: Record<string, string> = {
    bull: '#00FF94',
    range: '#00D4FF',
    bear: '#FF3366',
    crisis: '#FFB800',
  }
  const color = colorMap[regime] ?? '#00D4FF'

  const signalImpact = apiRegime?.signal_impact ?? {
    momentum: 'overweight',
    mean_reversion: 'neutral',
    macro: 'overweight',
    stat_arb: 'underweight',
    options_vol: 'neutral',
  }

  const impactColor: Record<string, string> = {
    overweight: '#00FF94',
    underweight: '#FF3366',
    neutral: '#FFB800',
    elevated: '#00D4FF',
    reduced: '#FF3366',
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: 0.15 }}
      className="rounded-2xl p-5"
      style={{
        background: `linear-gradient(135deg, ${color}06 0%, rgba(255,255,255,0.02) 100%)`,
        border: `1px solid ${color}20`,
      }}
    >
      <div className="flex items-start justify-between mb-4">
        <div>
          <div className="text-[11px] text-white/30 uppercase tracking-widest mb-1">Current Regime</div>
          <div className="text-2xl font-black" style={{ color }}>
            {regime.toUpperCase()}
          </div>
        </div>
        <div className="text-right">
          <div className="text-[11px] text-white/30 mb-1">Duration</div>
          <div className="text-lg font-black text-white">{durationDays}d</div>
        </div>
      </div>

      <p className="text-xs text-white/50 leading-relaxed mb-4">
        {REGIME_DESCRIPTIONS[regime]}
      </p>

      {/* Signal impact grid */}
      <div className="space-y-1">
        <div className="text-[10px] text-white/20 uppercase tracking-widest mb-2">
          Strategy Impact
        </div>
        {Object.entries(signalImpact).slice(0, 6).map(([strat, impact]) => (
          <div key={strat} className="flex items-center justify-between py-1">
            <span className="text-[11px] text-white/40 capitalize">
              {strat.replace(/_/g, ' ')}
            </span>
            <span
              className="text-[11px] font-bold capitalize px-2 py-0.5 rounded-full"
              style={{
                color: impactColor[impact] ?? '#888',
                background: `${impactColor[impact] ?? '#888'}15`,
              }}
            >
              {impact}
            </span>
          </div>
        ))}
      </div>
    </motion.div>
  )
}

export default function RegimePage() {
  const { data: apiRegime } = useRegime()

  return (
    <div className="p-4 sm:p-6 space-y-6">
      {/* Page header */}
      <div>
        <h1 className="text-xl font-black text-white tracking-tight">Regime Analysis</h1>
        <p className="text-xs text-white/30 mt-0.5">
          Hidden Markov Model regime detection with real-time posterior probabilities
        </p>
      </div>

      {/* Regime bar (reused component — full width) */}
      <RegimeIndicator />

      {/* Main grid */}
      <div className="grid lg:grid-cols-3 gap-4">
        {/* Left col: current regime detail + probabilities */}
        <div className="space-y-4">
          <CurrentRegimeDetail apiRegime={apiRegime} />
          <RegimeProbabilityBreakdown apiRegime={apiRegime} />
        </div>

        {/* Right: history table (spans 2 cols) */}
        <div className="lg:col-span-2">
          <RegimeHistoryTable />
        </div>
      </div>

      {/* Regime info cards */}
      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {REGIMES.map((regime, i) => {
          const Icon = REGIME_ICONS[regime.type]
          const isActive = (apiRegime?.regime ?? 'bull') === regime.type

          return (
            <motion.div
              key={regime.type}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.4 + i * 0.07 }}
              className="rounded-2xl p-4"
              style={{
                background: isActive
                  ? `linear-gradient(135deg, ${regime.color}08 0%, rgba(255,255,255,0.02) 100%)`
                  : 'rgba(255,255,255,0.02)',
                border: `1px solid ${isActive ? regime.color + '30' : 'rgba(255,255,255,0.07)'}`,
              }}
            >
              <div className="flex items-center gap-2 mb-2">
                <Icon className="w-4 h-4" style={{ color: regime.color }} />
                <span className="text-xs font-bold" style={{ color: regime.color }}>
                  {regime.label}
                </span>
                {isActive && (
                  <div
                    className="ml-auto w-1.5 h-1.5 rounded-full animate-pulse"
                    style={{ background: regime.color }}
                  />
                )}
              </div>
              <p className="text-[11px] text-white/40 leading-relaxed">
                {regime.description}
              </p>
              <div className="mt-3 flex items-center justify-between">
                <span className="text-[10px] text-white/20">Confidence</span>
                <span className="text-xs font-bold" style={{ color: regime.color }}>
                  {regime.confidence}%
                </span>
              </div>
            </motion.div>
          )
        })}
      </div>
    </div>
  )
}
