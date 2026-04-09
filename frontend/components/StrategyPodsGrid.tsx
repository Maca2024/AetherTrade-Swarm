'use client'

import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useInView } from 'react-intersection-observer'
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  Tooltip,
} from 'recharts'
import { TrendingUp, TrendingDown, ChevronDown, Activity } from 'lucide-react'
import { STRATEGY_PODS, type StrategyPod } from '@/lib/data'
import { useStrategies } from '@/lib/hooks'
import { cn } from '@/lib/utils'

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
  momentum: 'MOM', mean_reversion: 'MR', macro: 'GMC', stat_arb: 'SA',
  options_vol: 'VOL', behavioral: 'BEH', ai_ml: 'AI', multi_factor: 'MF', market_making: 'MM',
}

function apiToStrategyPod(pod: {
  pod_name: string; display_name: string; regime_allocation: number;
  ytd_return: number; sharpe_ratio: number; win_rate: number; description: string;
}): StrategyPod {
  const colors = POD_COLORS[pod.pod_name] ?? { color: '#888', glowColor: 'rgba(136,136,136,0.3)' }
  const sparkline: number[] = []
  let val = 100
  const trend = pod.ytd_return / 15 / 100
  for (let i = 0; i < 15; i++) {
    val += val * (trend + (Math.sin(i * 1.3) * 0.01))
    sparkline.push(parseFloat(val.toFixed(2)))
  }
  return {
    id: pod.pod_name,
    name: pod.display_name,
    shortName: POD_SHORT_NAMES[pod.pod_name] ?? pod.pod_name.slice(0, 3).toUpperCase(),
    allocation: pod.regime_allocation * 100,
    signal: 0,
    signalStrength: Math.round(pod.win_rate * 100),
    pnl: pod.ytd_return,
    sharpe: pod.sharpe_ratio,
    sparkline,
    color: colors.color,
    glowColor: colors.glowColor,
    description: pod.description,
    regime: [],
  }
}

function SignalBar({ value, color }: { value: number; color: string }) {
  // value: -1 to 1
  const pct = ((value + 1) / 2) * 100
  const isPositive = value >= 0

  return (
    <div className="flex items-center gap-2">
      <div className="relative h-1.5 flex-1 bg-white/8 rounded-full overflow-hidden">
        <div className="absolute inset-0 flex">
          <div className="flex-1" />
          <div className="w-px bg-white/20" />
          <div className="flex-1" />
        </div>
        <motion.div
          initial={{ width: '50%' }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 1, ease: 'easeOut' }}
          className="absolute top-0 bottom-0 rounded-full"
          style={{
            left: value < 0 ? `${pct}%` : '50%',
            right: value >= 0 ? `${100 - pct}%` : '50%',
            background: color,
            boxShadow: `0 0 6px ${color}`,
          }}
        />
      </div>
      <span className="text-xs tabular-nums" style={{ color }}>
        {value >= 0 ? '+' : ''}{(value * 100).toFixed(0)}
      </span>
    </div>
  )
}

function AllocationRing({ value, color }: { value: number; color: string }) {
  const radius = 18
  const circumference = 2 * Math.PI * radius
  const offset = circumference - (value / 100) * circumference

  return (
    <div className="relative flex-shrink-0">
      <svg width="44" height="44" className="rotate-[-90deg]">
        <circle
          cx="22" cy="22" r={radius}
          fill="none"
          stroke="rgba(255,255,255,0.07)"
          strokeWidth="3"
        />
        <motion.circle
          cx="22" cy="22" r={radius}
          fill="none"
          stroke={color}
          strokeWidth="3"
          strokeLinecap="round"
          strokeDasharray={circumference}
          initial={{ strokeDashoffset: circumference }}
          animate={{ strokeDashoffset: offset }}
          transition={{ duration: 1.2, ease: 'easeOut' }}
          style={{ filter: `drop-shadow(0 0 4px ${color})` }}
        />
      </svg>
      <div className="absolute inset-0 flex items-center justify-center rotate-0">
        <span className="text-[10px] font-bold" style={{ color }}>{value.toFixed(0)}%</span>
      </div>
    </div>
  )
}

