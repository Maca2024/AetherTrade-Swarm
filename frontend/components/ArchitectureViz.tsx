'use client'

import { useState, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useInView } from 'react-intersection-observer'
import {
  Database, Zap, Brain, PieChart, Cpu, Shield, RefreshCw, ChevronRight, ChevronDown,
} from 'lucide-react'
import { ARCHITECTURE_LAYERS } from '@/lib/data'
import { cn } from '@/lib/utils'

const ICON_MAP: Record<string, React.ReactNode> = {
  Database: <Database className="w-5 h-5" />,
  Zap: <Zap className="w-5 h-5" />,
  Brain: <Brain className="w-5 h-5" />,
  PieChart: <PieChart className="w-5 h-5" />,
  Cpu: <Cpu className="w-5 h-5" />,
  Shield: <Shield className="w-5 h-5" />,
  RefreshCw: <RefreshCw className="w-5 h-5" />,
}

function DataFlowParticle({ color, delay }: { color: string; delay: number }) {
  return (
    <motion.div
      className="absolute w-1 h-1 rounded-full"
      style={{ background: color, boxShadow: `0 0 4px ${color}`, left: '50%', top: '100%' }}
      animate={{
        top: ['-10%', '110%'],
        opacity: [0, 1, 1, 0],
      }}
      transition={{
        duration: 2.5,
        delay,
        repeat: Infinity,
        ease: 'linear',
      }}
    />
  )
}

function LayerCard({
  layer,
  index,
  total,
  isActive,
  onToggle,
  inView,
}: {
  layer: typeof ARCHITECTURE_LAYERS[0]
  index: number
  total: number
  isActive: boolean
  onToggle: () => void
  inView: boolean
}) {
  const isTop = index === total - 1

  return (
    <motion.div
      initial={{ opacity: 0, x: -30 }}
      animate={inView ? { opacity: 1, x: 0 } : {}}
      transition={{ duration: 0.5, delay: (total - 1 - index) * 0.07, ease: [0.16, 1, 0.3, 1] }}
      className="relative"
    >
      {/* Connecting line above (except last) */}
      {!isTop && (
        <div className="absolute left-[2.25rem] top-0 -translate-y-full h-4 w-px z-0">
          <div
            className="absolute inset-0"
            style={{ background: `linear-gradient(to bottom, ${layer.color}40, ${layer.color}20)` }}
          />
          {/* Animated particle */}
          <div className="relative h-full overflow-visible">
            <DataFlowParticle color={layer.color} delay={index * 0.4} />
          </div>
        </div>
      )}

      <div
        onClick={onToggle}
        className={cn(
          'relative rounded-2xl cursor-pointer transition-all duration-300',
          'flex flex-col overflow-hidden',
        )}
        style={{
          background: isActive
            ? `linear-gradient(135deg, rgba(12,12,22,0.98) 0%, ${layer.color}10 100%)`
            : 'rgba(255,255,255,0.03)',
          border: `1px solid ${isActive ? layer.color + '50' : 'rgba(255,255,255,0.07)'}`,
          boxShadow: isActive ? `0 0 30px ${layer.color}20, 0 8px 40px rgba(0,0,0,0.4)` : undefined,
        }}
      >
        {/* Top highlight */}
        <div
          className="absolute top-0 left-0 right-0 h-px transition-opacity duration-300"
          style={{
            background: `linear-gradient(90deg, transparent, ${layer.color}80, transparent)`,
            opacity: isActive ? 1 : 0,
          }}
        />

        <div className="flex items-center gap-4 p-4">
          {/* Layer number + icon */}
          <div className="flex-shrink-0 flex items-center gap-3">
            <div
              className="w-10 h-10 rounded-xl flex items-center justify-center relative"
              style={{
                background: isActive ? layer.color + '20' : 'rgba(255,255,255,0.05)',
                border: `1px solid ${isActive ? layer.color + '40' : 'rgba(255,255,255,0.08)'}`,
                transition: 'all 0.3s',
              }}
            >
              <div style={{ color: isActive ? layer.color : 'rgba(255,255,255,0.4)' }}>
                {ICON_MAP[layer.icon]}
              </div>
              {/* Pulsing glow on active */}
              {isActive && (
                <div
                  className="absolute inset-0 rounded-xl animate-pulse-slow"
                  style={{ boxShadow: `0 0 15px ${layer.color}60` }}
                />
              )}
            </div>

            {/* Layer number badge */}
            <div
              className="w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-black"
              style={{
                background: layer.color + '20',
                color: layer.color,
                border: `1px solid ${layer.color}30`,
              }}
            >
              {layer.id}
            </div>
          </div>

          {/* Text */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center justify-between">
              <div>
                <h3
                  className="text-sm font-black tracking-wider"
                  style={{ color: isActive ? layer.color : 'white' }}
                >
                  {layer.name}
                </h3>
                <p className="text-xs text-white/30 mt-0.5">{layer.subtitle}</p>
              </div>
              <motion.div
                animate={{ rotate: isActive ? 90 : 0 }}
                transition={{ duration: 0.3 }}
                className="flex-shrink-0 ml-4"
              >
                <ChevronRight
                  className="w-4 h-4"
                  style={{ color: isActive ? layer.color : 'rgba(255,255,255,0.2)' }}
                />
              </motion.div>
            </div>

            {/* Metric pills */}
            <div className="flex items-center gap-2 mt-2 flex-wrap">
              {layer.metrics.map((m) => (
                <span
                  key={m}
                  className="text-[10px] px-2 py-0.5 rounded-full"
                  style={{
                    background: layer.color + '10',
                    color: layer.color + 'CC',
                    border: `1px solid ${layer.color}20`,
                  }}
                >
                  {m}
                </span>
              ))}
            </div>
          </div>
        </div>

        {/* Expanded description */}
        <AnimatePresence>
          {isActive && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.3 }}
              className="overflow-hidden"
            >
              <div
                className="mx-4 mb-4 p-4 rounded-xl text-sm text-white/50 leading-relaxed"
                style={{
                  background: 'rgba(0,0,0,0.3)',
                  border: `1px solid ${layer.color}15`,
                }}
              >
                {layer.description}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </motion.div>
  )
}

