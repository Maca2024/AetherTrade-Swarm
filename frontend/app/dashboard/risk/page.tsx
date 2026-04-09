'use client'

import { useState } from 'react'
import { Shield, AlertTriangle, Activity, TrendingDown, Zap, BarChart3, Lock, Eye } from 'lucide-react'
import { motion } from 'framer-motion'

interface RiskMetric {
  name: string
  value: number
  threshold_warning: number
  threshold_critical: number
  status: 'ok' | 'warning' | 'critical'
  unit: string
  icon: React.ReactNode
}

interface KillSwitch {
  name: string
  triggered: boolean
  threshold: number
  current_value: number
  auto_action: string
}

const MOCK_METRICS: RiskMetric[] = [
  { name: 'Annualized Volatility', value: 0.0725, threshold_warning: 0.15, threshold_critical: 0.25, status: 'ok', unit: '%', icon: <Activity className="w-4 h-4" /> },
  { name: 'Maximum Drawdown', value: 0.1146, threshold_warning: 0.10, threshold_critical: 0.20, status: 'warning', unit: '%', icon: <TrendingDown className="w-4 h-4" /> },
  { name: 'Current Drawdown', value: 0.0437, threshold_warning: 0.05, threshold_critical: 0.12, status: 'ok', unit: '%', icon: <TrendingDown className="w-4 h-4" /> },
  { name: 'Gross Leverage', value: 1.35, threshold_warning: 1.75, threshold_critical: 2.50, status: 'ok', unit: 'x', icon: <BarChart3 className="w-4 h-4" /> },
  { name: 'Concentration Risk', value: 0.235, threshold_warning: 0.25, threshold_critical: 0.40, status: 'ok', unit: '%', icon: <Eye className="w-4 h-4" /> },
  { name: 'Liquidity Score', value: 0.2194, threshold_warning: 0.20, threshold_critical: 0.35, status: 'warning', unit: '%', icon: <Zap className="w-4 h-4" /> },
  { name: 'Tail Risk (99% VaR)', value: 0.0105, threshold_warning: 0.03, threshold_critical: 0.06, status: 'ok', unit: '%', icon: <AlertTriangle className="w-4 h-4" /> },
  { name: 'Strategy Correlation', value: 0.3661, threshold_warning: 0.50, threshold_critical: 0.70, status: 'ok', unit: '', icon: <Shield className="w-4 h-4" /> },
]

const MOCK_KILL_SWITCHES: KillSwitch[] = [
  { name: 'Max Drawdown Kill', triggered: false, threshold: 0.15, current_value: 0.0437, auto_action: 'flatten_all_positions' },
  { name: 'Daily Loss Limit', triggered: false, threshold: 0.025, current_value: 0.0035, auto_action: 'halt_new_positions' },
  { name: 'Leverage Limit', triggered: false, threshold: 2.5, current_value: 1.35, auto_action: 'reduce_leverage' },
  { name: 'Correlation Spike', triggered: false, threshold: 0.8, current_value: 0.3846, auto_action: 'reduce_size_20pct' },
]

const STATUS_COLORS = {
  ok: { bg: 'rgba(0,255,148,0.1)', border: 'rgba(0,255,148,0.3)', text: '#00FF94', label: 'NORMAL' },
  warning: { bg: 'rgba(255,184,0,0.1)', border: 'rgba(255,184,0,0.3)', text: '#FFB800', label: 'WARNING' },
  critical: { bg: 'rgba(255,51,102,0.1)', border: 'rgba(255,51,102,0.3)', text: '#FF3366', label: 'CRITICAL' },
}

function formatValue(value: number, unit: string): string {
  if (unit === '%') return `${(value * 100).toFixed(2)}%`
  if (unit === 'x') return `${value.toFixed(2)}x`
  return value.toFixed(4)
}