function PodCard({ pod, index }: { pod: StrategyPod; index: number }) {
  const [expanded, setExpanded] = useState(false)
  const [ref, inView] = useInView({ threshold: 0.2, triggerOnce: true })

  const sparkData = pod.sparkline.map((v, i) => ({ i, v }))
  const isUp = pod.pnl > 0

  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: 30 }}
      animate={inView ? { opacity: 1, y: 0 } : {}}
      transition={{ duration: 0.5, delay: index * 0.07, ease: [0.16, 1, 0.3, 1] }}
      onClick={() => setExpanded(!expanded)}
      className={cn(
        'relative rounded-2xl cursor-pointer select-none',
        'transition-all duration-300',
        'group overflow-hidden',
      )}
      style={{
        background: expanded
          ? `linear-gradient(135deg, rgba(12,12,22,0.95) 0%, ${pod.glowColor.replace('0.3', '0.08')} 100%)`
          : 'rgba(255,255,255,0.03)',
        border: `1px solid ${expanded ? pod.color + '40' : 'rgba(255,255,255,0.07)'}`,
        boxShadow: expanded
          ? `0 0 30px ${pod.glowColor}, 0 8px 40px rgba(0,0,0,0.5)`
          : '0 4px 24px rgba(0,0,0,0.3)',
      }}
      whileHover={{
        scale: 1.02,
        boxShadow: `0 0 20px ${pod.glowColor}, 0 8px 32px rgba(0,0,0,0.5)`,
        borderColor: pod.color + '60',
      }}
    >
      {/* Top glow bar */}
      <div
        className="absolute top-0 left-0 right-0 h-px"
        style={{
          background: `linear-gradient(90deg, transparent, ${pod.color}80, transparent)`,
          opacity: expanded ? 1 : 0,
          transition: 'opacity 0.3s',
        }}
      />

      {/* Shimmer on hover */}
      <div
        className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none shimmer rounded-2xl"
      />

      <div className="p-5">
        {/* Header */}
        <div className="flex items-start justify-between mb-3">
          <div className="flex items-center gap-3">
            <AllocationRing value={pod.allocation} color={pod.color} />
            <div>
              <div className="flex items-center gap-2">
                <span
                  className="text-[10px] font-black tracking-widest px-1.5 py-0.5 rounded"
                  style={{
                    color: pod.color,
                    background: pod.glowColor.replace('0.3', '0.15'),
                    border: `1px solid ${pod.color}30`,
                  }}
                >
                  {pod.shortName}
                </span>
              </div>
              <h3 className="text-sm font-semibold text-white mt-1 leading-tight">
                {pod.name}
              </h3>
            </div>
          </div>

          <div className="flex flex-col items-end gap-1">
            <div className={cn('flex items-center gap-1 text-xs font-bold')}>
              {isUp
                ? <TrendingUp className="w-3 h-3 text-[#00FF94]" />
                : <TrendingDown className="w-3 h-3 text-[#FF3366]" />
              }
              <span style={{ color: isUp ? '#00FF94' : '#FF3366' }}>
                {isUp ? '+' : ''}{pod.pnl.toFixed(1)}%
              </span>
            </div>
            <span className="text-[10px] text-white/30">YTD PnL</span>
          </div>
        </div>

        {/* Sparkline */}
        <div className="h-12 mb-3">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={sparkData} margin={{ top: 0, right: 0, bottom: 0, left: 0 }}>
              <defs>
                <linearGradient id={`spark-${pod.id}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={pod.color} stopOpacity={0.4} />
                  <stop offset="100%" stopColor={pod.color} stopOpacity={0} />
                </linearGradient>
              </defs>
              <Area
                type="monotone"
                dataKey="v"
                stroke={pod.color}
                strokeWidth={1.5}
                fill={`url(#spark-${pod.id})`}
                dot={false}
                isAnimationActive={true}
                animationDuration={1200}
                animationEasing="ease-out"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Signal */}
        <div className="mb-2">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-[10px] text-white/30 uppercase tracking-wider">Signal</span>
            <div className="flex items-center gap-1">
              <Activity className="w-2.5 h-2.5" style={{ color: pod.color }} />
              <span className="text-[10px]" style={{ color: pod.color }}>
                {pod.signalStrength}%
              </span>
            </div>
          </div>
          <SignalBar value={pod.signal} color={pod.color} />
        </div>

        {/* Sharpe */}
        <div className="flex items-center justify-between">
          <span className="text-[10px] text-white/30 uppercase tracking-wider">Sharpe</span>
          <span className="text-xs font-bold" style={{ color: pod.color }}>
            {pod.sharpe.toFixed(2)}
          </span>
        </div>
      </div>

      {/* Expanded details */}
      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3, ease: 'easeInOut' }}
            className="overflow-hidden"
          >
            <div
              className="mx-4 mb-4 p-3 rounded-xl"
              style={{
                background: 'rgba(0,0,0,0.3)',
                border: `1px solid ${pod.color}20`,
              }}
            >
              <p className="text-xs text-white/50 leading-relaxed mb-3">{pod.description}</p>
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-[10px] text-white/30 uppercase tracking-wider">Active regimes:</span>
                {pod.regime.map(r => (
                  <span
                    key={r}
                    className="text-[10px] px-2 py-0.5 rounded-full font-medium capitalize"
                    style={{
                      background: `${pod.color}15`,
                      color: pod.color,
                      border: `1px solid ${pod.color}30`,
                    }}
                  >
                    {r}
                  </span>
                ))}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Expand indicator */}
      <div className="absolute bottom-3 right-4">
        <motion.div
          animate={{ rotate: expanded ? 180 : 0 }}
          transition={{ duration: 0.3 }}
        >
          <ChevronDown className="w-3 h-3 text-white/20" />
        </motion.div>
      </div>
    </motion.div>
  )
}

