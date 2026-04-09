'use client'

import { useState } from 'react'
import { motion } from 'framer-motion'
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
} from 'recharts'
import {
  TrendingUp,
  TrendingDown,
  Briefcase,
  Clock,
  ArrowUpRight,
  ArrowDownRight,
  Filter,
  Download,
} from 'lucide-react'
import { generateEquityCurve } from '@/lib/data'
import { usePerformance } from '@/lib/hooks'
import { cn } from '@/lib/utils'

// --- Mock data matching Supabase schema ---
interface Position {
  id: string
  ticker: string
  underlying: string
  side: 'LONG' | 'SHORT'
  quantity: number
  entry_price: number
  current_price: number
  market_value: number
  unrealized_pnl: number
  unrealized_pnl_pct: number
  pod: string
  opened_at: string
  color: string
}

const MOCK_POSITIONS: Position[] = [
  {
    id: 'pos-001',
    ticker: 'SPY',
    underlying: 'S&P 500 ETF',
    side: 'LONG',
    quantity: 12,
    entry_price: 521.40,
    current_price: 528.73,
    market_value: 6344.76,
    unrealized_pnl: 87.96,
    unrealized_pnl_pct: 1.41,
    pod: 'Momentum Alpha',
    opened_at: '2026-04-03T09:31:00Z',
    color: '#00D4FF',
  },
  {
    id: 'pos-002',
    ticker: 'QQQ',
    underlying: 'Nasdaq-100 ETF',
    side: 'LONG',
    quantity: 8,
    entry_price: 443.20,
    current_price: 447.85,
    market_value: 3582.80,
    unrealized_pnl: 37.20,
    unrealized_pnl_pct: 1.05,
    pod: 'AI / ML Alpha',
    opened_at: '2026-04-04T10:15:00Z',
    color: '#06B6D4',
  },
  {
    id: 'pos-003',
    ticker: 'GLD',
    underlying: 'Gold ETF',
    side: 'SHORT',
    quantity: 10,
    entry_price: 218.60,
    current_price: 215.40,
    market_value: 2154.00,
    unrealized_pnl: 32.00,
    unrealized_pnl_pct: 1.46,
    pod: 'Global Macro',
    opened_at: '2026-04-05T14:22:00Z',
    color: '#FFB800',
  },
  {
    id: 'pos-004',
    ticker: 'TLT',
    underlying: '20Y Treasury ETF',
    side: 'LONG',
    quantity: 25,
    entry_price: 87.30,
    current_price: 88.14,
    market_value: 2203.50,
    unrealized_pnl: 21.00,
    unrealized_pnl_pct: 0.96,
    pod: 'Multi-Factor',
    opened_at: '2026-04-06T09:45:00Z',
    color: '#A78BFA',
  },
  {
    id: 'pos-005',
    ticker: 'VXX',
    underlying: 'VIX Short-Term',
    side: 'SHORT',
    quantity: 30,
    entry_price: 14.82,
    current_price: 15.30,
    market_value: 459.00,
    unrealized_pnl: -14.40,
    unrealized_pnl_pct: -3.24,
    pod: 'Options / Vol',
    opened_at: '2026-04-07T11:30:00Z',
    color: '#FF3366',
  },
]

interface TradeRecord {
  id: string
  ticker: string
  side: 'LONG' | 'SHORT'
  quantity: number
  entry_price: number
  exit_price: number
  pnl: number
  pnl_pct: number
  duration: string
  pod: string
  closed_at: string
  color: string
}