export default function RiskPage() {
  const overallStatus = MOCK_METRICS.some(m => m.status === 'critical') ? 'critical' :
    MOCK_METRICS.some(m => m.status === 'warning') ? 'warning' : 'ok'

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Risk Management</h1>
          <p className="text-sm text-white/40 mt-1">8 metrics, 4 kill switches, real-time monitoring</p>
        </div>
        <div
          className="px-4 py-2 rounded-xl text-sm font-bold"
          style={{
            background: STATUS_COLORS[overallStatus].bg,
            border: `1px solid ${STATUS_COLORS[overallStatus].border}`,
            color: STATUS_COLORS[overallStatus].text,
          }}
        >
          <Shield className="w-4 h-4 inline mr-2" />
          {STATUS_COLORS[overallStatus].label}
        </div>
      </div>

      {/* Risk Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
        {MOCK_METRICS.map((metric, i) => {
          const colors = STATUS_COLORS[metric.status]
          const pct = Math.min(metric.value / metric.threshold_critical, 1)
          return (
            <motion.div
              key={metric.name}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05 }}
              className="p-4 rounded-2xl"
              style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.08)' }}
            >
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2 text-white/50">
                  {metric.icon}
                  <span className="text-xs">{metric.name}</span>
                </div>
                <span className="text-[10px] font-bold px-2 py-0.5 rounded-full" style={{ background: colors.bg, color: colors.text }}>
                  {colors.label}
                </span>
              </div>
              <div className="text-xl font-bold text-white mb-2">
                {formatValue(metric.value, metric.unit)}
              </div>
              {/* Progress bar */}
              <div className="h-1.5 rounded-full bg-white/5 overflow-hidden">
                <div className="h-full rounded-full transition-all" style={{ width: `${pct * 100}%`, background: colors.text }} />
              </div>
              <div className="flex justify-between mt-1">
                <span className="text-[10px] text-white/20">0</span>
                <span className="text-[10px] text-white/20">{formatValue(metric.threshold_critical, metric.unit)}</span>
              </div>
            </motion.div>
          )
        })}
      </div>

      {/* Kill Switches */}
      <div>
        <h2 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
          <Lock className="w-5 h-5 text-[#FF3366]" />
          Kill Switches
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {MOCK_KILL_SWITCHES.map((ks, i) => (
            <motion.div
              key={ks.name}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.3 + i * 0.05 }}
              className="p-4 rounded-2xl flex items-center justify-between"
              style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.08)' }}
            >
              <div>
                <div className="text-sm font-medium text-white">{ks.name}</div>
                <div className="text-xs text-white/30 mt-1">
                  Threshold: {ks.threshold} | Current: {ks.current_value.toFixed(4)}
                </div>
                <div className="text-[10px] text-white/20 mt-0.5">
                  Action: {ks.auto_action.replace(/_/g, ' ')}
                </div>
              </div>
              <div
                className="w-3 h-3 rounded-full"
                style={{
                  background: ks.triggered ? '#FF3366' : '#00FF94',
                  boxShadow: `0 0 8px ${ks.triggered ? '#FF3366' : '#00FF94'}`,
                }}
              />
            </motion.div>
          ))}
        </div>
      </div>

      {/* VaR Summary */}
      <div className="p-6 rounded-2xl" style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.08)' }}>
        <h3 className="text-sm font-bold text-white/50 uppercase tracking-wider mb-4">Value at Risk Summary</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
          {[
            { label: '95% VaR (1-day)', value: '0.52%', color: '#00FF94' },
            { label: '95% CVaR', value: '0.95%', color: '#00D4FF' },
            { label: '99% VaR (1-day)', value: '1.05%', color: '#FFB800' },
            { label: 'Stress Test Loss', value: '19.1%', color: '#FF3366' },
          ].map((item) => (
            <div key={item.label}>
              <div className="text-xs text-white/30 mb-1">{item.label}</div>
              <div className="text-lg font-bold" style={{ color: item.color }}>{item.value}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
