'use client'

import { useState } from 'react'
import { motion } from 'framer-motion'
import {
  Settings,
  Key,
  Bell,
  Monitor,
  Shield,
  ChevronRight,
  Copy,
  Check,
  Eye,
  EyeOff,
  Save,
  Wifi,
  WifiOff,
} from 'lucide-react'
import { useApiStatus } from '@/lib/hooks'
import { setApiKey, getApiKey } from '@/lib/hooks'
import { cn } from '@/lib/utils'

function SectionHeader({ icon, title, subtitle }: { icon: React.ReactNode; title: string; subtitle: string }) {
  return (
    <div className="flex items-center gap-3 mb-4">
      <div
        className="w-8 h-8 rounded-xl flex items-center justify-center"
        style={{ background: 'rgba(124,58,237,0.15)', border: '1px solid rgba(124,58,237,0.25)' }}
      >
        <div className="text-[#7C3AED]">{icon}</div>
      </div>
      <div>
        <div className="text-sm font-bold text-white">{title}</div>
        <div className="text-[11px] text-white/30">{subtitle}</div>
      </div>
    </div>
  )
}

function ApiKeySection() {
  const { isConnected, health } = useApiStatus()
  const [key, setKey] = useState(getApiKey() ?? '')
  const [showKey, setShowKey] = useState(false)
  const [saved, setSaved] = useState(false)
  const [copied, setCopied] = useState(false)

  const handleSave = () => {
    if (key.trim()) {
      setApiKey(key.trim())
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
    }
  }

  const handleCopy = async () => {
    if (!key) return
    await navigator.clipboard.writeText(key)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const maskedKey = key ? `${key.slice(0, 8)}${'•'.repeat(Math.max(0, key.length - 12))}${key.slice(-4)}` : ''

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
      <SectionHeader
        icon={<Key className="w-4 h-4" />}
        title="API Key"
        subtitle="Authenticate with the AetherTrade backend"
      />

      {/* Connection status */}
      <div
        className={cn(
          'flex items-center gap-2 px-3 py-2 rounded-xl text-xs mb-4',
          isConnected
            ? 'bg-[#00FF94]/08 border border-[#00FF94]/20 text-[#00FF94]'
            : 'bg-white/5 border border-white/10 text-white/30'
        )}
      >
        {isConnected ? (
          <>
            <Wifi className="w-3.5 h-3.5" />
            <span className="font-medium">Connected</span>
            {health && (
              <span className="ml-auto text-[#00FF94]/60">
                v{health.version} — {health.environment}
              </span>
            )}
          </>
        ) : (
          <>
            <WifiOff className="w-3.5 h-3.5" />
            <span>Not connected — running in demo mode</span>
          </>
        )}
      </div>

      <div className="space-y-3">
        <label className="block">
          <span className="text-[11px] text-white/40 uppercase tracking-widest mb-1.5 block">
            API Key
          </span>
          <div className="flex items-center gap-2">
            <div className="relative flex-1">
              <input
                type={showKey ? 'text' : 'password'}
                value={key}
                onChange={(e) => setKey(e.target.value)}
                placeholder="aetherswarm_..."
                className="w-full bg-white/5 border border-white/10 rounded-xl px-3 py-2.5 text-sm text-white placeholder-white/20 focus:outline-none focus:border-[#7C3AED]/50 focus:bg-white/8 transition-all pr-10 tabular-nums"
                aria-label="API Key"
                autoComplete="off"
                spellCheck={false}
              />
              <button
                onClick={() => setShowKey(!showKey)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-white/30 hover:text-white/60 transition-colors"
                aria-label={showKey ? 'Hide key' : 'Show key'}
              >
                {showKey ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
              </button>
            </div>
            <button
              onClick={handleCopy}
              disabled={!key}
              className="flex items-center gap-1.5 px-3 py-2.5 rounded-xl text-xs text-white/40 hover:text-white bg-white/5 hover:bg-white/10 transition-all border border-white/5 disabled:opacity-30 disabled:cursor-not-allowed"
              aria-label="Copy API key"
            >
              {copied ? <Check className="w-3.5 h-3.5 text-[#00FF94]" /> : <Copy className="w-3.5 h-3.5" />}
            </button>
          </div>
        </label>

        <label className="block">
          <span className="text-[11px] text-white/40 uppercase tracking-widest mb-1.5 block">
            Backend URL
          </span>
          <input
            type="url"
            defaultValue={process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8888'}
            readOnly
            className="w-full bg-white/3 border border-white/5 rounded-xl px-3 py-2.5 text-sm text-white/30 cursor-default"
            aria-label="Backend URL (read-only)"
          />
          <p className="text-[10px] text-white/20 mt-1">
            Set via NEXT_PUBLIC_API_URL environment variable
          </p>
        </label>

        <button
          onClick={handleSave}
          className={cn(
            'flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-medium transition-all',
            saved
              ? 'bg-[#00FF94]/20 text-[#00FF94] border border-[#00FF94]/30'
              : 'bg-[#7C3AED] text-white hover:bg-[#6D28D9] border border-[#7C3AED]'
          )}
          aria-label="Save API key"
        >
          {saved ? <Check className="w-4 h-4" /> : <Save className="w-4 h-4" />}
          {saved ? 'Saved' : 'Save Key'}
        </button>
      </div>
    </motion.div>
  )
}

function NotificationSettings() {
  const [alerts, setAlerts] = useState({
    regimeChange: true,
    killSwitchTrigger: true,
    dailySummary: false,
    drawdownWarning: true,
    newSignal: false,
  })

  const toggleAlert = (key: keyof typeof alerts) => {
    setAlerts((prev) => ({ ...prev, [key]: !prev[key] }))
  }

  const notificationItems = [
    { key: 'regimeChange' as const, label: 'Regime Change', desc: 'Alert when market regime transitions' },
    { key: 'killSwitchTrigger' as const, label: 'Kill Switch Trigger', desc: 'Critical alert when circuit breakers fire' },
    { key: 'drawdownWarning' as const, label: 'Drawdown Warning', desc: 'Alert at 75% of drawdown limit' },
    { key: 'dailySummary' as const, label: 'Daily Summary', desc: 'P&L and performance digest at close' },
    { key: 'newSignal' as const, label: 'New Signals', desc: 'Notify on each new pod signal generation' },
  ]

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
      <SectionHeader
        icon={<Bell className="w-4 h-4" />}
        title="Notifications"
        subtitle="Configure dashboard alert thresholds"
      />

      <div className="space-y-1">
        {notificationItems.map((item, i) => (
          <motion.div
            key={item.key}
            initial={{ opacity: 0, x: -8 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.15 + i * 0.05 }}
            className="flex items-center justify-between py-3 border-b border-white/5 last:border-0"
          >
            <div className="min-w-0">
              <div className="text-sm text-white/70 font-medium">{item.label}</div>
              <div className="text-[11px] text-white/30">{item.desc}</div>
            </div>
            <button
              role="switch"
              aria-checked={alerts[item.key]}
              onClick={() => toggleAlert(item.key)}
              className={cn(
                'relative flex-shrink-0 ml-4 w-10 h-5 rounded-full transition-all duration-200',
                alerts[item.key] ? 'bg-[#7C3AED]' : 'bg-white/10'
              )}
              aria-label={`Toggle ${item.label}`}
            >
              <div
                className={cn(
                  'absolute top-0.5 w-4 h-4 rounded-full bg-white transition-all duration-200 shadow-sm',
                  alerts[item.key] ? 'left-5' : 'left-0.5'
                )}
              />
            </button>
          </motion.div>
        ))}
      </div>
    </motion.div>
  )
}

function DisplaySettings() {
  const [refreshRate, setRefreshRate] = useState('10')
  const [chartTheme, setChartTheme] = useState('void')

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
      <SectionHeader
        icon={<Monitor className="w-4 h-4" />}
        title="Display"
        subtitle="Customize chart and refresh behavior"
      />

      <div className="space-y-4">
        <div>
          <label className="block text-[11px] text-white/40 uppercase tracking-widest mb-2">
            Data Refresh Rate
          </label>
          <div className="flex gap-2">
            {['5', '10', '30', '60'].map((rate) => (
              <button
                key={rate}
                onClick={() => setRefreshRate(rate)}
                className={cn(
                  'flex-1 py-2 rounded-xl text-xs font-medium transition-all border',
                  refreshRate === rate
                    ? 'bg-[#7C3AED] text-white border-[#7C3AED]'
                    : 'bg-white/5 text-white/40 border-white/5 hover:text-white/70 hover:border-white/10'
                )}
                aria-pressed={refreshRate === rate}
              >
                {rate}s
              </button>
            ))}
          </div>
        </div>

        <div>
          <label className="block text-[11px] text-white/40 uppercase tracking-widest mb-2">
            Chart Theme
          </label>
          <div className="flex gap-2">
            {[
              { value: 'void', label: 'Luminous Void', color: '#7C3AED' },
              { value: 'neon', label: 'Neon Grid', color: '#00D4FF' },
              { value: 'minimal', label: 'Minimal', color: '#888' },
            ].map((theme) => (
              <button
                key={theme.value}
                onClick={() => setChartTheme(theme.value)}
                className={cn(
                  'flex-1 py-2 px-2 rounded-xl text-[11px] font-medium transition-all border flex items-center justify-center gap-1.5',
                  chartTheme === theme.value
                    ? 'text-white border-opacity-50'
                    : 'bg-white/5 text-white/40 border-white/5 hover:text-white/70'
                )}
                style={
                  chartTheme === theme.value
                    ? { background: `${theme.color}20`, borderColor: `${theme.color}40`, color: theme.color }
                    : {}
                }
                aria-pressed={chartTheme === theme.value}
              >
                <div className="w-2 h-2 rounded-full" style={{ background: theme.color }} />
                {theme.label}
              </button>
            ))}
          </div>
        </div>

        <div className="flex items-center justify-between py-2">
          <div>
            <div className="text-sm text-white/70 font-medium">Compact Mode</div>
            <div className="text-[11px] text-white/30">Reduce padding on all cards</div>
          </div>
          <button
            role="switch"
            aria-checked={false}
            className="relative flex-shrink-0 w-10 h-5 rounded-full bg-white/10 transition-all duration-200"
            aria-label="Toggle compact mode"
          >
            <div className="absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white shadow-sm" />
          </button>
        </div>
      </div>
    </motion.div>
  )
}

function SecurityInfo() {
  const securityItems = [
    {
      label: 'API Key Storage',
      value: 'Session storage only',
      detail: 'Never persisted to disk or transmitted outside the app',
      ok: true,
    },
    {
      label: 'Data in Transit',
      value: 'HTTPS enforced',
      detail: 'All backend communication is TLS encrypted',
      ok: true,
    },
    {
      label: 'Paper Trading Mode',
      value: 'Active',
      detail: 'No real capital — all orders are simulated',
      ok: true,
    },
    {
      label: 'Kill Switch Override',
      value: 'Manual only',
      detail: 'Automated triggers cannot be disabled remotely',
      ok: true,
    },
  ]

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
      <SectionHeader
        icon={<Shield className="w-4 h-4" />}
        title="Security & Compliance"
        subtitle="Platform safety configuration"
      />

      <div className="space-y-2">
        {securityItems.map((item, i) => (
          <motion.div
            key={item.label}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.25 + i * 0.06 }}
            className="flex items-start justify-between p-3 rounded-xl"
            style={{
              background: 'rgba(0,255,148,0.04)',
              border: '1px solid rgba(0,255,148,0.12)',
            }}
          >
            <div className="min-w-0">
              <div className="text-xs font-medium text-white/70">{item.label}</div>
              <div className="text-[10px] text-white/30 mt-0.5">{item.detail}</div>
            </div>
            <div className="flex items-center gap-1.5 ml-4 flex-shrink-0">
              <Check className="w-3.5 h-3.5 text-[#00FF94]" />
              <span className="text-[11px] font-medium text-[#00FF94]">{item.value}</span>
            </div>
          </motion.div>
        ))}
      </div>

      <div
        className="mt-4 p-3 rounded-xl text-[11px] text-white/30 leading-relaxed"
        style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.05)' }}
      >
        AetherTrade-Swarm is a research platform. Past simulated performance does not guarantee future results. All trading decisions carry inherent risk. AetherLink B.V. is not a licensed investment advisor.
      </div>
    </motion.div>
  )
}

