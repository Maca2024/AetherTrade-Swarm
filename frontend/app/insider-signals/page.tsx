'use client'

import { useState, useRef } from 'react'
import { motion, useInView } from 'framer-motion'
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts'
import {
  Eye,
  Zap,
  ChevronDown,
  TrendingUp,
  Shield,
  Database,
  Bell,
  Check,
  ArrowRight,
  Activity,
  BarChart2,
  Lock,
  Webhook,
  Slack,
  Filter,
} from 'lucide-react'
import AuthButton from '@/components/AuthButton'

// --- Types ---

interface SignalRow {
  ticker: string
  company: string
  insiders: number
  totalValue: string
  strength: number
  date: string
}

interface FaqItem {
  question: string
  answer: string
}

// --- Constants ---

const EQUITY_DATA = [
  { month: 'Jan', strategy: 10000, spy: 10000 },
  { month: 'Feb', strategy: 10420, spy: 10210 },
  { month: 'Mrt', strategy: 10180, spy: 10050 },
  { month: 'Apr', strategy: 10890, spy: 10380 },
  { month: 'Mei', strategy: 11340, spy: 10520 },
  { month: 'Jun', strategy: 10910, spy: 10290 },
  { month: 'Jul', strategy: 11650, spy: 10610 },
  { month: 'Aug', strategy: 12240, spy: 10820 },
  { month: 'Sep', strategy: 11980, spy: 10640 },
  { month: 'Okt', strategy: 12580, spy: 10780 },
  { month: 'Nov', strategy: 12910, spy: 10940 },
  { month: 'Dec', strategy: 13200, spy: 11100 },
]

const MAX_DRAWDOWN_MONTHS = ['Jun', 'Sep']

const SIGNALS: SignalRow[] = [
  {
    ticker: 'NVDA',
    company: 'NVIDIA Corporation',
    insiders: 4,
    totalValue: '$2.4M',
    strength: 85,
    date: '2 dagen geleden',
  },
  {
    ticker: 'AAPL',
    company: 'Apple Inc.',
    insiders: 3,
    totalValue: '$1.1M',
    strength: 72,
    date: '5 dagen geleden',
  },
  {
    ticker: 'META',
    company: 'Meta Platforms',
    insiders: 5,
    totalValue: '$4.8M',
    strength: 92,
    date: '1 week geleden',
  },
  {
    ticker: 'MSFT',
    company: 'Microsoft Corp.',
    insiders: 3,
    totalValue: '$1.8M',
    strength: 68,
    date: '9 dagen geleden',
  },
  {
    ticker: 'AMZN',
    company: 'Amazon.com Inc.',
    insiders: 4,
    totalValue: '$3.2M',
    strength: 79,
    date: '12 dagen geleden',
  },
]

const FAQS: FaqItem[] = [
  {
    question: 'Hoe werkt insider trading signaling?',
    answer:
      'Bedrijfsinsiders — CEO\'s, CFO\'s en directieleden — zijn wettelijk verplicht elke aandelelaankoop van hun eigen bedrijf te melden bij de SEC via een Form 4 filing. Wanneer meerdere insiders tegelijk kopen, is dat een statistisch significant signaal van vertrouwen in de toekomst van het bedrijf. Ons algoritme scant elke nieuwe filing in real-time en detecteert cluster patronen automatisch.',
  },
  {
    question: 'Is dit legaal om te gebruiken?',
    answer:
      'Absoluut ja. Form 4 filings zijn openbare data, verplicht gepubliceerd door de SEC. Wij lezen uitsluitend openbare bronnen en sturen geen enkele geheime of niet-publieke informatie door. Het volgen van legaal gemelde insider transacties is een erkende en wijdverspreide beleggingsstrategie.',
  },
  {
    question: 'Welke alpha kan ik realistisch verwachten?',
    answer:
      'Onze backtest over 2020–2025 toont een gemiddeld jaarrendement van 22–32%, afhankelijk van marktregime. De Sharpe ratio van 1.42 wijst op aantrekkelijk risicogecorrigeerd rendement. Houd rekening met transactiekosten en slippage in live trading. Rendementen uit het verleden bieden geen garantie voor de toekomst.',
  },
  {
    question: 'Hoe en wanneer ontvang ik de signalen?',
    answer:
      'Starter-gebruikers ontvangen dagelijks een gestructureerde email met alle nieuwe clusters van de afgelopen 24 uur. Pro-gebruikers hebben bovendien toegang tot real-time REST API en WebSocket feed, plus configureerbare webhooks naar Slack, Discord of je eigen systeem — signalen binnen seconden na de SEC filing.',
  },
  {
    question: 'Kan ik op elk moment opzeggen?',
    answer:
      'Ja, geen bochten. Je kunt je abonnement op elk moment opzeggen vanuit je accountinstellingen. Je houdt toegang tot het einde van de betaalde periode. We hanteren geen opzegtermijnen of verborgen kosten. De 14-dagen gratis proef vereist geen creditcard.',
  },
]

