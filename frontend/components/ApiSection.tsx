'use client'

import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useInView } from 'react-intersection-observer'
import {
  Key, Copy, Eye, EyeOff, RefreshCw, Code, Zap, Lock, Globe,
  CheckCircle, Terminal, ChevronRight,
} from 'lucide-react'
import { generateApiKey, maskApiKey, cn } from '@/lib/utils'
import { setApiKey } from '@/lib/hooks'

const PYTHON_SNIPPET = `import oracle_swarm as os_client

# Initialize client
client = os_client.Client(api_key="os_live_xxxx...")

# Get current regime
regime = client.regime.current()
print(f"Regime: {regime.type} ({regime.confidence}%)")

# Fetch strategy allocations
allocations = client.portfolio.allocations()
for pod in allocations.pods:
    print(f"{pod.name}: {pod.weight:.1%}")

# Stream live signals
with client.signals.stream() as stream:
    for signal in stream:
        print(f"[{signal.pod}] {signal.value:.4f}")`

const TS_SNIPPET = `import { OracleSwarmClient } from '@aethertrade-swarm/sdk'

const client = new OracleSwarmClient({
  apiKey: process.env.AETHERTRADE_API_KEY!,
  region: 'eu-west-1',
})

// Real-time performance metrics
const metrics = await client.performance.metrics({
  period: '30d',
  include: ['sharpe', 'drawdown', 'alpha'],
})

console.log(\`Sharpe: \${metrics.sharpe}\`)
console.log(\`Max DD: \${metrics.maxDrawdown}%\`)

// Subscribe to regime changes
client.regime.subscribe((regime) => {
  console.log(\`Regime changed: \${regime.type}\`)
})`

const ENDPOINTS = [
  { method: 'GET', path: '/v1/regime/current', desc: 'Current market regime + confidence', latency: '< 5ms' },
  { method: 'GET', path: '/v1/portfolio/allocations', desc: 'Strategy pod weights', latency: '< 8ms' },
  { method: 'GET', path: '/v1/performance/metrics', desc: 'Risk-adjusted performance stats', latency: '< 12ms' },
  { method: 'GET', path: '/v1/signals/stream', desc: 'WebSocket live signal stream', latency: 'Real-time' },
  { method: 'POST', path: '/v1/portfolio/optimize', desc: 'Run custom optimization', latency: '< 200ms' },
  { method: 'GET', path: '/v1/risk/metrics', desc: 'VaR, CVaR, drawdown metrics', latency: '< 10ms' },
]

const METHOD_COLORS: Record<string, string> = {
  GET: '#00FF94',
  POST: '#00D4FF',
  WS: '#8B5CF6',
}