function AboutSection() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: 0.25 }}
      className="rounded-2xl p-5"
      style={{
        background: 'rgba(255,255,255,0.02)',
        border: '1px solid rgba(255,255,255,0.07)',
      }}
    >
      <div className="flex items-center justify-between">
        <div>
          <div className="text-sm font-bold text-white mb-0.5">AetherTrade-Swarm</div>
          <div className="text-[11px] text-white/30">Sprint 6 — Dashboard Release</div>
        </div>
        <div className="text-right">
          <div className="text-[11px] text-white/30">Build</div>
          <div className="text-xs font-mono text-[#7C3AED]">v1.6.0</div>
        </div>
      </div>

      <div className="mt-4 grid grid-cols-2 sm:grid-cols-4 gap-3 text-center">
        {[
          { label: 'Strategy Pods', value: '9' },
          { label: 'Regime States', value: '4' },
          { label: 'Risk Layers', value: '4' },
          { label: 'Kill Switches', value: '6' },
        ].map((stat) => (
          <div
            key={stat.label}
            className="rounded-xl py-3 px-2"
            style={{ background: 'rgba(124,58,237,0.08)', border: '1px solid rgba(124,58,237,0.15)' }}
          >
            <div className="text-xl font-black text-[#7C3AED]">{stat.value}</div>
            <div className="text-[10px] text-white/30 mt-0.5">{stat.label}</div>
          </div>
        ))}
      </div>

      <div className="mt-4 pt-4 border-t border-white/5 flex items-center justify-between text-[11px] text-white/20">
        <span>AetherLink B.V. &copy; 2026. All rights reserved.</span>
        <div className="flex items-center gap-3">
          <button className="hover:text-white/50 transition-colors flex items-center gap-1">
            Docs <ChevronRight className="w-3 h-3" />
          </button>
          <button className="hover:text-white/50 transition-colors flex items-center gap-1">
            GitHub <ChevronRight className="w-3 h-3" />
          </button>
        </div>
      </div>
    </motion.div>
  )
}

export default function SettingsPage() {
  return (
    <div className="p-4 sm:p-6 space-y-6">
      {/* Page header */}
      <div>
        <h1 className="text-xl font-black text-white tracking-tight flex items-center gap-2">
          <Settings className="w-5 h-5 text-white/40" />
          Settings
        </h1>
        <p className="text-xs text-white/30 mt-0.5">
          API credentials, display preferences, and platform configuration
        </p>
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        <div className="space-y-6">
          <ApiKeySection />
          <NotificationSettings />
        </div>
        <div className="space-y-6">
          <DisplaySettings />
          <SecurityInfo />
        </div>
      </div>

      <AboutSection />
    </div>
  )
}