// --- Small helpers ---

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-[11px] font-bold tracking-widest uppercase mb-4"
      style={{
        background: 'rgba(124,58,237,0.12)',
        border: '1px solid rgba(124,58,237,0.3)',
        color: '#A78BFA',
      }}
    >
      {children}
    </div>
  )
}

function GlassCard({
  children,
  className = '',
  featured = false,
  style,
}: {
  children: React.ReactNode
  className?: string
  featured?: boolean
  style?: React.CSSProperties
}) {
  return (
    <div
      className={`rounded-2xl ${className}`}
      style={{
        background: featured ? 'rgba(124,58,237,0.08)' : 'rgba(255,255,255,0.03)',
        border: featured
          ? '1px solid rgba(124,58,237,0.4)'
          : '1px solid rgba(255,255,255,0.07)',
        backdropFilter: 'blur(20px)',
        WebkitBackdropFilter: 'blur(20px)',
        boxShadow: featured
          ? '0 0 40px rgba(124,58,237,0.12), 0 8px 32px rgba(0,0,0,0.4)'
          : '0 8px 32px rgba(0,0,0,0.4)',
        ...style,
      }}
    >
      {children}
    </div>
  )
}

function StrengthBadge({ value }: { value: number }) {
  const color =
    value >= 85 ? '#00FF94' : value >= 70 ? '#FFB800' : '#00D4FF'
  return (
    <div className="flex items-center gap-2">
      <div
        className="h-1.5 rounded-full overflow-hidden"
        style={{ width: 48, background: 'rgba(255,255,255,0.08)' }}
      >
        <div
          className="h-full rounded-full transition-all"
          style={{ width: `${value}%`, background: color }}
        />
      </div>
      <span className="text-xs font-bold tabular-nums" style={{ color }}>
        {value}/100
      </span>
    </div>
  )
}

// Custom tooltip for the chart
function ChartTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean
  payload?: Array<{ value: number; name: string; color: string }>
  label?: string
}) {
  if (!active || !payload?.length) return null
  return (
    <div
      className="rounded-xl px-4 py-3 text-xs"
      style={{
        background: 'rgba(7,7,15,0.95)',
        border: '1px solid rgba(255,255,255,0.1)',
        backdropFilter: 'blur(20px)',
      }}
    >
      <div className="font-bold text-white/60 mb-2">{label}</div>
      {payload.map((entry) => (
        <div key={entry.name} className="flex items-center gap-2 mb-1">
          <div className="w-2 h-2 rounded-full" style={{ background: entry.color }} />
          <span className="text-white/50">{entry.name}:</span>
          <span className="font-bold tabular-nums" style={{ color: entry.color }}>
            ${entry.value.toLocaleString()}
          </span>
        </div>
      ))}
    </div>
  )
}

// --- Section: Nav ---

function Nav() {
  return (
    <nav
      className="fixed top-0 left-0 right-0 z-50 flex items-center justify-between px-4 sm:px-6 h-16"
      style={{
        background: 'rgba(4,4,10,0.8)',
        borderBottom: '1px solid rgba(255,255,255,0.06)',
        backdropFilter: 'blur(20px)',
        WebkitBackdropFilter: 'blur(20px)',
      }}
    >
      <div className="flex items-center gap-3">
        <div
          className="w-8 h-8 rounded-lg flex items-center justify-center text-xs font-black"
          style={{
            background: 'linear-gradient(135deg, rgba(124,58,237,0.4), rgba(0,212,255,0.2))',
            border: '1px solid rgba(124,58,237,0.4)',
            color: '#A78BFA',
          }}
        >
          IS
        </div>
        <div>
          <div
            className="text-sm font-black tracking-wider"
            style={{
              background: 'linear-gradient(135deg, #FFFFFF 0%, #A78BFA 100%)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              backgroundClip: 'text',
            }}
          >
            INSIDER SIGNALS
          </div>
          <div className="text-[9px] text-white/25 tracking-widest hidden sm:block">
            BY AETHERTRADE
          </div>
        </div>
      </div>

      <div className="flex items-center gap-2 sm:gap-4">
        <a
          href="#prijzen"
          className="text-xs text-white/40 hover:text-white/70 transition-colors hidden sm:inline"
        >
          Prijzen
        </a>
        <a
          href="#backtest"
          className="text-xs text-white/40 hover:text-white/70 transition-colors hidden sm:inline"
        >
          Backtest
        </a>
        <AuthButton />
      </div>
    </nav>
  )
}

// --- Section: Hero ---

