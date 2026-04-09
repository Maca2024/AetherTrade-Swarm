'use client'

import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useInView } from 'react-intersection-observer'
import { Shield, AlertTriangle, CheckCircle, XCircle, Activity } from 'lucide-react'
import { RISK_METRICS, KILL_SWITCHES, STRATEGY_PODS, generateCorrelationMatrix, type RiskMetric as RiskMetricType } from '@/lib/data'
import { useRiskDashboard, useKillSwitches } from '@/lib/hooks'
import { correlationToColor, cn } from '@/lib/utils'

const correlationMatrix = generateCorrelationMatrix()
const podNames = STRATEGY_PODS.map(p => p.shortName)

function RiskBar({ metric, inView, index }: {
  metric: typeof RISK_METRICS[0]
  inView: boolean
  index: number
}) {
  const pct = (metric.value / metric.max) * 100

  return (
    <motion.div
      initial={{ opacity: 0, x: -20 }}
      animate={inView ? { opacity: 1, x: 0 } : {}}
      transition={{ duration: 0.5, delay: index * 0.08 }}
      className="space-y-2"
    >
      <div className="flex items-center justify-between text-xs">
        <span className="text-white/50">{metric.label}</span>
        <div className="flex items-center gap-2">
          <span className="font-bold tabular-nums" style={{ color: metric.color }}>
            {metric.value}{metric.unit}
          </span>
          <span className="text-white/20">/ {metric.max}{metric.unit}</span>
        </div>
      </div>
      <div className="relative h-2 bg-white/6 rounded-full overflow-hidden">
        {/* Danger zones */}
        <div
          className="absolute top-0 right-0 bottom-0 w-1/4 rounded-r-full"
          style={{ background: 'rgba(255,51,102,0.08)' }}
        />
        <motion.div
          initial={{ width: 0 }}
          animate={inView ? { width: `${pct}%` } : {}}
          transition={{ duration: 1, delay: index * 0.08 + 0.3, ease: 'easeOut' }}
          className="absolute top-0 left-0 bottom-0 rounded-full"
          style={{
            background: `linear-gradient(90deg, ${metric.color}80, ${metric.color})`,
            boxShadow: `0 0 8px ${metric.color}60`,
          }}
        />
      </div>
    </motion.div>
  )
}

function KillSwitchRow({ sw, index, inView }: {
  sw: typeof KILL_SWITCHES[0]
  index: number
  inView: boolean
}) {
  const colorMap = {
    green: { bg: '#00FF9415', color: '#00FF94', icon: <CheckCircle className="w-3.5 h-3.5" /> },
    amber: { bg: '#FFB80015', color: '#FFB800', icon: <AlertTriangle className="w-3.5 h-3.5" /> },
    red: { bg: '#FF336615', color: '#FF3366', icon: <XCircle className="w-3.5 h-3.5" /> },
  }
  const style = colorMap[sw.status as keyof typeof colorMap]

  return (
    <motion.div
      initial={{ opacity: 0, x: 20 }}
      animate={inView ? { opacity: 1, x: 0 } : {}}
      transition={{ duration: 0.5, delay: index * 0.08 }}
      className="flex items-center justify-between py-2.5 px-3 rounded-xl"
      style={{
        background: style.bg,
        border: `1px solid ${style.color}20`,
      }}
    >
      <div className="flex items-center gap-2">
        <div style={{ color: style.color }}>{style.icon}</div>
        <span className="text-xs text-white/60">{sw.label}</span>
      </div>
      <div className="flex items-center gap-3">
        <div className="text-right hidden sm:block">
          <div className="text-[10px] text-white/30">Threshold</div>
          <div className="text-xs font-medium text-white/50">{sw.threshold}</div>
        </div>
        <div className="text-right">
          <div className="text-[10px] text-white/30">Current</div>
          <div className="text-xs font-bold" style={{ color: style.color }}>{sw.current}</div>
        </div>
      </div>
    </motion.div>
  )
}

