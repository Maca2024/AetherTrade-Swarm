'use client'

import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import {
  TrendingUp,
  TrendingDown,
  Activity,
  BarChart2,
  DollarSign,
  Zap,
  RefreshCw,
  AlertCircle,
} from 'lucide-react'
import dynamic from 'next/dynamic'
import { getLiveMetrics, REGIMES, STRATEGY_PODS } from '@/lib/data'
import { useRegime, usePerformance, useStrategies, useApiStatus } from '@/lib/hooks'
import { cn } from '@/lib/utils'

const PerformanceDashboard = dynamic(() => import('@/components/PerformanceDashboard'), {
  ssr: false,
  loading: () => (
    <div className="h-96 rounded-2xl bg-white/3 animate-pulse mx-6 mb-6" />
  ),
})

const RegimeIndicator = dynamic(() => import('@/components/RegimeIndicator'), {
  ssr: false,
})

interface SummaryCard {
  label: string
  value: string
  sub: string
  positive: boolean
  icon: React.ReactNode
  color: string
}

function QuickStatCard({
  label,
  value,
  sub,
  positive,
  icon,
  color,
  index,
}: SummaryCard & { index: number }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: index * 0.07, ease: [0.16, 1, 0.3, 1] }}
      className="relative rounded-2xl p-5"
      style={{
        background: 'rgba(255,255,255,0.03)',
        border: '1px solid rgba(255,255,255,0.07)',
      }}
    >
      {/* Top gradient line */}
      <div
        className="absolute top-0 left-4 right-4 h-px rounded-full"
        style={{ background: `linear-gradient(90deg, transparent, ${color}60, transparent)` }}
      />

      <div className="flex items-start justify-between mb-3">
        <div
          className="w-9 h-9 rounded-xl flex items-center justify-center"
          style={{ background: `${color}15`, border: `1px solid ${color}25` }}
        >
          <div style={{ color }}>{icon}</div>
        </div>
        <span
          className={cn(
            'text-[11px] font-semibold px-2 py-0.5 rounded-full',
            positive
              ? 'text-[#00FF94] bg-[#00FF94]/10'
              : 'text-[#FF3366] bg-[#FF3366]/10'
          )}
        >
          {sub}
        </span>
      </div>

      <div className="text-2xl font-black mb-0.5" style={{ color }}>
        {value}
      </div>
      <div className="text-xs text-white/40 uppercase tracking-wider">{label}</div>
    </motion.div>
  )
}