function HeroSection() {
  const ref = useRef(null)
  const inView = useInView(ref, { once: true })

  return (
    <section
      ref={ref}
      className="relative min-h-screen flex flex-col items-center justify-center text-center px-4 sm:px-6 pt-24 pb-16 overflow-hidden"
    >
      {/* Ambient orbs */}
      <div className="absolute inset-0 pointer-events-none" aria-hidden="true">
        <div
          className="absolute top-0 left-1/2 -translate-x-1/2 w-[600px] h-[400px] rounded-full opacity-[0.06]"
          style={{
            background: 'radial-gradient(circle, #7C3AED 0%, transparent 70%)',
            filter: 'blur(60px)',
          }}
        />
        <div
          className="absolute bottom-0 right-0 w-[400px] h-[300px] rounded-full opacity-[0.04]"
          style={{
            background: 'radial-gradient(circle, #00D4FF 0%, transparent 70%)',
            filter: 'blur(80px)',
          }}
        />
        {/* Grid */}
        <div
          className="absolute inset-0 opacity-[0.3]"
          style={{
            backgroundImage:
              'linear-gradient(rgba(124,58,237,0.06) 1px, transparent 1px), linear-gradient(90deg, rgba(124,58,237,0.06) 1px, transparent 1px)',
            backgroundSize: '40px 40px',
          }}
        />
      </div>

      <div className="relative z-10 max-w-3xl mx-auto">
        {/* Badge */}
        <motion.div
          initial={{ opacity: 0, y: -12 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.5 }}
          className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full text-[11px] font-bold tracking-widest uppercase mb-8"
          style={{
            background: 'rgba(0,212,255,0.08)',
            border: '1px solid rgba(0,212,255,0.2)',
            color: '#00D4FF',
          }}
        >
          <div className="w-1.5 h-1.5 rounded-full bg-[#00FF94] animate-pulse" />
          LIVE DATA &bull; SEC EDGAR &bull; GRATIS PROEFPERIODE
        </motion.div>

        {/* Headline */}
        <motion.h1
          initial={{ opacity: 0, y: 16 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.6, delay: 0.1 }}
          className="text-4xl sm:text-5xl lg:text-6xl font-black tracking-tight leading-[1.05] mb-6"
        >
          <span className="text-white">Handel Mee Met</span>
          <br />
          <span
            style={{
              background: 'linear-gradient(135deg, #7C3AED 0%, #00D4FF 100%)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              backgroundClip: 'text',
            }}
          >
            Corporate Insiders
          </span>
        </motion.h1>

        {/* Subheadline */}
        <motion.p
          initial={{ opacity: 0, y: 16 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.6, delay: 0.2 }}
          className="text-base sm:text-lg text-white/50 leading-relaxed mb-8 max-w-xl mx-auto"
        >
          AI-gedetecteerde cluster koop signalen. Wanneer 3+ bestuurders hun eigen
          aandelen kopen, krijg jij het signaal.
        </motion.p>

        {/* Key stat */}
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={inView ? { opacity: 1, scale: 1 } : {}}
          transition={{ duration: 0.5, delay: 0.3 }}
          className="inline-flex flex-col items-center mb-10"
        >
          <div
            className="text-5xl sm:text-6xl font-black tabular-nums mb-1"
            style={{
              background: 'linear-gradient(135deg, #00FF94 0%, #00D4FF 100%)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              backgroundClip: 'text',
            }}
          >
            22–32%
          </div>
          <div className="text-sm text-white/40">
            historisch jaarrendement{' '}
            <span className="italic text-white/25">*backtested 2020–2025</span>
          </div>
        </motion.div>

        {/* CTAs */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.5, delay: 0.4 }}
          className="flex flex-col sm:flex-row items-center justify-center gap-4"
        >
          <a
            href="#prijzen"
            className="flex items-center gap-2 px-6 py-3 rounded-xl text-sm font-bold text-white transition-all hover:scale-105 active:scale-100"
            style={{
              background: 'linear-gradient(135deg, #7C3AED, #00D4FF)',
              boxShadow: '0 0 30px rgba(124,58,237,0.4), 0 4px 24px rgba(0,0,0,0.4)',
            }}
          >
            Start 14-dagen gratis proef
            <ArrowRight className="w-4 h-4" />
          </a>
          <a
            href="#signalen"
            className="flex items-center gap-2 px-6 py-3 rounded-xl text-sm font-medium text-white/60 hover:text-white transition-colors"
            style={{
              background: 'rgba(255,255,255,0.04)',
              border: '1px solid rgba(255,255,255,0.1)',
            }}
          >
            <Eye className="w-4 h-4" />
            Bekijk live signalen
          </a>
        </motion.div>
      </div>

      {/* Scroll indicator */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={inView ? { opacity: 1 } : {}}
        transition={{ delay: 1 }}
        className="absolute bottom-8 left-1/2 -translate-x-1/2 flex flex-col items-center gap-1"
        aria-hidden="true"
      >
        <div className="text-[10px] text-white/20 tracking-widest uppercase">Scroll</div>
        <ChevronDown className="w-4 h-4 text-white/20 animate-bounce" />
      </motion.div>
    </section>
  )
}

// --- Section: How It Works ---