const MOCK_TRADE_HISTORY: TradeRecord[] = [
  {
    id: 'trade-001',
    ticker: 'AAPL',
    side: 'LONG',
    quantity: 15,
    entry_price: 212.40,
    exit_price: 218.90,
    pnl: 97.50,
    pnl_pct: 3.06,
    duration: '3d 4h',
    pod: 'Momentum Alpha',
    closed_at: '2026-04-07T15:45:00Z',
    color: '#00D4FF',
  },
  {
    id: 'trade-002',
    ticker: 'MSFT',
    side: 'LONG',
    quantity: 8,
    entry_price: 408.20,
    exit_price: 415.60,
    pnl: 59.20,
    pnl_pct: 1.81,
    duration: '1d 6h',
    pod: 'AI / ML Alpha',
    closed_at: '2026-04-06T14:20:00Z',
    color: '#06B6D4',
  },
  {
    id: 'trade-003',
    ticker: 'IWM',
    side: 'SHORT',
    quantity: 20,
    entry_price: 214.80,
    exit_price: 211.30,
    pnl: 70.00,
    pnl_pct: 1.63,
    duration: '2d 1h',
    pod: 'Global Macro',
    closed_at: '2026-04-05T10:30:00Z',
    color: '#FFB800',
  },
  {
    id: 'trade-004',
    ticker: 'NVDA',
    side: 'LONG',
    quantity: 5,
    entry_price: 862.40,
    exit_price: 851.20,
    pnl: -56.00,
    pnl_pct: -1.30,
    duration: '18h',
    pod: 'Behavioral Alpha',
    closed_at: '2026-04-04T16:00:00Z',
    color: '#F97316',
  },
  {
    id: 'trade-005',
    ticker: 'GS',
    side: 'LONG',
    quantity: 6,
    entry_price: 478.30,
    exit_price: 492.10,
    pnl: 82.80,
    pnl_pct: 2.88,
    duration: '4d 2h',
    pod: 'Multi-Factor',
    closed_at: '2026-04-03T13:15:00Z',
    color: '#A78BFA',
  },
]

// Pre-generate equity data (subset for speed)
const equityData = generateEquityCurve(365).filter((_, i) => i % 5 === 0)

function EquityCurveChart() {
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
      <div className="flex items-center justify-between mb-5">
        <div>
          <h3 className="text-sm font-bold text-white">Equity Curve</h3>
          <p className="text-[11px] text-white/30 mt-0.5">365-day NAV vs benchmarks</p>
        </div>
        <div className="flex items-center gap-3 text-[11px]">
          <div className="flex items-center gap-1.5">
            <div className="w-3 h-0.5 rounded-full bg-[#00D4FF]" />
            <span className="text-white/40">ATS</span>
          </div>
          <div className="flex items-center gap-1.5">
            <div className="w-3 h-0.5 rounded-full bg-[#FFB800]" />
            <span className="text-white/40">S&P 500</span>
          </div>
        </div>
      </div>

      <div className="h-52">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={equityData} margin={{ top: 5, right: 5, bottom: 5, left: 10 }}>
            <defs>
              <linearGradient id="portfolioGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#00D4FF" stopOpacity={0.25} />
                <stop offset="100%" stopColor="#00D4FF" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="spGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#FFB800" stopOpacity={0.12} />
                <stop offset="100%" stopColor="#FFB800" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" vertical={false} />
            <XAxis
              dataKey="date"
              tick={{ fill: 'rgba(255,255,255,0.25)', fontSize: 9 }}
              tickLine={false}
              axisLine={false}
              interval={Math.floor(equityData.length / 5)}
            />
            <YAxis
              tick={{ fill: 'rgba(255,255,255,0.25)', fontSize: 9 }}
              tickLine={false}
              axisLine={false}
              tickFormatter={(v) => `$${(v / 1000).toFixed(1)}k`}
            />
            <Tooltip
              contentStyle={{
                background: 'rgba(7,7,15,0.95)',
                border: '1px solid rgba(0,212,255,0.2)',
                borderRadius: '12px',
                fontSize: '11px',
                color: 'rgba(255,255,255,0.7)',
              }}
              formatter={(value: number, name: string) => [`$${value.toFixed(0)}`, name === 'oracle' ? 'ATS' : 'S&P 500']}
              labelStyle={{ color: 'rgba(255,255,255,0.4)', marginBottom: '4px' }}
            />
            <ReferenceLine y={10000} stroke="rgba(255,255,255,0.08)" strokeDasharray="4 4" />
            <Area type="monotone" dataKey="sp500" name="S&P 500" stroke="#FFB800" strokeWidth={1.5} fill="url(#spGrad)" dot={false} />
            <Area type="monotone" dataKey="oracle" name="ATS" stroke="#00D4FF" strokeWidth={2} fill="url(#portfolioGrad)" dot={false} style={{ filter: 'drop-shadow(0 0 4px rgba(0,212,255,0.4))' }} />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      <div className="mt-4 pt-3 border-t border-white/5 grid grid-cols-3 gap-4">
        {[
          { label: 'Total Return', value: '+187.4%', color: '#00D4FF' },
          { label: 'vs S&P 500', value: '+89.2%', color: '#00FF94' },
          { label: 'Max Drawdown', value: '-8.3%', color: '#FFB800' },
        ].map((stat) => (
          <div key={stat.label} className="text-center">
            <div className="text-base font-black" style={{ color: stat.color }}>{stat.value}</div>
            <div className="text-[10px] text-white/30 mt-0.5">{stat.label}</div>
          </div>
        ))}
      </div>
    </motion.div>
  )
}