export default function StrategyPodsGrid() {
  const [ref, inView] = useInView({ threshold: 0.1, triggerOnce: true })
  const { data: apiData } = useStrategies()

  // Use live data if available, fallback to static
  const pods = apiData
    ? apiData.pods.map(apiToStrategyPod)
    : STRATEGY_PODS

  return (
    <section className="py-20 px-4 sm:px-6 max-w-7xl mx-auto" aria-labelledby="pods-heading">
      <motion.div
        ref={ref}
        initial={{ opacity: 0, y: 20 }}
        animate={inView ? { opacity: 1, y: 0 } : {}}
        transition={{ duration: 0.6 }}
        className="mb-12 text-center"
      >
        <div className="flex items-center justify-center gap-3 mb-4">
          <div className="h-px w-16 bg-gradient-to-r from-transparent to-[#00D4FF]/40" />
          <span className="text-xs tracking-widest text-[#00D4FF] uppercase font-semibold">
            Strategy Intelligence
          </span>
          <div className="h-px w-16 bg-gradient-to-l from-transparent to-[#00D4FF]/40" />
        </div>

        <h2
          id="pods-heading"
          className="text-4xl sm:text-5xl font-black tracking-tight mb-4"
          style={{
            background: 'linear-gradient(135deg, #FFFFFF 0%, #00D4FF 100%)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            backgroundClip: 'text',
          }}
        >
          9 Strategy Pods
        </h2>
        <p className="text-white/40 text-base max-w-xl mx-auto">
          Independent alpha engines, unified by AI orchestration. Each pod operates autonomously
          with dedicated risk budgets and regime-adaptive weights.
        </p>
      </motion.div>

      {/* Total allocation indicator */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={inView ? { opacity: 1 } : {}}
        transition={{ duration: 0.6, delay: 0.3 }}
        className="flex items-center justify-center gap-6 mb-10 flex-wrap"
      >
        {pods.map((pod) => (
          <div key={pod.id} className="flex items-center gap-1.5">
            <div
              className="w-2 h-2 rounded-full"
              style={{ background: pod.color, boxShadow: `0 0 6px ${pod.color}` }}
            />
            <span className="text-xs text-white/30">{pod.shortName}</span>
            <span className="text-xs font-bold" style={{ color: pod.color }}>
              {pod.allocation.toFixed(1)}%
            </span>
          </div>
        ))}
      </motion.div>

      {/* Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {pods.map((pod, i) => (
          <PodCard key={pod.id} pod={pod} index={i} />
        ))}
      </div>

      <motion.p
        initial={{ opacity: 0 }}
        animate={inView ? { opacity: 1 } : {}}
        transition={{ delay: 0.8 }}
        className="text-center text-xs text-white/20 mt-6"
      >
        Click any pod to expand strategy details
      </motion.p>
    </section>
  )
}