function HowItWorksSection() {
  const ref = useRef(null)
  const inView = useInView(ref, { once: true, margin: '-100px' })

  const steps = [
    {
      step: '01',
      icon: <Database className="w-6 h-6" />,
      title: 'SEC EDGAR Monitoring',
      description:
        'We scannen elke nieuwe Form 4 filing in real-time — de wettelijk verplichte melding die insiders moeten doen binnen 2 handelsdagen na een aankoop.',
      color: '#00D4FF',
    },
    {
      step: '02',
      icon: <Activity className="w-6 h-6" />,
      title: 'AI Cluster Detectie',
      description:
        'Ons algoritme detecteert wanneer 3 of meer insiders van hetzelfde bedrijf binnen 10 dagen kopen — een bewezen statistisch signaal van insider vertrouwen.',
      color: '#7C3AED',
    },
    {
      step: '03',
      icon: <Bell className="w-6 h-6" />,
      title: 'Signal naar Jou',
      description:
        'Dagelijkse email digest met alle nieuwe clusters, plus real-time API en webhook notificaties voor Pro-gebruikers die directe integratie in hun trading setup willen.',
      color: '#00FF94',
    },
  ]

  return (
    <section className="py-24 px-4 sm:px-6 max-w-7xl mx-auto" ref={ref}>
      <div className="text-center mb-16">
        <SectionLabel>
          <Zap className="w-3 h-3" />
          Hoe het werkt
        </SectionLabel>
        <h2 className="text-3xl sm:text-4xl font-black text-white">
          Van SEC Filing naar Trading Signaal
        </h2>
        <p className="text-white/40 mt-3 max-w-md mx-auto text-sm">
          Volledig geautomatiseerd. Geen ruis, alleen significante clusters.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 relative">
        {/* Connector line (desktop only) */}
        <div
          className="hidden md:block absolute top-14 left-1/3 right-1/3 h-px"
          style={{
            background: 'linear-gradient(90deg, transparent, rgba(124,58,237,0.3), transparent)',
          }}
          aria-hidden="true"
        />

        {steps.map((step, i) => (
          <motion.div
            key={step.step}
            initial={{ opacity: 0, y: 24 }}
            animate={inView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.5, delay: i * 0.15 }}
          >
            <GlassCard className="p-7 h-full relative overflow-hidden">
              {/* Top accent line */}
              <div
                className="absolute top-0 left-6 right-6 h-px rounded-full"
                style={{
                  background: `linear-gradient(90deg, transparent, ${step.color}50, transparent)`,
                }}
                aria-hidden="true"
              />
              <div className="flex items-start gap-4 mb-5">
                <div
                  className="w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0"
                  style={{
                    background: `${step.color}15`,
                    border: `1px solid ${step.color}30`,
                    color: step.color,
                  }}
                >
                  {step.icon}
                </div>
                <div
                  className="text-4xl font-black opacity-10 ml-auto"
                  style={{ color: step.color }}
                >
                  {step.step}
                </div>
              </div>
              <h3 className="text-base font-bold text-white mb-3">{step.title}</h3>
              <p className="text-sm text-white/40 leading-relaxed">{step.description}</p>
            </GlassCard>
          </motion.div>
        ))}
      </div>
    </section>
  )
}

// --- Section: Live Signals Preview ---

function SignalsSection() {
  const ref = useRef(null)
  const inView = useInView(ref, { once: true, margin: '-80px' })

  return (
    <section id="signalen" className="py-24 px-4 sm:px-6 max-w-7xl mx-auto" ref={ref}>
      <div className="text-center mb-12">
        <SectionLabel>
          <div className="w-1.5 h-1.5 rounded-full bg-[#00FF94] animate-pulse" />
          Live signalen
        </SectionLabel>
        <h2 className="text-3xl sm:text-4xl font-black text-white">
          Recente Cluster Aankopen
        </h2>
        <p className="text-white/40 mt-3 text-sm">
          Voorbeelddata — abonnees ontvangen alle clusters real-time
        </p>
      </div>

      <motion.div
        initial={{ opacity: 0, y: 24 }}
        animate={inView ? { opacity: 1, y: 0 } : {}}
        transition={{ duration: 0.6 }}
      >
        <GlassCard className="overflow-hidden">
          {/* Table header */}
          <div
            className="grid grid-cols-[1fr_2fr_1fr_1fr_1.5fr_1fr] gap-4 px-6 py-4 text-[10px] font-bold uppercase tracking-widest text-white/25"
            style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}
          >
            <div>Ticker</div>
            <div className="hidden sm:block">Bedrijf</div>
            <div># Insiders</div>
            <div className="hidden md:block">Totale Waarde</div>
            <div>Sterkte</div>
            <div>Datum</div>
          </div>

          {/* Table rows */}
          {SIGNALS.map((signal, i) => (
            <motion.div
              key={signal.ticker}
              initial={{ opacity: 0, x: -12 }}
              animate={inView ? { opacity: 1, x: 0 } : {}}
              transition={{ duration: 0.4, delay: 0.2 + i * 0.08 }}
              className="grid grid-cols-[1fr_2fr_1fr_1fr_1.5fr_1fr] gap-4 px-6 py-4 items-center hover:bg-white/[0.02] transition-colors"
              style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}
            >
              {/* Ticker */}
              <div>
                <span
                  className="text-sm font-black px-2 py-0.5 rounded"
                  style={{
                    background: 'rgba(124,58,237,0.15)',
                    border: '1px solid rgba(124,58,237,0.2)',
                    color: '#A78BFA',
                  }}
                >
                  {signal.ticker}
                </span>
              </div>

              {/* Company */}
              <div className="hidden sm:block text-sm text-white/60 truncate">
                {signal.company}
              </div>

              {/* Insiders */}
              <div className="flex items-center gap-1.5">
                <div className="flex -space-x-1" aria-label={`${signal.insiders} insiders`}>
                  {Array.from({ length: Math.min(signal.insiders, 5) }).map((_, j) => (
                    <div
                      key={j}
                      className="w-5 h-5 rounded-full border border-void-900 flex items-center justify-center text-[8px] font-bold"
                      style={{ background: `hsl(${260 + j * 15}, 60%, 55%)` }}
                      aria-hidden="true"
                    />
                  ))}
                </div>
                <span className="text-xs text-white/40">{signal.insiders}</span>
              </div>

              {/* Total value */}
              <div className="hidden md:block text-sm font-bold text-white/70 tabular-nums">
                {signal.totalValue}
              </div>

              {/* Strength */}
              <div>
                <StrengthBadge value={signal.strength} />
              </div>

              {/* Date */}
              <div className="text-xs text-white/30">{signal.date}</div>
            </motion.div>
          ))}

          {/* Blurred teaser row */}
          <div
            className="px-6 py-4 text-center text-xs text-white/20 select-none"
            style={{ borderTop: '1px solid rgba(255,255,255,0.04)' }}
          >
            <span
              className="blur-sm select-none"
              aria-hidden="true"
            >
              TSLA | Tesla Inc. | 6 insiders | $7.2M | 96/100 | gisteren
            </span>
            <span className="ml-3 not-italic text-white/40 no-blur">
              + meer signalen voor abonnees
            </span>
          </div>
        </GlassCard>
      </motion.div>
    </section>
  )
}

