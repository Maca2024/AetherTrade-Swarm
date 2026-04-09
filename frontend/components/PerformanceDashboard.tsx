'use client'

import { useState, useEffect, useRef } from 'react'
import { motion } from 'framer-motion'
import { useInView } from 'react-intersection-observer'
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ReferenceLine,
} from 'recharts'
import { TrendingUp, Award, ShieldCheck, Target, BarChart2, Zap } from 'lucide-react'
import { generateEquityCurve, PERFORMANCE_METRICS, type MetricCard as MetricCardType } from '@/lib/data'
import { usePerformance } from '@/lib/hooks'
import { cn } from '@/lib/utils'

const equityData = generateEquityCurve(365)
// Sample every 5th point for performance
const chartData = equityData.filter((_, i) => i % 3 === 0)

interface MetricProps {
  label: string
  value: string
  change: string
  positive: boolean
  index: number
  inView: boolean
  icon: React.ReactNode
  color: string
}

function MetricCard({ label, value, change, positive, index, inView, icon, color }: MetricProps) {
  const [displayed, setDisplayed] = useState('--')

  useEffect(() => {
    if (!inView) return
    const timeout = setTimeout(() => {
      setDisplayed(value)
    }, index * 120)
    return () => clearTimeout(timeout)
  }, [inView, value, index])

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={inView ? { opacity: 1, y: 0 } : {}}
      transition={{ duration: 0.5, delay: index * 0.1 }}
      className="relative rounded-2xl p-5 group"
      style={{
        background: 'rgba(255,255,255,0.03)',
        border: '1px solid rgba(255,255,255,0.07)',
        transition: 'all 0.3s',
      }}
      whileHover={{
        scale: 1.02,
        borderColor: color + '40',
        boxShadow: `0 0 20px ${color}20`,
      }}
    >
      <div className="flex items-start justify-between mb-3">
        <div
          className="w-8 h-8 rounded-lg flex items-center justify-center"
          style={{ background: color + '15', border: `1px solid ${color}30` }}
        >
          <div style={{ color }}>{icon}</div>
        </div>
        <motion.div
          key={displayed}
          initial={{ y: -10, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          className={cn(
            'text-xs px-2 py-0.5 rounded-full font-medium',
            positive ? 'text-[#00FF94] bg-[#00FF94]/10' : 'text-[#FF3366] bg-[#FF3366]/10'
          )}
        >
          {change}
        </motion.div>
      </div>

      <motion.div
        key={`val-${displayed}`}
        initial={{ scale: 0.9, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ duration: 0.4 }}
        className="text-2xl font-black mb-1"
        style={{ color, textShadow: `0 0 20px ${color}40` }}
      >
        {displayed}
      </motion.div>

      <div className="text-xs text-white/40 uppercase tracking-wider">{label}</div>

      {/* Bottom glow line */}
      <div
        className="absolute bottom-0 left-4 right-4 h-px opacity-0 group-hover:opacity-100 transition-opacity duration-300"
        style={{ background: `linear-gradient(90deg, transparent, ${color}60, transparent)` }}
      />
    </motion.div>
  )
}

const METRIC_ICONS = [
  <TrendingUp key="1" className="w-4 h-4" />,
  <Award key="2" className="w-4 h-4" />,
  <ShieldCheck key="3" className="w-4 h-4" />,
  <Target key="4" className="w-4 h-4" />,
  <BarChart2 key="5" className="w-4 h-4" />,
  <Zap key="6" className="w-4 h-4" />,
]

const METRIC_COLORS = ['#00FF94', '#00D4FF', '#FFB800', '#8B5CF6', '#FF3366', '#F97316']

interface CustomTooltipProps {
  active?: boolean
  payload?: Array<{ name: string; value: number; color: string }>
  label?: string
}

function CustomTooltip({ active, payload, label }: CustomTooltipProps) {
  if (!active || !payload?.length) return null

  return (
    <div
      className="rounded-xl p-3 text-xs"
      style={{
        background: 'rgba(7, 7, 15, 0.95)',
        border: '1px solid rgba(0, 212, 255, 0.2)',
        backdropFilter: 'blur(20px)',
        boxShadow: '0 8px 32px rgba(0,0,0,0.5)',
      }}
    >
      <p className="text-white/40 mb-2 font-medium">{label}</p>
      {payload.map((entry) => (
        <div key={entry.name} className="flex items-center justify-between gap-4 mb-1">
          <div className="flex items-center gap-1.5">
            <div className="w-2 h-2 rounded-full" style={{ background: entry.color }} />
            <span className="text-white/60">{entry.name}</span>
          </div>
          <span className="font-bold tabular-nums" style={{ color: entry.color }}>
            ${entry.value.toFixed(0)}
          </span>
        </div>
      ))}
    </div>
  )
}

export default function PerformanceDashboard() {
  const [ref, inView] = useInView({ threshold: 0.15, triggerOnce: true })
  const { data: apiPerf } = usePerformance()

  // Build metrics from API data or fallback to static
  const displayMetrics: MetricCardType[] = apiPerf
    ? [
        {
          label: 'Total Return',
          value: `${apiPerf.total_return >= 0 ? '+' : ''}${apiPerf.total_return.toFixed(1)}%`,
          change: `${apiPerf.ytd_return >= 0 ? '+' : ''}${apiPerf.ytd_return.toFixed(1)}% YTD`,
          positive: apiPerf.total_return >= 0,
        },
        {
          label: 'Sharpe Ratio',
          value: apiPerf.sharpe_ratio.toFixed(2),
          change: `Sortino ${apiPerf.sortino_ratio.toFixed(2)}`,
          positive: apiPerf.sharpe_ratio >= 1.0,
        },
        {
          label: 'Max Drawdown',
          value: `${apiPerf.max_drawdown.toFixed(1)}%`,
          change: `Current ${apiPerf.current_drawdown.toFixed(1)}%`,
          positive: apiPerf.max_drawdown > -10,
        },
        {
          label: 'Win Rate',
          value: `${(apiPerf.win_rate * 100).toFixed(1)}%`,
          change: `PF ${apiPerf.profit_factor.toFixed(2)}`,
          positive: apiPerf.win_rate > 0.5,
        },
        {
          label: 'Alpha (ann.)',
          value: `${apiPerf.alpha >= 0 ? '+' : ''}${apiPerf.alpha.toFixed(1)}%`,
          change: 'vs S&P 500',
          positive: apiPerf.alpha >= 0,
        },
        {
          label: 'Sortino Ratio',
          value: apiPerf.sortino_ratio.toFixed(2),
          change: `Beta ${apiPerf.beta.toFixed(2)}`,
          positive: apiPerf.sortino_ratio >= 1.5,
        },
      ]
    : PERFORMANCE_METRICS

  const [activeLines, setActiveLines] = useState({
    oracle: true,
    sp500: true,
    balanced: false,
  })

  const toggleLine = (key: keyof typeof activeLines) => {
    setActiveLines(prev => ({ ...prev, [key]: !prev[key] }))
  }

  const lastPoint = chartData[chartData.length - 1]
  const oracleReturn = ((lastPoint.oracle - 10000) / 10000 * 100).toFixed(1)
  const spReturn = ((lastPoint.sp500 - 10000) / 10000 * 100).toFixed(1)
  const balReturn = ((lastPoint.balanced - 10000) / 10000 * 100).toFixed(1)

  return (
    <section
      ref={ref}
      className="py-20 px-4 sm:px-6 max-w-7xl mx-auto"
      aria-labelledby="performance-heading"
    >
      {/* Section header */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={inView ? { opacity: 1, y: 0 } : {}}
        transition={{ duration: 0.6 }}
        className="mb-12 text-center"
      >
        <div className="flex items-center justify-center gap-3 mb-4">
          <div className="h-px w-16 bg-gradient-to-r from-transparent to-[#00FF94]/40" />
          <span className="text-xs tracking-widest text-[#00FF94] uppercase font-semibold">
            Live Performance
          </span>
          <div className="h-px w-16 bg-gradient-to-l from-transparent to-[#00FF94]/40" />
        </div>
        <h2
          id="performance-heading"
          className="text-4xl sm:text-5xl font-black tracking-tight mb-4"
          style={{
            background: 'linear-gradient(135deg, #FFFFFF 0%, #00FF94 100%)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            backgroundClip: 'text',
          }}
        >
          Performance Dashboard
        </h2>
        <p className="text-white/40 text-base max-w-xl mx-auto">
          365-day simulated track record. Risk-adjusted returns across all market conditions.
        </p>
      </motion.div>

      {/* Metrics grid */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3 mb-8">
        {displayMetrics.map((metric, i) => (
          <MetricCard
            key={metric.label}
            {...metric}
            index={i}
            inView={inView}
            icon={METRIC_ICONS[i]}
            color={METRIC_COLORS[i]}
          />
        ))}
      </div>

      {/* Chart */}
      <motion.div
        initial={{ opacity: 0, y: 30 }}
        animate={inView ? { opacity: 1, y: 0 } : {}}
        transition={{ duration: 0.7, delay: 0.3 }}
        className="rounded-2xl p-6"
        style={{
          background: 'rgba(255,255,255,0.02)',
          border: '1px solid rgba(255,255,255,0.07)',
          boxShadow: '0 20px 60px rgba(0,0,0,0.4)',
        }}
      >
        {/* Chart header */}
        <div className="flex items-center justify-between mb-6 flex-wrap gap-4">
          <div>
            <h3 className="text-lg font-bold text-white">Equity Curve</h3>
            <p className="text-xs text-white/40">Starting NAV: $10,000 | 365 days</p>
          </div>

          {/* Legend toggles */}
          <div className="flex items-center gap-4">
            {[
              { key: 'oracle' as const, label: 'AETHERTRADE-SWARM', color: '#00D4FF', ret: oracleReturn },
              { key: 'sp500' as const, label: 'S&P 500', color: '#FFB800', ret: spReturn },
              { key: 'balanced' as const, label: '60/40', color: '#8B5CF6', ret: balReturn },
            ].map(({ key, label, color, ret }) => (
              <button
                key={key}
                onClick={() => toggleLine(key)}
                className={cn(
                  'flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium',
                  'transition-all duration-200',
                  activeLines[key]
                    ? 'text-white'
                    : 'text-white/30',
                )}
                style={{
                  background: activeLines[key] ? color + '15' : 'transparent',
                  border: `1px solid ${activeLines[key] ? color + '40' : 'rgba(255,255,255,0.05)'}`,
                }}
                aria-pressed={activeLines[key]}
              >
                <div
                  className="w-2 h-2 rounded-full transition-opacity"
                  style={{ background: color, opacity: activeLines[key] ? 1 : 0.3 }}
                />
                {label}
                <span
                  className="font-black tabular-nums"
                  style={{ color: activeLines[key] ? color : 'inherit' }}
                >
                  +{ret}%
                </span>
              </button>
            ))}
          </div>
        </div>

        <div className="h-72">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData} margin={{ top: 5, right: 5, bottom: 5, left: 10 }}>
              <defs>
                <linearGradient id="gradOracle" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#00D4FF" stopOpacity={0.3} />
                  <stop offset="100%" stopColor="#00D4FF" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="gradSP" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#FFB800" stopOpacity={0.15} />
                  <stop offset="100%" stopColor="#FFB800" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="gradBal" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#8B5CF6" stopOpacity={0.15} />
                  <stop offset="100%" stopColor="#8B5CF6" stopOpacity={0} />
                </linearGradient>
              </defs>

              <CartesianGrid
                strokeDasharray="3 3"
                stroke="rgba(255,255,255,0.04)"
                vertical={false}
              />

              <XAxis
                dataKey="date"
                tick={{ fill: 'rgba(255,255,255,0.3)', fontSize: 10 }}
                tickLine={false}
                axisLine={false}
                interval={Math.floor(chartData.length / 6)}
              />

              <YAxis
                tick={{ fill: 'rgba(255,255,255,0.3)', fontSize: 10 }}
                tickLine={false}
                axisLine={false}
                tickFormatter={(v) => `$${(v / 1000).toFixed(1)}k`}
              />

              <Tooltip content={<CustomTooltip />} />

              <ReferenceLine
                y={10000}
                stroke="rgba(255,255,255,0.1)"
                strokeDasharray="4 4"
              />

              {activeLines.balanced && (
                <Area
                  type="monotone"
                  dataKey="balanced"
                  name="60/40"
                  stroke="#8B5CF6"
                  strokeWidth={1.5}
                  fill="url(#gradBal)"
                  dot={false}
                  animationDuration={1500}
                />
              )}

              {activeLines.sp500 && (
                <Area
                  type="monotone"
                  dataKey="sp500"
                  name="S&P 500"
                  stroke="#FFB800"
                  strokeWidth={1.5}
                  fill="url(#gradSP)"
                  dot={false}
                  animationDuration={1800}
                />
              )}

              {activeLines.oracle && (
                <Area
                  type="monotone"
                  dataKey="oracle"
                  name="AETHERTRADE-SWARM"
                  stroke="#00D4FF"
                  strokeWidth={2.5}
                  fill="url(#gradOracle)"
                  dot={false}
                  animationDuration={2000}
                  style={{ filter: 'drop-shadow(0 0 4px rgba(0,212,255,0.5))' }}
                />
              )}
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Bottom stat row */}
        <div
          className="mt-4 pt-4 grid grid-cols-3 gap-4"
          style={{ borderTop: '1px solid rgba(255,255,255,0.05)' }}
        >
          {[
            { label: 'vs S&P 500 Alpha', value: `+${(parseFloat(oracleReturn) - parseFloat(spReturn)).toFixed(1)}%`, color: '#00D4FF' },
            { label: 'Avg Monthly Return', value: '+1.42%', color: '#00FF94' },
            { label: 'Profitable Months', value: '81.6%', color: '#FFB800' },
          ].map((stat) => (
            <div key={stat.label} className="text-center">
              <div className="text-lg font-black" style={{ color: stat.color }}>{stat.value}</div>
              <div className="text-xs text-white/30">{stat.label}</div>
            </div>
          ))}
        </div>
      </motion.div>
    </section>
  )
}