function CodeBlock({ code, language }: { code: string; language: string }) {
  const [copied, setCopied] = useState(false)

  const handleCopy = async () => {
    await navigator.clipboard.writeText(code)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  // Simple syntax highlighting via span injection
  const highlight = (line: string): React.ReactNode => {
    // Comments
    if (line.trim().startsWith('#') || line.trim().startsWith('//')) {
      return <span className="text-white/30 italic">{line}</span>
    }

    let result = line
    const keywords = language === 'python'
      ? ['import', 'from', 'as', 'for', 'in', 'with', 'print', 'def', 'class', 'return', 'await', 'async']
      : ['import', 'const', 'let', 'from', 'await', 'new', 'console', 'log', 'if', 'return', 'async']

    return (
      <span>
        {line.split(/(\b(?:import|from|as|for|in|with|print|def|class|return|await|async|const|let|new|console)\b|['"`][^'"`]*['"`]|\.[\w]+\(|[{}\[\]])/g).map((part, i) => {
          if (keywords.some(k => part === k)) {
            return <span key={i} className="text-[#FF3366]">{part}</span>
          }
          if (part.startsWith("'") || part.startsWith('"') || part.startsWith('`')) {
            return <span key={i} className="text-[#00FF94]">{part}</span>
          }
          if (part.startsWith('.') && part.endsWith('(')) {
            return <span key={i} className="text-[#00D4FF]">{part}</span>
          }
          if (part === '{' || part === '}' || part === '[' || part === ']') {
            return <span key={i} className="text-[#FFB800]">{part}</span>
          }
          return part
        })}
      </span>
    )
  }

  return (
    <div
      className="relative rounded-xl overflow-hidden"
      style={{
        background: 'rgba(0,0,0,0.5)',
        border: '1px solid rgba(0, 212, 255, 0.1)',
      }}
    >
      {/* Header bar */}
      <div
        className="flex items-center justify-between px-4 py-2.5"
        style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}
      >
        <div className="flex items-center gap-2">
          <div className="flex gap-1.5">
            <div className="w-2.5 h-2.5 rounded-full bg-[#FF3366]/60" />
            <div className="w-2.5 h-2.5 rounded-full bg-[#FFB800]/60" />
            <div className="w-2.5 h-2.5 rounded-full bg-[#00FF94]/60" />
          </div>
          <span className="text-xs text-white/30 ml-2 capitalize">{language}</span>
        </div>
        <button
          onClick={handleCopy}
          className="flex items-center gap-1.5 text-xs text-white/40 hover:text-white/70 transition-colors"
          aria-label="Copy code"
        >
          <AnimatePresence mode="wait">
            {copied
              ? <motion.span key="check" initial={{ scale: 0 }} animate={{ scale: 1 }} className="text-[#00FF94]">
                  <CheckCircle className="w-3.5 h-3.5" />
                </motion.span>
              : <motion.span key="copy" initial={{ scale: 0 }} animate={{ scale: 1 }}>
                  <Copy className="w-3.5 h-3.5" />
                </motion.span>
            }
          </AnimatePresence>
          {copied ? 'Copied!' : 'Copy'}
        </button>
      </div>

      {/* Code */}
      <pre className="p-4 text-xs leading-6 overflow-x-auto font-mono">
        {code.split('\n').map((line, i) => (
          <div key={i} className="flex">
            <span className="select-none w-7 text-right mr-4 text-white/15 flex-shrink-0">
              {i + 1}
            </span>
            {highlight(line)}
          </div>
        ))}
      </pre>
    </div>
  )
}