// --- Section: Backtest Results ---

function BacktestSection() {
  const ref = useRef(null)
  const inView = useInView(ref, { once: true, margin: '-80px' })

  const stats = [
    { label: 'Totaal rendement', value: '+32%', color: '#00FF94', icon: <TrendingUp className="w-4 h-4" /> },
    { label: 'Sharpe ratio', value: '1.42', color: '#00D4FF', icon: <BarChart2 className="w-4 h-4" /> },
    { label: 'Win rate', value: '58%', color: '#A78BFA', icon: <Activity className="w-4 h-4" /> },
    { label: 'Max drawdown', value: '-11%', color: '#FF3366', icon: <TrendingUp className="w-4 h-4 rotate-180" /> },
  ]

  return (
    <section id="backtest" className="py-24 px-4 sm:px-6 max-w-7xl mx-auto" ref={ref}>
      <div className="text-center mb-12">
        <SectionLabel>
          <BarChart2 className="w-3 h-3" />
          Backtest 2020–2025
        </SectionLabel>
        <h2 className="text-3xl sm:text-4xl font-black text-white">
          Performance vs. S&amp;P 500
        </h2>
        <p className="text-white/40 mt-3 text-sm">
          $10.000 initieel kapitaal, geen leverage, dagelijks herbalanceren op signaal
        </p>
      </div>

      <motion.div
        initial={{ opacity: 0, y: 24 }}
        animate={inView ? { opacity: 1, y: 0 } : {}}
        transition={{ duration: 0.7 }}
      >
        <GlassCard className="p-6 sm:p-8 mb-6">
          {/* Legend */}
          <div className="flex items-center gap-6 mb-6">
            <div className="flex items-center gap-2">
              <div className="w-8 h-0.5 rounded-full" style={{ background: '#7C3AED' }} />
              <span className="text-xs text-white/50">Insider Signals</span>
            </div>
            <div className="flex items-center gap-2">
              <div
                className="w-8 h-0.5 rounded-full border-dashed"
                style={{ borderTop: '2px dashed rgba(0,212,255,0.4)', background: 'none' }}
              />
              <span className="text-xs text-white/30">SPY (baseline)</span>
            </div>
            <div className="ml-auto flex items-center gap-2">
              <div className="w-3 h-3 rounded-sm opacity-40" style={{ background: '#FF3366' }} />
              <span className="text-xs text-white/30">Max drawdown periode</span>
            </div>
          </div>

          <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={EQUITY_DATA} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="stratGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#7C3AED" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#7C3AED" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="spyGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#00D4FF" stopOpacity={0.1} />
                  <stop offset="95%" stopColor="#00D4FF" stopOpacity={0} />
                </linearGradient>
              </defs>

              <CartesianGrid
                strokeDasharray="3 3"
                stroke="rgba(255,255,255,0.04)"
                vertical={false}
              />
              <XAxis
                dataKey="month"
                tick={{ fill: 'rgba(255,255,255,0.25)', fontSize: 11 }}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                tickFormatter={(v: number) => `$${(v / 1000).toFixed(0)}K`}
                tick={{ fill: 'rgba(255,255,255,0.25)', fontSize: 11 }}
                axisLine={false}
                tickLine={false}
                width={48}
              />
              <Tooltip content={<ChartTooltip />} />

              {/* Drawdown reference area */}
              {MAX_DRAWDOWN_MONTHS.map((month) => (
                <ReferenceLine
                  key={month}
                  x={month}
                  stroke="rgba(255,51,102,0.15)"
                  strokeWidth={24}
                />
              ))}

              <Area
                type="monotone"
                dataKey="spy"
                name="SPY"
                stroke="rgba(0,212,255,0.3)"
                strokeWidth={1.5}
                strokeDasharray="4 4"
                fill="url(#spyGrad)"
                dot={false}
              />
              <Area
                type="monotone"
                dataKey="strategy"
                name="Insider Signals"
                stroke="#7C3AED"
                strokeWidth={2.5}
                fill="url(#stratGrad)"
                dot={false}
                activeDot={{ r: 5, fill: '#7C3AED', stroke: '#A78BFA', strokeWidth: 2 }}
              />
            </AreaChart>
          </ResponsiveContainer>
        </GlassCard>
      </motion.div>

      {/* Stat cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {stats.map((stat, i) => (
          <motion.div
            key={stat.label}
            initial={{ opacity: 0, y: 16 }}
            animate={inView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.4, delay: 0.4 + i * 0.08 }}
          >
            <GlassCard className="p-5 relative overflow-hidden">
              <div
                className="absolute top-0 left-4 right-4 h-px"
                style={{ background: `linear-gradient(90deg, transparent, ${stat.color}40, transparent)` }}
                aria-hidden="true"
              />
              <div className="flex items-center gap-2 mb-2" style={{ color: stat.color }}>
                {stat.icon}
                <span className="text-[10px] font-bold uppercase tracking-widest text-white/30">
                  {stat.label}
                </span>
              </div>
              <div className="text-2xl font-black tabular-nums" style={{ color: stat.color }}>
                {stat.value}
              </div>
            </GlassCard>
          </motion.div>
        ))}
      </div>

      <p className="text-center text-[11px] text-white/20 mt-6 italic">
        *Backtested resultaten zijn hypothetisch en bieden geen garantie voor toekomstige performance.
        Rendementen zijn berekend vóór transactiekosten en belastingen.
      </p>
    </section>
  )
}

// --- Section: Pricing ---

function PricingSection() {
  const ref = useRef(null)
  const inView = useInView(ref, { once: true, margin: '-80px' })

  const starterFeatures = [
    'Dagelijkse email met nieuwe clusters',
    'Web dashboard toegang',
    '30 dagen historische data',
    'Email support',
  ]

  const proFeatures = [
    'Alles van Starter',
    'Real-time API (REST + WebSocket)',
    '5 jaar historische data',
    'Webhook notificaties',
    'Slack & Discord integratie',
    'Custom filter regels',
    'Priority support',
  ]

  return (
    <section id="prijzen" className="py-24 px-4 sm:px-6 max-w-5xl mx-auto" ref={ref}>
      <div className="text-center mb-14">
        <SectionLabel>
          <Lock className="w-3 h-3" />
          Prijzen
        </SectionLabel>
        <h2 className="text-3xl sm:text-4xl font-black text-white">
          Kies Jouw Toegangsniveau
        </h2>
        <p className="text-white/40 mt-3 text-sm">
          14 dagen gratis proberen. Geen creditcard vereist.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-stretch">
        {/* Starter */}
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={inView ? { opacity: 1, x: 0 } : {}}
          transition={{ duration: 0.5, delay: 0.1 }}
          className="h-full"
        >
          <GlassCard className="p-8 h-full flex flex-col">
            <div className="mb-6">
              <div className="text-xs font-bold uppercase tracking-widest text-white/30 mb-2">
                Starter
              </div>
              <div className="flex items-baseline gap-1 mb-1">
                <span className="text-4xl font-black text-white">€49</span>
                <span className="text-sm text-white/30">/maand</span>
              </div>
              <p className="text-sm text-white/40">
                Dagelijkse signalen voor actieve beleggers
              </p>
            </div>

            <ul className="space-y-3 mb-8 flex-1">
              {starterFeatures.map((feature) => (
                <li key={feature} className="flex items-start gap-3 text-sm text-white/60">
                  <Check className="w-4 h-4 text-[#00FF94] flex-shrink-0 mt-0.5" />
                  {feature}
                </li>
              ))}
            </ul>

            <a
              href="#"
              className="w-full flex items-center justify-center gap-2 py-3 rounded-xl text-sm font-bold text-white/70 hover:text-white transition-all"
              style={{
                background: 'rgba(255,255,255,0.06)',
                border: '1px solid rgba(255,255,255,0.12)',
              }}
            >
              Start gratis proef
            </a>
          </GlassCard>
        </motion.div>

        {/* Pro */}
        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={inView ? { opacity: 1, x: 0 } : {}}
          transition={{ duration: 0.5, delay: 0.2 }}
          className="h-full"
        >
          <GlassCard featured className="p-8 h-full flex flex-col relative overflow-hidden">
            {/* Popular badge */}
            <div
              className="absolute top-4 right-4 px-2.5 py-1 rounded-full text-[10px] font-bold uppercase tracking-widest"
              style={{
                background: 'linear-gradient(135deg, #7C3AED, #00D4FF)',
                color: 'white',
              }}
            >
              Meest gekozen
            </div>

            {/* Glow orb */}
            <div
              className="absolute -top-16 -right-16 w-48 h-48 rounded-full pointer-events-none"
              style={{
                background: 'radial-gradient(circle, rgba(124,58,237,0.15) 0%, transparent 70%)',
              }}
              aria-hidden="true"
            />

            <div className="mb-6">
              <div className="text-xs font-bold uppercase tracking-widest text-[#A78BFA] mb-2">
                Pro
              </div>
              <div className="flex items-baseline gap-1 mb-1">
                <span className="text-4xl font-black text-white">€149</span>
                <span className="text-sm text-white/30">/maand</span>
              </div>
              <p className="text-sm text-white/40">
                Real-time toegang voor professionele traders
              </p>
            </div>

            <ul className="space-y-3 mb-8 flex-1">
              {proFeatures.map((feature, i) => {
                const icons: Record<number, React.ReactNode> = {
                  1: <Webhook className="w-4 h-4" />,
                  2: <Database className="w-4 h-4" />,
                  3: <Bell className="w-4 h-4" />,
                  4: <Slack className="w-4 h-4" />,
                  5: <Filter className="w-4 h-4" />,
                }
                return (
                  <li key={feature} className="flex items-start gap-3 text-sm text-white/70">
                    <div style={{ color: '#A78BFA', flexShrink: 0, marginTop: 2 }}>
                      {icons[i] ?? <Check className="w-4 h-4" />}
                    </div>
                    {i === 0 ? (
                      <span className="text-white/40">{feature}</span>
                    ) : (
                      feature
                    )}
                  </li>
                )
              })}
            </ul>

            <a
              href="#"
              className="w-full flex items-center justify-center gap-2 py-3 rounded-xl text-sm font-bold text-white transition-all hover:scale-[1.02] active:scale-100"
              style={{
                background: 'linear-gradient(135deg, #7C3AED, #00D4FF)',
                boxShadow: '0 0 24px rgba(124,58,237,0.4)',
              }}
            >
              Start gratis proef
              <ArrowRight className="w-4 h-4" />
            </a>
          </GlassCard>
        </motion.div>
      </div>
    </section>
  )
}