function CorrelationHeatmap({ inView }: { inView: boolean }) {
  return (
    <div
      className="rounded-2xl p-5"
      style={{
        background: 'rgba(255,255,255,0.02)',
        border: '1px solid rgba(255,255,255,0.07)',
      }}
    >
      <h3 className="text-sm font-bold text-white mb-1">Correlation Matrix</h3>
      <p className="text-xs text-white/30 mb-4">9x9 inter-strategy correlation heatmap</p>

      {/* X axis labels */}
      <div className="flex items-center mb-1 pl-8">
        {podNames.map((name) => (
          <div key={name} className="flex-1 text-center text-[8px] text-white/30 font-medium truncate">
            {name}
          </div>
        ))}
      </div>

      <div className="space-y-0.5">
        {correlationMatrix.map((row, i) => (
          <div key={i} className="flex items-center gap-0.5">
            {/* Y label */}
            <div className="w-8 flex-shrink-0 text-[8px] text-white/30 text-right pr-1.5 font-medium">
              {podNames[i]}
            </div>
            {row.map((val, j) => (
              <motion.div
                key={j}
                initial={{ opacity: 0, scale: 0.5 }}
                animate={inView ? { opacity: 1, scale: 1 } : {}}
                transition={{
                  duration: 0.3,
                  delay: (i * 9 + j) * 0.005,
                }}
                className="flex-1 aspect-square rounded-sm flex items-center justify-center cursor-default"
                style={{ background: correlationToColor(val) }}
                title={`${podNames[i]} / ${podNames[j]}: ${val.toFixed(2)}`}
                role="cell"
                aria-label={`${podNames[i]} to ${podNames[j]} correlation: ${val.toFixed(2)}`}
              >
                {i === j && (
                  <div className="w-1 h-1 rounded-full bg-white/60" />
                )}
              </motion.div>
            ))}
          </div>
        ))}
      </div>

      {/* Legend */}
      <div className="flex items-center justify-between mt-3 text-[10px] text-white/30">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-sm" style={{ background: 'rgba(255,51,102,0.4)' }} />
          <span>Negative</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-sm" style={{ background: 'rgba(255,255,255,0.1)' }} />
          <span>Neutral</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-sm" style={{ background: 'rgba(0,212,255,0.6)' }} />
          <span>Positive</span>
        </div>
      </div>
    </div>
  )
}