function ActiveSignalsTable() {
  const { data: apiStrategies } = useStrategies()
  const pods = apiStrategies
    ? apiStrategies.pods.slice(0, 5).map((p) => ({
        name: p.display_name,
        signal: p.win_rate > 0.55 ? 'LONG' : p.win_rate < 0.45 ? 'SHORT' : 'NEUTRAL',
        strength: Math.round(p.win_rate * 100),
        pnl: p.ytd_return,
        color:
          p.pod_name === 'momentum'
            ? '#00D4FF'
            : p.pod_name === 'mean_reversion'
            ? '#8B5CF6'
            : p.pod_name === 'macro'
            ? '#FFB800'
            : p.pod_name === 'stat_arb'
            ? '#00FF94'
            : '#FF3366',
      }))
    : STRATEGY_PODS.slice(0, 5).map((p) => ({
        name: p.name,
        signal: p.signal > 0.2 ? 'LONG' : p.signal < -0.2 ? 'SHORT' : 'NEUTRAL',
        strength: p.signalStrength,
        pnl: p.pnl,
        color: p.color,
      }))

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: 0.35 }}
      className="rounded-2xl p-5"
      style={{
        background: 'rgba(255,255,255,0.02)',
        border: '1px solid rgba(255,255,255,0.07)',
      }}
    >
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-bold text-white">Active Signals</h3>
        <span className="text-[11px] text-white/30 bg-white/5 px-2 py-0.5 rounded-full">
          Top 5 pods
        </span>
      </div>

      <div className="space-y-2">
        {pods.map((pod, i) => (
          <motion.div
            key={pod.name}
            initial={{ opacity: 0, x: -12 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.4 + i * 0.06 }}
            className="flex items-center justify-between py-2 border-b border-white/5 last:border-0"
          >
            <div className="flex items-center gap-3 min-w-0">
              <div
                className="w-1.5 h-6 rounded-full flex-shrink-0"
                style={{ background: pod.color }}
              />
              <span className="text-sm text-white/70 truncate">{pod.name}</span>
            </div>
            <div className="flex items-center gap-4 flex-shrink-0">
              <span
                className={cn(
                  'text-[11px] font-bold px-2 py-0.5 rounded tracking-wider',
                  pod.signal === 'LONG'
                    ? 'text-[#00FF94] bg-[#00FF94]/10'
                    : pod.signal === 'SHORT'
                    ? 'text-[#FF3366] bg-[#FF3366]/10'
                    : 'text-[#FFB800] bg-[#FFB800]/10'
                )}
              >
                {pod.signal}
              </span>
              <span className="text-xs text-white/40 w-10 text-right tabular-nums">
                {pod.strength}%
              </span>
              <span
                className="text-xs font-bold w-14 text-right tabular-nums"
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

function SystemStatusBar() {
  const { isConnected, health } = useApiStatus()

  const services = health?.services ?? [
    { name: 'Regime Detector', status: 'online' },
    { name: 'Signal Engine', status: 'online' },
    { name: 'Risk Manager', status: 'online' },
    { name: 'Portfolio Optimizer', status: 'online' },
  ]

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ delay: 0.5 }}
      className="rounded-2xl p-4"
      style={{
        background: 'rgba(255,255,255,0.02)',
        border: '1px solid rgba(255,255,255,0.07)',
      }}
    >
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-bold text-white">System Status</h3>
        {isConnected ? (
          <div className="flex items-center gap-1.5 text-[11px] text-[#00FF94]">
            <div className="w-1.5 h-1.5 rounded-full bg-[#00FF94] animate-pulse" />
            All Systems Operational
          </div>
        ) : (
          <div className="flex items-center gap-1.5 text-[11px] text-[#FFB800]">
            <AlertCircle className="w-3 h-3" />
            Demo Mode
          </div>
        )}
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
        {services.slice(0, 4).map((svc) => {
          const ok = svc.status === 'online' || svc.status === 'ok'
          return (
            <div
              key={svc.name}
              className="flex items-center gap-2 px-2.5 py-2 rounded-xl"
              style={{
                background: ok ? 'rgba(0,255,148,0.05)' : 'rgba(255,51,102,0.05)',
                border: `1px solid ${ok ? 'rgba(0,255,148,0.15)' : 'rgba(255,51,102,0.15)'}`,
              }}
            >
              <div
                className="w-1.5 h-1.5 rounded-full flex-shrink-0"
                style={{ background: ok ? '#00FF94' : '#FF3366' }}
              />
              <span className="text-[10px] text-white/50 truncate">{svc.name}</span>
            </div>
          )
        })}
      </div>
    </motion.div>
  )
}