// --- Section: FAQ ---

function FaqItem({ item, index, inView }: { item: FaqItem; index: number; inView: boolean }) {
  const [open, setOpen] = useState(false)

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={inView ? { opacity: 1, y: 0 } : {}}
      transition={{ duration: 0.4, delay: index * 0.08 }}
    >
      <GlassCard className="overflow-hidden">
        <button
          onClick={() => setOpen((prev) => !prev)}
          className="w-full flex items-center justify-between px-6 py-5 text-left focus-visible:outline-none"
          aria-expanded={open}
        >
          <span className="text-sm font-semibold text-white pr-4">{item.question}</span>
          <ChevronDown
            className="w-4 h-4 text-white/30 flex-shrink-0 transition-transform duration-300"
            style={{ transform: open ? 'rotate(180deg)' : 'rotate(0deg)' }}
            aria-hidden="true"
          />
        </button>

        <motion.div
          initial={false}
          animate={{ height: open ? 'auto' : 0, opacity: open ? 1 : 0 }}
          transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
          style={{ overflow: 'hidden' }}
        >
          <div
            className="px-6 pb-5 text-sm text-white/40 leading-relaxed"
            style={{ borderTop: '1px solid rgba(255,255,255,0.05)' }}
          >
            <div className="pt-4">{item.answer}</div>
          </div>
        </motion.div>
      </GlassCard>
    </motion.div>
  )
}