function PortfolioSummary({ perf }: { perf: ReturnType<typeof usePerformance>['data'] }) {
  const totalValue = 28740
  const totalPnl = 163.20
  const totalPnlPct = 1.84
  const openPositions = MOCK_POSITIONS.length

  const stats = [
    { label: 'Portfolio Value', value: `$${totalValue.toLocaleString('en-US')}`, color: '#00D4FF' },
    { label: 'Unrealized P&L', value: `+$${totalPnl.toFixed(2)}`, color: '#00FF94' },
    { label: 'P&L %', value: `+${totalPnlPct.toFixed(2)}%`, color: '#00FF94' },
    { label: 'Open Positions', value: `${openPositions}`, color: '#7C3AED' },
  ]

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      {stats.map((stat, i) => (
        <motion.div
          key={stat.label}
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: i * 0.07 }}
          className="rounded-2xl p-4"
          style={{
            background: 'rgba(255,255,255,0.03)',
            border: '1px solid rgba(255,255,255,0.07)',
          }}
        >
          <div className="text-xl font-black mb-0.5" style={{ color: stat.color }}>
            {stat.value}
          </div>
          <div className="text-[11px] text-white/40">{stat.label}</div>
        </motion.div>
      ))}
    </div>
  )
}

function PositionsTable() {
  const [sortKey, setSortKey] = useState<'unrealized_pnl' | 'market_value' | 'unrealized_pnl_pct'>('unrealized_pnl_pct')

  const sorted = [...MOCK_POSITIONS].sort((a, b) => b[sortKey] - a[sortKey])

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: 0.15 }}
      className="rounded-2xl overflow-hidden"
      style={{
        background: 'rgba(255,255,255,0.02)',
        border: '1px solid rgba(255,255,255,0.07)',
      }}
    >
      <div className="flex items-center justify-between px-5 py-4 border-b border-white/5">
        <div className="flex items-center gap-2">
          <Briefcase className="w-4 h-4 text-white/40" />
          <h3 className="text-sm font-bold text-white">Open Positions</h3>
          <span className="text-[11px] text-white/30 bg-white/5 px-2 py-0.5 rounded-full ml-1">
            {MOCK_POSITIONS.length} active
          </span>
        </div>
        <div className="flex items-center gap-2">
          <button
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-[11px] text-white/40 hover:text-white bg-white/5 hover:bg-white/10 transition-all border border-white/5"
            aria-label="Filter positions"
          >
            <Filter className="w-3 h-3" />
            Filter
          </button>
        </div>
      </div>

      {/* Table header */}
      <div className="grid grid-cols-6 px-5 py-2.5 border-b border-white/5 text-[10px] uppercase tracking-widest text-white/20">
        <span className="col-span-2">Instrument</span>
        <span className="text-right">Qty</span>
        <span className="text-right">Entry / Current</span>
        <button
          onClick={() => setSortKey('market_value')}
          className={cn('text-right transition-colors', sortKey === 'market_value' ? 'text-[#7C3AED]' : 'hover:text-white/40')}
        >
          Market Value
        </button>
        <button
          onClick={() => setSortKey('unrealized_pnl_pct')}
          className={cn('text-right transition-colors', sortKey === 'unrealized_pnl_pct' ? 'text-[#7C3AED]' : 'hover:text-white/40')}
        >
          Unr. P&L
        </button>
      </div>

      <div className="divide-y divide-white/5">
        {sorted.map((pos, i) => {
          const isProfit = pos.unrealized_pnl >= 0
          return (
            <motion.div
              key={pos.id}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.2 + i * 0.05 }}
              className="grid grid-cols-6 px-5 py-3.5 items-center text-xs hover:bg-white/[0.02] transition-colors"
            >
              {/* Instrument */}
              <div className="col-span-2 flex items-center gap-2.5 min-w-0">
                <div
                  className="w-1.5 h-6 rounded-full flex-shrink-0"
                  style={{ background: pos.color }}
                />
                <div className="min-w-0">
                  <div className="font-bold text-white">{pos.ticker}</div>
                  <div className="text-[10px] text-white/30 truncate">{pos.underlying}</div>
                </div>
                <span
                  className={cn(
                    'flex-shrink-0 text-[10px] font-bold px-1.5 py-0.5 rounded',
                    pos.side === 'LONG'
                      ? 'text-[#00FF94] bg-[#00FF94]/10'
                      : 'text-[#FF3366] bg-[#FF3366]/10'
                  )}
                >
                  {pos.side}
                </span>
              </div>

              {/* Quantity */}
              <span className="text-right text-white/50 tabular-nums">{pos.quantity}</span>

              {/* Entry / Current */}
              <div className="text-right">
                <div className="tabular-nums text-white/60">${pos.current_price.toFixed(2)}</div>
                <div className="tabular-nums text-white/30 text-[10px]">
                  ${pos.entry_price.toFixed(2)}
                </div>
              </div>

              {/* Market value */}
              <span className="text-right text-white/60 tabular-nums font-medium">
                ${pos.market_value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </span>

              {/* P&L */}
              <div className="text-right">
                <div
                  className="flex items-center justify-end gap-0.5 font-black tabular-nums"
                  style={{ color: isProfit ? '#00FF94' : '#FF3366' }}
                >
                  {isProfit ? <ArrowUpRight className="w-3 h-3" /> : <ArrowDownRight className="w-3 h-3" />}
                  {isProfit ? '+' : ''}{pos.unrealized_pnl_pct.toFixed(2)}%
                </div>
                <div
                  className="text-[10px] tabular-nums"
                  style={{ color: isProfit ? 'rgba(0,255,148,0.5)' : 'rgba(255,51,102,0.5)' }}
                >
                  {isProfit ? '+' : ''}${pos.unrealized_pnl.toFixed(2)}
                </div>
              </div>
            </motion.div>
          )
        })}
      </div>

      {/* Footer */}
      <div
        className="flex items-center justify-between px-5 py-3 text-xs border-t border-white/5"
        style={{ background: 'rgba(255,255,255,0.01)' }}
      >
        <span className="text-white/30">Total market exposure</span>
        <span className="font-bold text-white">
          ${MOCK_POSITIONS.reduce((s, p) => s + p.market_value, 0).toLocaleString('en-US', { minimumFractionDigits: 2 })}
        </span>
      </div>
    </motion.div>
  )
}

