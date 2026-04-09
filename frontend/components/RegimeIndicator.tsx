'use client'

import { useState, useEffect, useMemo } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Activity, TrendingDown, TrendingUp, Minus, AlertTriangle, Wifi, WifiOff } from 'lucide-react'
import { REGIMES, type RegimeState, type Regime } from '@/lib/data'
import { useRegime, useApiStatus } from '@/lib/hooks'
import { cn } from '@/lib/utils'

const REGIME_ICONS = {
  bull: TrendingUp,
  bear: TrendingDown,
  crisis: AlertTriangle,
  range: Minus,
}

function ConfidenceBar({ value, color }: { value: number; color: string }) {
  return (
    <div className="flex items-center gap-2">
      <div className="w-24 h-1.5 rounded-full bg-white/10 overflow-hidden">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${value}%` }}
          transition={{ duration: 1, ease: 'easeOut' }}
          className="h-full rounded-full"
          style={{ background: color, boxShadow: `0 0 8px ${color}` }}
        />
      </div>
      <span className="text-xs tabular-nums" style={{ color }}>
        {value}%
      </span>
    </div>
  )
}

const REGIME_STYLE_MAP: Record<string, { color: string; bgColor: string; label: string; description: string }> = {
  bull: { color: '#00FF94', bgColor: 'rgba(0, 255, 148, 0.08)', label: 'BULL MARKET', description: 'Risk-on momentum regime detected. Trend-following strategies overweight.' },
  bear: { color: '#FF3366', bgColor: 'rgba(255, 51, 102, 0.08)', label: 'BEAR MARKET', description: 'Defensive posture active. Short bias, mean-reversion and volatility pods elevated.' },
  crisis: { color: '#FFB800', bgColor: 'rgba(255, 184, 0, 0.08)', label: 'CRISIS MODE', description: 'Tail-risk event detected. Kill switches active. Capital preservation priority.' },
  range: { color: '#00D4FF', bgColor: 'rgba(0, 212, 255, 0.08)', label: 'RANGE-BOUND', description: 'Low directional bias. Mean-reversion and stat-arb strategies optimal.' },
}

export default function RegimeIndicator() {
  const { data: apiRegime } = useRegime()
  const { isConnected } = useApiStatus()

  const [cycleIndex, setCycleIndex] = useState(0)
  const [isTransitioning, setIsTransitioning] = useState(false)

  // Build live regime from API data if available
  const liveRegime: RegimeState | null = useMemo(() => {
    if (!apiRegime) return null
    const style = REGIME_STYLE_MAP[apiRegime.regime] ?? REGIME_STYLE_MAP.range
    return {
      type: apiRegime.regime as Regime,
      label: style.label,
      confidence: Math.round(apiRegime.confidence * 100),
      color: style.color,
      bgColor: style.bgColor,
      description: style.description,
    }
  }, [apiRegime])

  // Only cycle through demo regimes when API is NOT connected
  useEffect(() => {
    if (liveRegime) return // Don't cycle if we have live data
    const interval = setInterval(() => {
      setIsTransitioning(true)
      setTimeout(() => {
        setCycleIndex(prev => (prev + 1) % REGIMES.length)
        setIsTransitioning(false)
      }, 300)
    }, 12000)
    return () => clearInterval(interval)
  }, [liveRegime])

  const activeRegime = liveRegime ?? REGIMES[cycleIndex]

  const Icon = REGIME_ICONS[activeRegime.type]

  return (
    <div
      id="regime-indicator"
      className="sticky top-0 z-50 border-b border-white/5"
      style={{
        background: 'rgba(4, 4, 10, 0.85)',
        backdropFilter: 'blur(24px)',
        WebkitBackdropFilter: 'blur(24px)',
      }}
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6">
        <div className="flex items-center justify-between h-14 gap-4 flex-wrap">
          {/* Left: Regime status */}
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2">
              <div
                className="w-2 h-2 rounded-full"
                style={{
                  background: activeRegime.color,
                  boxShadow: `0 0 8px ${activeRegime.color}`,
                  animation: activeRegime.type === 'crisis' ? 'pulseDot 1s ease-out infinite' : 'none',
                }}
              />
              <span className="text-xs text-white/40 uppercase tracking-widest hidden sm:inline">
                Market Regime
              </span>
            </div>

            <div className="w-px h-4 bg-white/10" />

            <AnimatePresence mode="wait">
              <motion.div
                key={activeRegime.type}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 10 }}
                transition={{ duration: 0.3 }}
                className="flex items-center gap-2"
              >
                <Icon
                  className="w-4 h-4"
                  style={{ color: activeRegime.color }}
                />
                <span
                  className="text-sm font-bold tracking-wider"
                  style={{
                    color: activeRegime.color,
                    textShadow: `0 0 10px ${activeRegime.color}40`,
                  }}
                >
                  {activeRegime.label}
                </span>
              </motion.div>
            </AnimatePresence>
          </div>

          {/* Center: confidence */}
          <AnimatePresence mode="wait">
            <motion.div
              key={`conf-${activeRegime.type}`}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="hidden md:flex items-center gap-3"
            >
              <span className="text-xs text-white/40 uppercase tracking-widest">
                Confidence
              </span>
              <ConfidenceBar value={activeRegime.confidence} color={activeRegime.color} />
            </motion.div>
          </AnimatePresence>

          {/* Right: description + regime switcher */}
          <div className="flex items-center gap-4">
            <AnimatePresence mode="wait">
              <motion.p
                key={`desc-${activeRegime.type}`}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="hidden lg:block text-xs text-white/40 max-w-xs truncate"
              >
                {activeRegime.description}
              </motion.p>
            </AnimatePresence>

            {/* Regime selector pills */}
            <div className="flex items-center gap-1">
              {REGIMES.map((regime, i) => (
                <button
                  key={regime.type}
                  onClick={() => {
                    setIsTransitioning(true)
                    setTimeout(() => {
                      setCycleIndex(i)
                      setIsTransitioning(false)
                    }, 200)
                  }}
                  className={cn(
                    'w-6 h-6 rounded-md transition-all duration-200 flex items-center justify-center',
                    'text-xs font-bold',
                    i === cycleIndex
                      ? 'text-black scale-110'
                      : 'bg-white/5 text-white/30 hover:bg-white/10 hover:text-white/60'
                  )}
                  style={i === cycleIndex ? {
                    background: regime.color,
                    boxShadow: `0 0 10px ${regime.color}60`,
                  } : {}}
                  title={regime.label}
                  aria-label={`Switch to ${regime.label}`}
                  aria-pressed={i === cycleIndex}
                >
                  {regime.type.slice(0, 1).toUpperCase()}
                </button>
              ))}
            </div>

            {/* Live/Demo indicator */}
            <div className={cn(
              'flex items-center gap-1.5 px-2 py-1 rounded-md',
              isConnected ? 'bg-white/5' : 'bg-white/3'
            )}>
              {isConnected ? (
                <>
                  <Wifi className="w-3 h-3 text-[#00FF94]" />
                  <span className="text-xs text-[#00FF94] font-medium">LIVE</span>
                </>
              ) : (
                <>
                  <WifiOff className="w-3 h-3 text-white/30" />
                  <span className="text-xs text-white/30 font-medium">DEMO</span>
                </>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Colored bottom line */}
      <motion.div
        key={`line-${activeRegime.type}`}
        initial={{ scaleX: 0 }}
        animate={{ scaleX: 1 }}
        transition={{ duration: 0.8, ease: 'easeOut' }}
        className="absolute bottom-0 left-0 right-0 h-px origin-left"
        style={{ background: `linear-gradient(90deg, ${activeRegime.color}, transparent 80%)` }}
      />
    </div>
  )
}