export default function ApiSection() {
  const [ref, inView] = useInView({ threshold: 0.1, triggerOnce: true })
  const [apiKey, setLocalApiKey] = useState(() => generateApiKey())
  const [keyVisible, setKeyVisible] = useState(false)
  const [activeTab, setActiveTab] = useState<'python' | 'typescript'>('python')
  const [copiedKey, setCopiedKey] = useState(false)
  const [isGenerating, setIsGenerating] = useState(false)

  // Generate a real API key from the backend
  const generateRealKey = async () => {
    setIsGenerating(true)
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || ''
      const res = await fetch(`${apiUrl}/api/v1/keys/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: 'frontend-user' }),
      })
      if (!res.ok) throw new Error('Key generation failed')
      const data = await res.json()
      const realKey = data.api_key as string
      setLocalApiKey(realKey)
      setApiKey(realKey)
    } catch {
      // Backend unreachable — keep the demo key
      setApiKey(apiKey)
    } finally {
      setIsGenerating(false)
    }
  }

  // Auto-try on mount
  useState(() => {
    generateRealKey()
  })

  const handleCopyKey = async () => {
    await navigator.clipboard.writeText(apiKey)
    setCopiedKey(true)
    setTimeout(() => setCopiedKey(false), 2000)
  }

  return (
    <section
      ref={ref}
      className="py-20 px-4 sm:px-6 max-w-7xl mx-auto"
      aria-labelledby="api-heading"
    >
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={inView ? { opacity: 1, y: 0 } : {}}
        transition={{ duration: 0.6 }}
        className="mb-12 text-center"
      >
        <div className="flex items-center justify-center gap-3 mb-4">
          <div className="h-px w-16 bg-gradient-to-r from-transparent to-[#FFB800]/40" />
          <span className="text-xs tracking-widest text-[#FFB800] uppercase font-semibold">
            API Access
          </span>
          <div className="h-px w-16 bg-gradient-to-l from-transparent to-[#FFB800]/40" />
        </div>
        <h2
          id="api-heading"
          className="text-4xl sm:text-5xl font-black tracking-tight mb-4"
          style={{
            background: 'linear-gradient(135deg, #FFFFFF 0%, #FFB800 100%)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            backgroundClip: 'text',
          }}
        >
          Developer API
        </h2>
        <p className="text-white/40 text-base max-w-xl mx-auto">
          Programmatic access to AETHERTRADE-SWARM intelligence. REST + WebSocket APIs
          with SDKs for Python and TypeScript.
        </p>
      </motion.div>

      <div className="grid lg:grid-cols-2 gap-6">
        {/* Left: API key + endpoints */}
        <div className="space-y-5">
          {/* API Key card */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={inView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.5 }}
            className="rounded-2xl p-5"
            style={{
              background: 'rgba(255,255,255,0.02)',
              border: '1px solid rgba(255,255,255,0.07)',
            }}
          >
            <div className="flex items-center gap-2 mb-4">
              <Key className="w-4 h-4 text-[#FFB800]" />
              <h3 className="text-sm font-bold text-white">API Key</h3>
              <span
                className="ml-auto text-[10px] px-2 py-0.5 rounded-full font-medium"
                style={{
                  background: 'rgba(0,255,148,0.1)',
                  color: '#00FF94',
                  border: '1px solid rgba(0,255,148,0.2)',
                }}
              >
                LIVE
              </span>
            </div>

            <div
              className="flex items-center gap-2 p-3 rounded-xl mb-4 font-mono text-xs"
              style={{
                background: 'rgba(0,0,0,0.4)',
                border: '1px solid rgba(255,184,0,0.15)',
              }}
            >
              <span className="flex-1 text-white/70 truncate">
                {keyVisible ? apiKey : maskApiKey(apiKey)}
              </span>
              <button
                onClick={() => setKeyVisible(!keyVisible)}
                className="text-white/40 hover:text-white/70 transition-colors flex-shrink-0"
                aria-label={keyVisible ? 'Hide API key' : 'Show API key'}
              >
                {keyVisible ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
              </button>
              <button
                onClick={handleCopyKey}
                className="text-white/40 hover:text-white/70 transition-colors flex-shrink-0"
                aria-label="Copy API key"
              >
                <AnimatePresence mode="wait">
                  {copiedKey
                    ? <motion.span key="check" initial={{ scale: 0 }} animate={{ scale: 1 }}>
                        <CheckCircle className="w-3.5 h-3.5 text-[#00FF94]" />
                      </motion.span>
                    : <motion.span key="copy" initial={{ scale: 0 }} animate={{ scale: 1 }}>
                        <Copy className="w-3.5 h-3.5" />
                      </motion.span>
                  }
                </AnimatePresence>
              </button>
            </div>

            {/* Stats row */}
            <div className="grid grid-cols-3 gap-3">
              {[
                { icon: <Zap className="w-3.5 h-3.5" />, label: 'Rate Limit', value: '10K/min', color: '#00D4FF' },
                { icon: <Globe className="w-3.5 h-3.5" />, label: 'Latency', value: '< 5ms', color: '#00FF94' },
                { icon: <Lock className="w-3.5 h-3.5" />, label: 'Uptime', value: '99.99%', color: '#8B5CF6' },
              ].map((stat) => (
                <div
                  key={stat.label}
                  className="rounded-xl p-3 text-center"
                  style={{ background: stat.color + '08', border: `1px solid ${stat.color}20` }}
                >
                  <div className="flex justify-center mb-1" style={{ color: stat.color }}>
                    {stat.icon}
                  </div>
                  <div className="text-sm font-bold" style={{ color: stat.color }}>{stat.value}</div>
                  <div className="text-[10px] text-white/30">{stat.label}</div>
                </div>
              ))}
            </div>
          </motion.div>

          {/* Endpoints */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={inView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.5, delay: 0.15 }}
            className="rounded-2xl p-5"
            style={{
              background: 'rgba(255,255,255,0.02)',
              border: '1px solid rgba(255,255,255,0.07)',
            }}
          >
            <div className="flex items-center gap-2 mb-4">
              <Terminal className="w-4 h-4 text-[#00D4FF]" />
              <h3 className="text-sm font-bold text-white">Endpoints</h3>
              <span className="ml-auto text-[10px] text-white/30">v1 API</span>
            </div>

            <div className="space-y-2">
              {ENDPOINTS.map((ep, i) => (
                <motion.div
                  key={ep.path}
                  initial={{ opacity: 0, x: -10 }}
                  animate={inView ? { opacity: 1, x: 0 } : {}}
                  transition={{ duration: 0.4, delay: 0.2 + i * 0.06 }}
                  className="flex items-center gap-3 py-2 px-3 rounded-xl group cursor-default"
                  style={{ background: 'rgba(0,0,0,0.2)', border: '1px solid rgba(255,255,255,0.04)' }}
                >
                  <span
                    className="text-[10px] font-black w-10 flex-shrink-0 tracking-wider"
                    style={{ color: METHOD_COLORS[ep.method] ?? '#FFB800' }}
                  >
                    {ep.method}
                  </span>
                  <span className="text-xs font-mono text-white/60 flex-1 min-w-0 truncate">
                    {ep.path}
                  </span>
                  <span
                    className="text-[10px] text-white/30 flex-shrink-0 hidden sm:block"
                  >
                    {ep.latency}
                  </span>
                  <ChevronRight className="w-3 h-3 text-white/20 flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity" />
                </motion.div>
              ))}
            </div>
          </motion.div>
        </div>

        {/* Right: Code snippets */}
        <motion.div
          initial={{ opacity: 0, x: 30 }}
          animate={inView ? { opacity: 1, x: 0 } : {}}
          transition={{ duration: 0.6, delay: 0.2 }}
          className="space-y-4"
        >
          {/* Tab switcher */}
          <div
            className="flex rounded-xl p-1"
            style={{ background: 'rgba(0,0,0,0.4)', border: '1px solid rgba(255,255,255,0.07)' }}
          >
            {(['python', 'typescript'] as const).map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={cn(
                  'flex-1 py-2.5 rounded-lg text-xs font-medium tracking-wide transition-all duration-200',
                  activeTab === tab ? 'text-black' : 'text-white/40 hover:text-white/60'
                )}
                style={activeTab === tab ? {
                  background: '#00D4FF',
                  boxShadow: '0 0 15px rgba(0,212,255,0.3)',
                } : {}}
                aria-pressed={activeTab === tab}
              >
                <Code className="w-3 h-3 inline mr-1.5" />
                {tab === 'python' ? 'Python' : 'TypeScript'}
              </button>
            ))}
          </div>

          {/* Code block */}
          <AnimatePresence mode="wait">
            <motion.div
              key={activeTab}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              transition={{ duration: 0.25 }}
            >
              <CodeBlock
                code={activeTab === 'python' ? PYTHON_SNIPPET : TS_SNIPPET}
                language={activeTab}
              />
            </motion.div>
          </AnimatePresence>

          {/* Quick start */}
          <div
            className="rounded-2xl p-5"
            style={{
              background: 'rgba(255,184,0,0.04)',
              border: '1px solid rgba(255,184,0,0.1)',
            }}
          >
            <h4 className="text-sm font-bold text-[#FFB800] mb-3">Quick Install</h4>
            <div className="space-y-2">
              {[
                { label: 'Python', cmd: 'pip install aethertrade-swarm' },
                { label: 'Node.js', cmd: 'npm install @aethertrade-swarm/sdk' },
              ].map(({ label, cmd }) => (
                <div
                  key={label}
                  className="flex items-center justify-between p-2.5 rounded-lg font-mono text-xs"
                  style={{ background: 'rgba(0,0,0,0.4)', border: '1px solid rgba(255,255,255,0.05)' }}
                >
                  <span className="text-white/30 mr-3">{label}</span>
                  <span className="text-[#00D4FF] flex-1">$ {cmd}</span>
                </div>
              ))}
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  )
}