export default function ArchitectureViz() {
  const [activeLayer, setActiveLayer] = useState<number | null>(3)
  const [ref, inView] = useInView({ threshold: 0.1, triggerOnce: true })

  // Display layers in reverse order (L7 on top, L1 on bottom)
  const reversedLayers = [...ARCHITECTURE_LAYERS].reverse()

  return (
    <section
      ref={ref}
      className="py-20 px-4 sm:px-6 max-w-7xl mx-auto"
      aria-labelledby="arch-heading"
    >
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={inView ? { opacity: 1, y: 0 } : {}}
        transition={{ duration: 0.6 }}
        className="mb-12 text-center"
      >
        <div className="flex items-center justify-center gap-3 mb-4">
          <div className="h-px w-16 bg-gradient-to-r from-transparent to-[#8B5CF6]/40" />
          <span className="text-xs tracking-widest text-[#8B5CF6] uppercase font-semibold">
            System Architecture
          </span>
          <div className="h-px w-16 bg-gradient-to-l from-transparent to-[#8B5CF6]/40" />
        </div>
        <h2
          id="arch-heading"
          className="text-4xl sm:text-5xl font-black tracking-tight mb-4"
          style={{
            background: 'linear-gradient(135deg, #FFFFFF 0%, #8B5CF6 100%)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            backgroundClip: 'text',
          }}
        >
          7-Layer Neural Stack
        </h2>
        <p className="text-white/40 text-base max-w-xl mx-auto">
          Data flows bottom-to-top through seven specialized processing layers.
          Click any layer to inspect the internals.
        </p>
      </motion.div>

      <div className="grid lg:grid-cols-[1fr,400px] gap-8 items-start">
        {/* Layer stack */}
        <div className="flex flex-col gap-3">
          {reversedLayers.map((layer, i) => (
            <LayerCard
              key={layer.id}
              layer={layer}
              index={i}
              total={reversedLayers.length}
              isActive={activeLayer === layer.id}
              onToggle={() => setActiveLayer(activeLayer === layer.id ? null : layer.id)}
              inView={inView}
            />
          ))}
        </div>

        {/* Right panel: flow visualization */}
        <motion.div
          initial={{ opacity: 0, x: 30 }}
          animate={inView ? { opacity: 1, x: 0 } : {}}
          transition={{ duration: 0.6, delay: 0.4 }}
          className="lg:sticky lg:top-24 rounded-2xl p-6 hidden lg:block"
          style={{
            background: 'rgba(255,255,255,0.02)',
            border: '1px solid rgba(255,255,255,0.07)',
          }}
        >
          <h3 className="text-sm font-bold text-white mb-4 tracking-wider uppercase">
            Data Flow
          </h3>

          {/* Animated flow diagram */}
          <div className="relative">
            <svg
              viewBox="0 0 300 500"
              className="w-full"
              aria-label="Data flow diagram through 7 layers"
            >
              {/* Connecting path */}
              <path
                d="M 150 480 L 150 20"
                stroke="rgba(255,255,255,0.05)"
                strokeWidth="2"
                fill="none"
              />

              {ARCHITECTURE_LAYERS.map((layer, i) => {
                const y = 480 - (i / (ARCHITECTURE_LAYERS.length - 1)) * 460
                const isActive = activeLayer === layer.id

                return (
                  <g key={layer.id}>
                    {/* Connection line segment */}
                    {i < ARCHITECTURE_LAYERS.length - 1 && (
                      <motion.line
                        x1="150" y1={y}
                        x2="150"
                        y2={480 - ((i + 1) / (ARCHITECTURE_LAYERS.length - 1)) * 460}
                        stroke={layer.color}
                        strokeWidth="1.5"
                        strokeDasharray="4 4"
                        initial={{ pathLength: 0 }}
                        animate={inView ? { pathLength: 1 } : {}}
                        transition={{ duration: 0.5, delay: i * 0.15 }}
                        opacity={0.3}
                      />
                    )}

                    {/* Node circle */}
                    <motion.circle
                      cx="150"
                      cy={y}
                      r={isActive ? 14 : 10}
                      fill={layer.color + (isActive ? '30' : '15')}
                      stroke={layer.color}
                      strokeWidth={isActive ? 2 : 1}
                      initial={{ scale: 0 }}
                      animate={inView ? { scale: 1 } : {}}
                      transition={{ duration: 0.4, delay: i * 0.12 }}
                      style={{ filter: isActive ? `drop-shadow(0 0 8px ${layer.color})` : undefined }}
                      onClick={() => setActiveLayer(activeLayer === layer.id ? null : layer.id)}
                      className="cursor-pointer"
                    />

                    {/* Layer label */}
                    <text
                      x={i % 2 === 0 ? 140 : 160}
                      y={y + 1}
                      textAnchor={i % 2 === 0 ? 'end' : 'start'}
                      fill={isActive ? layer.color : 'rgba(255,255,255,0.4)'}
                      fontSize="10"
                      fontWeight={isActive ? 'bold' : 'normal'}
                      fontFamily="Inter, sans-serif"
                    >
                      {layer.name}
                    </text>

                    {/* Layer number inside circle */}
                    <text
                      x="150"
                      y={y + 4}
                      textAnchor="middle"
                      fill={layer.color}
                      fontSize="9"
                      fontWeight="bold"
                      fontFamily="Inter, sans-serif"
                    >
                      {layer.id}
                    </text>

                    {/* Animated particle flowing up */}
                    {i < ARCHITECTURE_LAYERS.length - 1 && (
                      <motion.circle
                        cx="150"
                        cy={y}
                        r="3"
                        fill={layer.color}
                        animate={{
                          cy: [y, 480 - ((i + 1) / (ARCHITECTURE_LAYERS.length - 1)) * 460],
                          opacity: [0, 1, 0],
                        }}
                        transition={{
                          duration: 2,
                          delay: i * 0.5,
                          repeat: Infinity,
                          ease: 'linear',
                        }}
                        style={{ filter: `drop-shadow(0 0 4px ${layer.color})` }}
                      />
                    )}
                  </g>
                )
              })}

              {/* Arrows */}
              <defs>
                <marker id="arrow-up" markerWidth="6" markerHeight="6" refX="3" refY="6" orient="auto">
                  <path d="M0,6 L3,0 L6,6" fill="rgba(0,212,255,0.5)" />
                </marker>
              </defs>
              <line
                x1="150" y1="440"
                x2="150" y2="30"
                stroke="transparent"
                strokeWidth="1"
                markerEnd="url(#arrow-up)"
              />
            </svg>
          </div>

          {/* Active layer detail */}
          <AnimatePresence mode="wait">
            {activeLayer !== null && (
              <motion.div
                key={activeLayer}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                transition={{ duration: 0.3 }}
                className="mt-4 p-4 rounded-xl"
                style={{
                  background: 'rgba(0,0,0,0.3)',
                  border: `1px solid ${ARCHITECTURE_LAYERS.find(l => l.id === activeLayer)?.color}25`,
                }}
              >
                {(() => {
                  const layer = ARCHITECTURE_LAYERS.find(l => l.id === activeLayer)
                  if (!layer) return null
                  return (
                    <>
                      <div
                        className="text-xs font-bold tracking-wider mb-2"
                        style={{ color: layer.color }}
                      >
                        {layer.name}
                      </div>
                      <p className="text-xs text-white/40 leading-relaxed">
                        {layer.description}
                      </p>
                    </>
                  )
                })()}
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>
      </div>
    </section>
  )
}