export default function DashboardOverviewPage() {
  const { data: apiRegime } = useRegime()
  const { data: apiPerf } = usePerformance()
  const [liveMetrics, setLiveMetrics] = useState(getLiveMetrics())
  const [lastUpdated, setLastUpdated] = useState(new Date())

  // Live-tick metrics every 3s
  useEffect(() => {
    const id = setInterval(() => {
      setLiveMetrics(getLiveMetrics())
      setLastUpdated(new Date())
    }, 3000)
    return () => clearInterval(id)
  }, [])

  // Build summary cards from API or simulated data
  const nav = apiPerf
    ? `$${(10000 * (1 + apiPerf.total_return / 100)).toFixed(0)}`
    : '$28,740'

  const dailyPnl = apiPerf
    ? `${apiPerf.mtd_return >= 0 ? '+' : ''}${apiPerf.mtd_return.toFixed(2)}%`
    : `${liveMetrics.dailyPnl >= 0 ? '+' : ''}${liveMetrics.dailyPnl.toFixed(2)}%`

  const winRate = apiPerf
    ? `${(apiPerf.win_rate * 100).toFixed(1)}%`
    : `${liveMetrics.winRate.toFixed(1)}%`

  const activeRegimePods =
    apiRegime?.regime === 'bull'
      ? 6
      : apiRegime?.regime === 'bear'
      ? 4
      : apiRegime?.regime === 'crisis'
      ? 3
      : 7

  const summaryCards: SummaryCard[] = [
    {
      label: 'Net Asset Value',
      value: nav,
      sub: `+${liveMetrics.totalReturn.toFixed(1)}% all-time`,
      positive: true,
      icon: <DollarSign className="w-4 h-4" />,
      color: '#00D4FF',
    },
    {
      label: 'Daily P&L',
      value: dailyPnl,
      sub: 'MTD return',
      positive: parseFloat(dailyPnl) >= 0,
      icon: <TrendingUp className="w-4 h-4" />,
      color: parseFloat(dailyPnl) >= 0 ? '#00FF94' : '#FF3366',
    },
    {
      label: 'Active Signals',
      value: `${activeRegimePods}/9`,
      sub: 'pods live',
      positive: true,
      icon: <Activity className="w-4 h-4" />,
      color: '#7C3AED',
    },
    {
      label: 'Win Rate',
      value: winRate,
      sub: `Sharpe ${liveMetrics.sharpe.toFixed(2)}`,
      positive: parseFloat(winRate) > 50,
      icon: <BarChart2 className="w-4 h-4" />,
      color: '#FFB800',
    },
  ]

  return (
    <div className="p-4 sm:p-6 space-y-6">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-black text-white tracking-tight">Overview</h1>
          <p className="text-xs text-white/30 mt-0.5">
            Last updated:{' '}
            {new Intl.DateTimeFormat('en-US', {
              hour: '2-digit',
              minute: '2-digit',
              second: '2-digit',
              timeZone: 'Europe/Amsterdam',
            }).format(lastUpdated)}{' '}
            CET
          </p>
        </div>
        <button
          onClick={() => {
            setLiveMetrics(getLiveMetrics())
            setLastUpdated(new Date())
          }}
          className="flex items-center gap-2 px-3 py-1.5 rounded-xl text-xs text-white/40 hover:text-white bg-white/5 hover:bg-white/10 border border-white/5 hover:border-white/15 transition-all"
          aria-label="Refresh data"
        >
          <RefreshCw className="w-3 h-3" />
          Refresh
        </button>
      </div>

      {/* Quick stats grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {summaryCards.map((card, i) => (
          <QuickStatCard key={card.label} {...card} index={i} />
        ))}
      </div>

      {/* Regime + Signals row */}
      <div className="grid lg:grid-cols-5 gap-4">
        <div className="lg:col-span-3">
          <ActiveSignalsTable />
        </div>

        {/* Open positions placeholder (minimal, matches Supabase schema) */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.3 }}
          className="lg:col-span-2 rounded-2xl p-5"
          style={{
            background: 'rgba(255,255,255,0.02)',
            border: '1px solid rgba(255,255,255,0.07)',
          }}
        >
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-bold text-white">Open Positions</h3>
            <span className="text-[11px] text-white/30 bg-white/5 px-2 py-0.5 rounded-full">
              Paper trading
            </span>
          </div>

          <div className="space-y-2">
            {[
              { ticker: 'SPY', side: 'LONG', size: '$4,200', pnl: '+1.34%', color: '#00FF94' },
              { ticker: 'QQQ', side: 'LONG', size: '$2,800', pnl: '+0.87%', color: '#00FF94' },
              { ticker: 'GLD', side: 'SHORT', size: '$1,400', pnl: '-0.22%', color: '#FF3366' },
              { ticker: 'TLT', side: 'LONG', size: '$3,100', pnl: '+0.41%', color: '#00FF94' },
            ].map((pos, i) => (
              <motion.div
                key={pos.ticker}
                initial={{ opacity: 0, x: 12 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.4 + i * 0.06 }}
                className="flex items-center justify-between py-2 border-b border-white/5 last:border-0"
              >
                <div className="flex items-center gap-2">
                  <span className="text-sm font-bold text-white">{pos.ticker}</span>
                  <span
                    className={cn(
                      'text-[10px] font-bold px-1.5 py-0.5 rounded',
                      pos.side === 'LONG'
                        ? 'text-[#00FF94] bg-[#00FF94]/10'
                        : 'text-[#FF3366] bg-[#FF3366]/10'
                    )}
                  >
                    {pos.side}
                  </span>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-xs text-white/40">{pos.size}</span>
                  <span className="text-xs font-bold tabular-nums" style={{ color: pos.color }}>
                    {pos.pnl}
                  </span>
                </div>
              </motion.div>
            ))}
          </div>

          <div className="mt-4 pt-3 border-t border-white/5 flex items-center justify-between">
            <span className="text-xs text-white/30">4 positions open</span>
            <span className="text-xs font-bold text-[#00FF94]">+$347.20 unrealized</span>
          </div>
        </motion.div>
      </div>

      {/* System status */}
      <SystemStatusBar />

      {/* Performance dashboard (reused component) */}
      <div>
        <h2 className="text-base font-bold text-white mb-4 px-1">Performance</h2>
        <PerformanceDashboard />
      </div>
    </div>
  )
}