function FaqSection() {
  const ref = useRef(null)
  const inView = useInView(ref, { once: true, margin: '-80px' })

  return (
    <section className="py-24 px-4 sm:px-6 max-w-3xl mx-auto" ref={ref}>
      <div className="text-center mb-12">
        <SectionLabel>
          <Shield className="w-3 h-3" />
          FAQ
        </SectionLabel>
        <h2 className="text-3xl sm:text-4xl font-black text-white">
          Veelgestelde Vragen
        </h2>
      </div>

      <div className="space-y-3">
        {FAQS.map((item, i) => (
          <FaqItem key={item.question} item={item} index={i} inView={inView} />
        ))}
      </div>
    </section>
  )
}

// --- Section: Footer ---

function InsiderSignalsFooter() {
  const ref = useRef(null)
  const inView = useInView(ref, { once: true, margin: '-60px' })

  return (
    <footer
      ref={ref}
      className="relative border-t overflow-hidden"
      style={{ borderColor: 'rgba(255,255,255,0.06)' }}
    >
      <div
        className="absolute inset-0 pointer-events-none"
        aria-hidden="true"
        style={{
          background: 'radial-gradient(ellipse at 50% 100%, rgba(124,58,237,0.04) 0%, transparent 60%)',
        }}
      />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-12 relative z-10">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-10 mb-10">
          {/* Brand */}
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={inView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.5 }}
          >
            <div className="flex items-center gap-3 mb-4">
              <div
                className="w-9 h-9 rounded-xl flex items-center justify-center text-xs font-black"
                style={{
                  background: 'linear-gradient(135deg, rgba(124,58,237,0.3), rgba(0,212,255,0.15))',
                  border: '1px solid rgba(124,58,237,0.3)',
                  color: '#A78BFA',
                }}
              >
                IS
              </div>
              <div>
                <div
                  className="text-sm font-black tracking-wider"
                  style={{
                    background: 'linear-gradient(135deg, #FFFFFF 0%, #A78BFA 100%)',
                    WebkitBackgroundClip: 'text',
                    WebkitTextFillColor: 'transparent',
                    backgroundClip: 'text',
                  }}
                >
                  INSIDER SIGNALS
                </div>
                <div className="text-[9px] text-white/25 tracking-widest">BY AETHERTRADE</div>
              </div>
            </div>
            <p className="text-xs text-white/30 leading-relaxed">
              AI-gedetecteerde SEC Form 4 cluster signalen. Powered by AetherLink B.V.
            </p>
          </motion.div>

          {/* AetherTrade producten */}
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={inView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.5, delay: 0.1 }}
          >
            <h4 className="text-[10px] font-bold uppercase tracking-widest text-white/30 mb-4">
              AetherTrade Producten
            </h4>
            <ul className="space-y-2.5">
              {[
                { label: 'SWARM Platform', href: '/' },
                { label: 'Insider Signals', href: '/insider-signals' },
                { label: 'Options Flow', href: '#' },
                { label: 'Dark Pool Radar', href: '#' },
                { label: 'Macro Dashboard', href: '#' },
              ].map((link) => (
                <li key={link.label}>
                  <a
                    href={link.href}
                    className="text-xs text-white/30 hover:text-white/60 transition-colors"
                  >
                    {link.label}
                  </a>
                </li>
              ))}
            </ul>
          </motion.div>

          {/* Legal */}
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={inView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.5, delay: 0.2 }}
          >
            <h4 className="text-[10px] font-bold uppercase tracking-widest text-white/30 mb-4">
              Juridisch
            </h4>
            <ul className="space-y-2.5 mb-6">
              {['Privacybeleid', 'Gebruiksvoorwaarden', 'Cookie-instellingen'].map((item) => (
                <li key={item}>
                  <a href="#" className="text-xs text-white/30 hover:text-white/60 transition-colors">
                    {item}
                  </a>
                </li>
              ))}
            </ul>
            <div
              className="p-3 rounded-xl text-[10px] text-white/25 leading-relaxed"
              style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.05)' }}
            >
              <Shield className="w-3 h-3 inline mr-1 text-white/20" />
              Deze informatie is <strong className="text-white/35">geen beleggingsadvies</strong>.
              Form 4 data is openbare SEC informatie. Handel altijd op basis van eigen oordeel en risicobereidheid.
            </div>
          </motion.div>
        </div>

        {/* Bottom bar */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={inView ? { opacity: 1 } : {}}
          transition={{ duration: 0.5, delay: 0.35 }}
          className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-8"
          style={{ borderTop: '1px solid rgba(255,255,255,0.06)' }}
        >
          <div className="flex items-center gap-2">
            <span className="text-[10px] text-white/20">Powered by</span>
            <span
              className="text-[10px] font-bold tracking-wider"
              style={{
                background: 'linear-gradient(135deg, #7C3AED, #00D4FF)',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
                backgroundClip: 'text',
              }}
            >
              AetherLink B.V.
            </span>
            <span className="text-[10px] text-white/15">KvK: 96245255 &bull; &copy; 2026</span>
          </div>
          <div className="text-[10px] text-white/20 italic">
            Alle backtested resultaten zijn hypothetisch. Rendementen uit het verleden bieden geen garantie voor de toekomst.
          </div>
        </motion.div>
      </div>
    </footer>
  )
}

// --- Page root ---

export default function InsiderSignalsPage() {
  return (
    <main className="relative min-h-screen bg-void-900 overflow-x-hidden">
      {/* Persistent ambient background */}
      <div className="fixed inset-0 pointer-events-none" aria-hidden="true" style={{ zIndex: 0 }}>
        <div
          className="absolute -top-1/4 -left-1/4 w-3/4 h-3/4 rounded-full opacity-[0.03]"
          style={{
            background: 'radial-gradient(circle, #7C3AED 0%, transparent 70%)',
            filter: 'blur(80px)',
          }}
        />
        <div
          className="absolute -bottom-1/4 -right-1/4 w-3/4 h-3/4 rounded-full opacity-[0.03]"
          style={{
            background: 'radial-gradient(circle, #00D4FF 0%, transparent 70%)',
            filter: 'blur(100px)',
          }}
        />
      </div>

      <div className="relative z-10">
        <Nav />
        <HeroSection />
        <HowItWorksSection />
        <SignalsSection />
        <BacktestSection />
        <PricingSection />
        <FaqSection />
        <InsiderSignalsFooter />
      </div>
    </main>
  )
}
