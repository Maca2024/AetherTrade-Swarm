'use client'

import { useEffect, useRef, useState, useCallback } from 'react'
import { motion, useAnimation, AnimatePresence } from 'framer-motion'
import { ChevronDown } from 'lucide-react'
import { cn } from '@/lib/utils'

interface Particle {
  x: number
  y: number
  vx: number
  vy: number
  size: number
  opacity: number
  color: string
  life: number
  maxLife: number
}

function ParticleCanvas() {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const particlesRef = useRef<Particle[]>([])
  const animFrameRef = useRef<number>(0)

  const COLORS = ['#00D4FF', '#8B5CF6', '#00FF94', '#FFB800', '#FF3366']

  const createParticle = useCallback((width: number, height: number): Particle => {
    const life = 200 + Math.random() * 300
    return {
      x: Math.random() * width,
      y: Math.random() * height,
      vx: (Math.random() - 0.5) * 0.4,
      vy: (Math.random() - 0.5) * 0.4,
      size: Math.random() * 2 + 0.5,
      opacity: Math.random() * 0.6 + 0.2,
      color: COLORS[Math.floor(Math.random() * COLORS.length)],
      life,
      maxLife: life,
    }
  }, [])

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const resize = () => {
      canvas.width = canvas.offsetWidth
      canvas.height = canvas.offsetHeight
    }
    resize()
    window.addEventListener('resize', resize)

    // Init particles
    for (let i = 0; i < 120; i++) {
      particlesRef.current.push(createParticle(canvas.width, canvas.height))
    }

    const draw = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height)

      // Draw connections
      const particles = particlesRef.current
      for (let i = 0; i < particles.length; i++) {
        for (let j = i + 1; j < particles.length; j++) {
          const dx = particles[i].x - particles[j].x
          const dy = particles[i].y - particles[j].y
          const dist = Math.sqrt(dx * dx + dy * dy)
          if (dist < 100) {
            ctx.beginPath()
            ctx.strokeStyle = `rgba(0, 212, 255, ${0.06 * (1 - dist / 100)})`
            ctx.lineWidth = 0.5
            ctx.moveTo(particles[i].x, particles[i].y)
            ctx.lineTo(particles[j].x, particles[j].y)
            ctx.stroke()
          }
        }
      }

      // Update and draw particles
      particlesRef.current = particles.map(p => {
        p.x += p.vx
        p.y += p.vy
        p.life--

        if (p.life <= 0 || p.x < 0 || p.x > canvas.width || p.y < 0 || p.y > canvas.height) {
          return createParticle(canvas.width, canvas.height)
        }

        const lifeRatio = p.life / p.maxLife
        ctx.beginPath()
        ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2)
        ctx.fillStyle = p.color.replace(')', `, ${p.opacity * lifeRatio})`)
          .replace('rgb', 'rgba').replace('#', 'rgba(')

        // Handle hex colors
        const hex = p.color.replace('#', '')
        const r = parseInt(hex.slice(0, 2), 16)
        const g = parseInt(hex.slice(2, 4), 16)
        const b = parseInt(hex.slice(4, 6), 16)
        ctx.fillStyle = `rgba(${r}, ${g}, ${b}, ${p.opacity * lifeRatio})`
        ctx.fill()

        // Glow
        ctx.shadowBlur = 6
        ctx.shadowColor = p.color
        ctx.fill()
        ctx.shadowBlur = 0

        return p
      })

      animFrameRef.current = requestAnimationFrame(draw)
    }

    animFrameRef.current = requestAnimationFrame(draw)

    return () => {
      window.removeEventListener('resize', resize)
      cancelAnimationFrame(animFrameRef.current)
    }
  }, [createParticle])

  return (
    <canvas
      ref={canvasRef}
      className="absolute inset-0 w-full h-full opacity-70"
      aria-hidden="true"
    />
  )
}

function AnimatedCounter({ target, duration = 2000 }: { target: number; duration?: number }) {
  const [value, setValue] = useState(0)
  const [started, setStarted] = useState(false)

  useEffect(() => {
    const timer = setTimeout(() => setStarted(true), 800)
    return () => clearTimeout(timer)
  }, [])

  useEffect(() => {
    if (!started) return
    const startTime = Date.now()
    const animate = () => {
      const elapsed = Date.now() - startTime
      const progress = Math.min(elapsed / duration, 1)
      // Ease out cubic
      const eased = 1 - Math.pow(1 - progress, 3)
      setValue(parseFloat((eased * target).toFixed(2)))
      if (progress < 1) requestAnimationFrame(animate)
    }
    requestAnimationFrame(animate)
  }, [started, target, duration])

  return <span>{value.toFixed(2)}</span>
}