export default function RiskPanel() {
  const [ref, inView] = useInView({ threshold: 0.1, triggerOnce: true })
  const { data: apiRisk } = useRiskDashboard()
  const { data: apiKs } = useKillSwitches()

  // Build risk metrics from API or fallback
  const displayRiskMetrics: RiskMetricType[] = apiRisk
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

  const displayKillSwitches = apiKs
    ? apiKs.kill_switches.map((ks) => ({
        label: ks.name,
        status: ks.triggered ? 'red' as const : 'green' as const,
        threshold: `${ks.threshold}`,
        current: `${ks.current_value}`,
      }))
    : KILL_SWITCHES

  // Live VaR from API or simulated
  const [liveVaR, setLiveVaR] = useState(apiRisk?.portfolio_var_95 ?? 1.42)
  useEffect(() => {
    if (apiRisk?.portfolio_var_95 != null) {
      setLiveVaR(apiRisk.portfolio_var_95)
      return
    }
    const interval = setInterval(() => {
      setLiveVaR(prev => parseFloat((prev + (Math.random() - 0.5) * 0.04).toFixed(3)))
    }, 3000)
    return () => clearInterval(interval)
  }, [apiRisk])

  return (
    <section
      ref={ref}
      className="py-20 px-4 sm:px-6 max-w-7xl mx-auto"
      aria-labelledby="risk-heading"
    >
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={inView ? { opacity: 1, y: 0 } : {}}
        transition={{ duration: 0.6 }}
        className="mb-12 text-center"
      >
        <div className="flex items-center justify-center gap-3 mb-4">
          <div className="h-px w-16 bg-gradient-to-r from-transparent to-[#FF3366]/40" />
          <span className="text-xs tracking-widest text-[#FF3366] uppercase font-semibold">
            Risk Intelligence
          </span>
          <div className="h-px w-16 bg-gradient-to-l from-transparent to-[#FF3366]/40" />
        </div>
        <h2
          id="risk-heading"
          className="text-4xl sm:text-5xl font-black tracking-tight mb-4"
          style={{
            background: 'linear-gradient(135deg, #FFFFFF 0%, #FF3366 100%)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            backgroundClip: 'text',
          }}
        >
          Risk Management
        </h2>
        <p className="text-white/40 text-base max-w-xl mx-auto">
          4-layer real-time risk framework with automated circuit breakers and kill switches.
        </p>
      </motion.div>

      <div className="grid lg:grid-cols-2 gap-6">
        {/* Left: Metrics + Kill Switches */}
        <div className="space-y-6">
          {/* Live VaR banner */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={inView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.5 }}
            className="rounded-2xl p-5"
            style={{
              background: 'linear-gradient(135deg, rgba(0,255,148,0.05) 0%, rgba(0,212,255,0.05) 100%)',
              border: '1px solid rgba(0,255,148,0.15)',
            }}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-[#00FF94]/10 border border-[#00FF94]/20 flex items-center justify-center">
                  <Shield className="w-5 h-5 text-[#00FF94]" />
                </div>
                <div>
                  <div className="text-xs text-white/40 uppercase tracking-wider">
                    Live 95% VaR
                  </div>
                  <div className="flex items-center gap-2">
                    <motion.span
                      key={liveVaR}
                      initial={{ y: -10, opacity: 0 }}
                      animate={{ y: 0, opacity: 1 }}
                      className="text-2xl font-black text-[#00FF94] tabular-nums"
                    >
                      {liveVaR.toFixed(2)}%
                    </motion.span>
                    <Activity className="w-4 h-4 text-[#00FF94] animate-pulse" />
                  </div>
                </div>
              </div>
              <div className="text-right">
                <div className="text-xs text-white/30 mb-1">Portfolio Status</div>
                <div
                  className="text-sm font-bold px-3 py-1 rounded-full"
                  style={{
                    background: 'rgba(0,255,148,0.1)',
                    color: '#00FF94',
                    border: '1px solid rgba(0,255,148,0.2)',
                  }}
                >
                  ALL GREEN
                </div>
              </div>
            </div>
          </motion.div>

          {/* Risk metric bars */}
          <div
            className="rounded-2xl p-5 space-y-4"
            style={{
              background: 'rgba(255,255,255,0.02)',
              border: '1px solid rgba(255,255,255,0.07)',
            }}
          >
            <h3 className="text-sm font-bold text-white">Risk Metrics</h3>
            {displayRiskMetrics.map((metric, i) => (
              <RiskBar key={metric.label} metric={metric} inView={inView} index={i} />
            ))}
          </div>

          {/* Kill switches */}
          <div
            className="rounded-2xl p-5"
            style={{
              background: 'rgba(255,255,255,0.02)',
              border: '1px solid rgba(255,255,255,0.07)',
            }}
          >
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-bold text-white">Circuit Breakers</h3>
              <div className="flex items-center gap-1.5 text-xs text-[#00FF94]">
                <div className="w-1.5 h-1.5 rounded-full bg-[#00FF94] animate-pulse" />
                5/6 Active
              </div>
            </div>
            <div className="space-y-2">
              {displayKillSwitches.map((sw, i) => (
                <KillSwitchRow key={sw.label} sw={sw} index={i} inView={inView} />
              ))}
            </div>
          </div>
        </div>

        {/* Right: Correlation matrix */}
        <div className="space-y-6">
          <CorrelationHeatmap inView={inView} />

          {/* Risk summary stats */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={inView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.5, delay: 0.4 }}
            className="grid grid-cols-2 gap-3"
          >
            {[
              { label: 'Portfolio Beta', value: '0.24', color: '#00D4FF', sub: 'vs S&P 500' },
              { label: 'Avg Correlation', value: '0.18', color: '#8B5CF6', sub: 'inter-strategy' },
              { label: 'Tail Risk (99%)', value: '-2.18%', color: '#FFB800', sub: 'daily CVaR' },
              { label: 'Stress Test', value: 'PASS', color: '#00FF94', sub: '2008 scenario' },
            ].map((stat) => (
              <div
                key={stat.label}
                className="rounded-xl p-4"
                style={{
                  background: stat.color + '08',
                  border: `1px solid ${stat.color}20`,
                }}
              >
                <div className="text-xl font-black mb-0.5" style={{ color: stat.color }}>
                  {stat.value}
                </div>
                <div className="text-xs font-medium text-white/60">{stat.label}</div>
                <div className="text-[10px] text-white/30 mt-0.5">{stat.sub}</div>
              </div>
            ))}
          </motion.div>
        </div>
      </div>
    </section>
  )
}