function TradeHistoryTable() {
  const [filter, setFilter] = useState<'all' | 'win' | 'loss'>('all')

  const filtered = MOCK_TRADE_HISTORY.filter((t) => {
    if (filter === 'win') return t.pnl > 0
    if (filter === 'loss') return t.pnl < 0
    return true
  })

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
      <div className="flex items-center justify-between px-5 py-4 border-b border-white/5 flex-wrap gap-3">
        <div className="flex items-center gap-2">
          <Clock className="w-4 h-4 text-white/40" />
          <h3 className="text-sm font-bold text-white">Trade History</h3>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex bg-white/5 rounded-xl p-1 gap-0.5">
            {(['all', 'win', 'loss'] as const).map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={cn(
                  'px-3 py-1 rounded-lg text-[11px] font-medium transition-all capitalize',
                  filter === f ? 'bg-white/10 text-white' : 'text-white/30 hover:text-white/60'
                )}
              >
                {f === 'all' ? 'All' : f === 'win' ? 'Winners' : 'Losers'}
              </button>
            ))}
          </div>
          <button
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-[11px] text-white/40 hover:text-white bg-white/5 hover:bg-white/10 transition-all border border-white/5"
            aria-label="Export trade history"
          >
            <Download className="w-3 h-3" />
            Export
          </button>
        </div>
      </div>

      {/* Headers */}
      <div className="grid grid-cols-6 px-5 py-2.5 border-b border-white/5 text-[10px] uppercase tracking-widest text-white/20">
        <span>Ticker</span>
        <span className="text-center">Side</span>
        <span className="text-right">Entry / Exit</span>
        <span className="text-right hidden sm:block">Pod</span>
        <span className="text-right">Duration</span>
        <span className="text-right">P&L</span>
      </div>

      <div className="divide-y divide-white/5">
        {filtered.map((trade, i) => {
          const isProfit = trade.pnl > 0
          return (
            <motion.div
              key={trade.id}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.25 + i * 0.05 }}
              className="grid grid-cols-6 px-5 py-3 items-center text-xs hover:bg-white/[0.02] transition-colors"
            >
              {/* Ticker */}
              <div className="flex items-center gap-2">
                <div className="w-1.5 h-1.5 rounded-full" style={{ background: trade.color }} />
                <span className="font-bold text-white">{trade.ticker}</span>
              </div>

              {/* Side */}
              <div className="text-center">
                <span
                  className={cn(
                    'text-[10px] font-bold px-1.5 py-0.5 rounded',
                    trade.side === 'LONG'
                      ? 'text-[#00FF94] bg-[#00FF94]/10'
                      : 'text-[#FF3366] bg-[#FF3366]/10'
                  )}
                >
                  {trade.side}
                </span>
              </div>

              {/* Entry / Exit */}
              <div className="text-right">
                <div className="text-white/60 tabular-nums">${trade.exit_price.toFixed(2)}</div>
                <div className="text-white/30 text-[10px] tabular-nums">${trade.entry_price.toFixed(2)}</div>
              </div>

              {/* Pod */}
              <span className="text-right text-white/30 truncate hidden sm:block text-[10px]">
                {trade.pod}
              </span>

              {/* Duration */}
              <div className="flex items-center justify-end gap-1 text-white/40">
                <Clock className="w-3 h-3 flex-shrink-0" />
                {trade.duration}
              </div>

              {/* P&L */}
              <div className="text-right">
                <div
                  className="font-black tabular-nums"
                  style={{ color: isProfit ? '#00FF94' : '#FF3366' }}
                >
                  {isProfit ? '+' : ''}${Math.abs(trade.pnl).toFixed(2)}
                </div>
                <div
                  className="text-[10px] tabular-nums"
                  style={{ color: isProfit ? 'rgba(0,255,148,0.5)' : 'rgba(255,51,102,0.5)' }}
                >
                  {isProfit ? '+' : ''}{trade.pnl_pct.toFixed(2)}%
                </div>
              </div>
            </motion.div>
          )
        })}
      </div>

      {/* Summary footer */}
      <div
        className="grid grid-cols-3 gap-4 px-5 py-3 border-t border-white/5 text-xs"
        style={{ background: 'rgba(255,255,255,0.01)' }}
      >
        <div>
          <div className="text-white/30">Total trades</div>
          <div className="font-bold text-white">{MOCK_TRADE_HISTORY.length}</div>
        </div>
        <div>
          <div className="text-white/30">Win rate</div>
          <div className="font-bold text-[#00FF94]">
            {Math.round(MOCK_TRADE_HISTORY.filter((t) => t.pnl > 0).length / MOCK_TRADE_HISTORY.length * 100)}%
          </div>
        </div>
        <div>
          <div className="text-white/30">Net P&L</div>
          <div className="font-bold text-[#00FF94]">
            +${MOCK_TRADE_HISTORY.reduce((s, t) => s + t.pnl, 0).toFixed(2)}
          </div>
        </div>
      </div>
    </motion.div>
  )
}

export default function PortfolioPage() {
  const { data: perf } = usePerformance()

  return (
    <div className="p-4 sm:p-6 space-y-6">
      {/* Page header */}
      <div>
        <h1 className="text-xl font-black text-white tracking-tight">Portfolio</h1>
        <p className="text-xs text-white/30 mt-0.5">
          Paper trading — Supabase-backed position tracking
        </p>
      </div>

      {/* Summary stats */}
      <PortfolioSummary perf={perf} />

      {/* Equity curve */}
      <EquityCurveChart />

      {/* Positions table */}
      <PositionsTable />

      {/* Trade history */}
      <TradeHistoryTable />
    </div>
  )
}