export default function HeroSection() {
  const [titleVisible, setTitleVisible] = useState(false)
  const [glitchActive, setGlitchActive] = useState(false)

  useEffect(() => {
    const t1 = setTimeout(() => setTitleVisible(true), 200)
    const t2 = setTimeout(() => {
      setGlitchActive(true)
      setTimeout(() => setGlitchActive(false), 600)
    }, 1200)
    return () => { clearTimeout(t1); clearTimeout(t2) }
  }, [])

  const scrollToContent = () => {
    document.getElementById('regime-indicator')?.scrollIntoView({ behavior: 'smooth' })
  }

  return (
    <section
      className="relative min-h-screen flex flex-col items-center justify-center overflow-hidden"
      aria-labelledby="hero-title"
    >
      {/* Animated background layers */}
      <div className="absolute inset-0 bg-void-900" />

      {/* Radial glow orbs */}
      <div className="absolute inset-0 overflow-hidden" aria-hidden="true">
        <div
          className="absolute top-1/4 left-1/4 w-[600px] h-[600px] rounded-full opacity-10"
          style={{
            background: 'radial-gradient(circle, #00D4FF 0%, transparent 70%)',
            filter: 'blur(60px)',
            animation: 'float 8s ease-in-out infinite',
          }}
        />
        <div
          className="absolute bottom-1/4 right-1/4 w-[500px] h-[500px] rounded-full opacity-8"
          style={{
            background: 'radial-gradient(circle, #8B5CF6 0%, transparent 70%)',
            filter: 'blur(80px)',
            animation: 'float 10s ease-in-out infinite reverse',
          }}
        />
        <div
          className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] rounded-full opacity-5"
          style={{
            background: 'radial-gradient(circle, #FF3366 0%, transparent 70%)',
            filter: 'blur(100px)',
            animation: 'float 12s ease-in-out infinite 2s',
          }}
        />
      </div>

      {/* Grid */}
      <div className="absolute inset-0 grid-bg opacity-60" aria-hidden="true" />

      {/* Particle canvas */}
      <ParticleCanvas />

      {/* Scanline overlay */}
      <div className="absolute inset-0 scanlines pointer-events-none" aria-hidden="true" />

      {/* Content */}
      <div className="relative z-10 flex flex-col items-center text-center px-4 max-w-5xl mx-auto">
        {/* Status badge */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2, duration: 0.6 }}
          className="flex items-center gap-2 mb-8 px-4 py-2 rounded-full glass border border-neon-blue/20"
        >
          <span className="pulse-dot w-2 h-2 rounded-full bg-[#00FF94] text-[#00FF94]" />
          <span className="text-xs font-medium text-[#00FF94] tracking-widest uppercase">
            Live Trading — All Systems Operational
          </span>
        </motion.div>

        {/* Main title */}
        <AnimatePresence>
          {titleVisible && (
            <motion.div
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
              className="relative mb-4"
            >
              <h1
                id="hero-title"
                className={cn(
                  'text-[clamp(4rem,12vw,10rem)] font-black tracking-tighter leading-none select-none',
                  'hero-glow',
                  glitchActive && 'glitch-text'
                )}
                data-text="AETHERTRADE-SWARM"
                style={{
                  background: 'linear-gradient(135deg, #FFFFFF 0%, #00D4FF 40%, #8B5CF6 70%, #FFFFFF 100%)',
                  WebkitBackgroundClip: 'text',
                  WebkitTextFillColor: 'transparent',
                  backgroundClip: 'text',
                }}
              >
                AETHERTRADE-SWARM
              </h1>

              {/* Decorative lines */}
              <div className="absolute -left-8 top-1/2 w-6 h-px bg-[#00D4FF] opacity-60" />
              <div className="absolute -right-8 top-1/2 w-6 h-px bg-[#00D4FF] opacity-60" />
            </motion.div>
          )}
        </AnimatePresence>

        {/* Subtitle */}
        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.7, duration: 0.7 }}
          className="text-[clamp(0.9rem,2vw,1.25rem)] text-white/50 font-light tracking-[0.2em] uppercase mb-3"
        >
          9 Strategy Pods &nbsp;•&nbsp; 4 Regimes &nbsp;•&nbsp; 1 Unified Intelligence
        </motion.p>

        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.9, duration: 0.7 }}
          className="text-[clamp(0.8rem,1.5vw,1rem)] text-white/30 font-light tracking-widest mb-12"
        >
          AI-Driven Multi-Strategy Quantitative Trading Platform
        </motion.p>

        {/* Sharpe counter */}
        <motion.div
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 1.1, duration: 0.6 }}
          className="flex items-center gap-8 mb-12"
        >
          <div className="text-center">
            <div
              className="text-[clamp(2.5rem,6vw,4rem)] font-black tabular-nums"
              style={{
                color: '#00D4FF',
                textShadow: '0 0 30px rgba(0,212,255,0.4), 0 0 60px rgba(0,212,255,0.1)',
              }}
            >
              <AnimatedCounter target={1.87} duration={2400} />
            </div>
            <div className="text-xs tracking-widest text-white/40 uppercase mt-1">Sharpe Ratio</div>
          </div>

          <div className="w-px h-16 bg-white/10" />

          <div className="text-center">
            <div
              className="text-[clamp(2.5rem,6vw,4rem)] font-black tabular-nums"
              style={{
                color: '#00FF94',
                textShadow: '0 0 30px rgba(0,255,148,0.4), 0 0 60px rgba(0,255,148,0.1)',
              }}
            >
              +<AnimatedCounter target={187.4} duration={2600} />%
            </div>
            <div className="text-xs tracking-widest text-white/40 uppercase mt-1">Total Return</div>
          </div>

          <div className="w-px h-16 bg-white/10" />

          <div className="text-center">
            <div
              className="text-[clamp(2.5rem,6vw,4rem)] font-black tabular-nums"
              style={{
                color: '#FFB800',
                textShadow: '0 0 30px rgba(255,184,0,0.4), 0 0 60px rgba(255,184,0,0.1)',
              }}
            >
              <AnimatedCounter target={8.3} duration={2200} />%
            </div>
            <div className="text-xs tracking-widest text-white/40 uppercase mt-1">Max Drawdown</div>
          </div>
        </motion.div>

        {/* CTA button */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 1.4, duration: 0.6 }}
          className="flex items-center gap-4"
        >
          <button
            onClick={scrollToContent}
            className={cn(
              'relative group px-10 py-4 rounded-xl font-semibold text-sm tracking-widest uppercase',
              'bg-[#00D4FF] text-black',
              'transition-all duration-300',
              'hover:scale-105 hover:shadow-neon-blue-lg',
              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#00D4FF]',
            )}
            style={{
              boxShadow: '0 0 30px rgba(0,212,255,0.3), 0 0 60px rgba(0,212,255,0.1)',
            }}
          >
            <span className="relative z-10">Launch Dashboard</span>
            <div
              className="absolute inset-0 rounded-xl opacity-0 group-hover:opacity-100 transition-opacity duration-300"
              style={{
                background: 'linear-gradient(135deg, #00D4FF 0%, #0096B4 100%)',
              }}
            />
          </button>

          <button
            className={cn(
              'px-8 py-4 rounded-xl font-medium text-sm tracking-widest uppercase',
              'border border-white/10 text-white/60',
              'transition-all duration-300',
              'hover:border-[#00D4FF]/40 hover:text-white hover:bg-white/5',
            )}
          >
            View Docs
          </button>
        </motion.div>
      </div>

      {/* Scroll indicator */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 2, duration: 1 }}
        className="absolute bottom-8 left-1/2 -translate-x-1/2 flex flex-col items-center gap-2 cursor-pointer"
        onClick={scrollToContent}
        role="button"
        tabIndex={0}
        aria-label="Scroll to content"
        onKeyDown={(e) => e.key === 'Enter' && scrollToContent()}
      >
        <span className="text-xs text-white/30 tracking-widest uppercase">Explore</span>
        <motion.div
          animate={{ y: [0, 6, 0] }}
          transition={{ duration: 1.5, repeat: Infinity, ease: 'easeInOut' }}
        >
          <ChevronDown className="w-5 h-5 text-white/30" />
        </motion.div>
      </motion.div>

      {/* Bottom gradient fade */}
      <div
        className="absolute bottom-0 left-0 right-0 h-32 pointer-events-none"
        style={{ background: 'linear-gradient(to bottom, transparent, #04040A)' }}
      />
    </section>
  )
}
