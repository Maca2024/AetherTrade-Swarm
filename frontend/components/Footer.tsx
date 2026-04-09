'use client'

import { motion } from 'framer-motion'
import { useInView } from 'react-intersection-observer'
import { Activity, Shield, Zap, Globe } from 'lucide-react'

export default function Footer() {
  const [ref, inView] = useInView({ threshold: 0.3, triggerOnce: true })

  return (
    <footer
      ref={ref}
      className="relative border-t overflow-hidden"
      style={{ borderColor: 'rgba(255,255,255,0.06)' }}
    >
      {/* Background gradient */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          background: 'radial-gradient(ellipse at 50% 100%, rgba(0,212,255,0.04) 0%, transparent 70%)',
        }}
      />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-16 relative z-10">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-10 mb-12">
          {/* Brand */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={inView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.6 }}
          >
            <div className="flex items-center gap-3 mb-4">
              <div
                className="w-10 h-10 rounded-xl flex items-center justify-center text-lg font-black"
                style={{
                  background: 'linear-gradient(135deg, rgba(0,212,255,0.2), rgba(139,92,246,0.2))',
                  border: '1px solid rgba(0,212,255,0.2)',
                  color: '#00D4FF',
                  textShadow: '0 0 15px rgba(0,212,255,0.5)',
                }}
              >
                AT
              </div>
              <div>
                <div
                  className="text-sm font-black tracking-wider"
                  style={{
                    background: 'linear-gradient(135deg, #FFFFFF 0%, #00D4FF 100%)',
                    WebkitBackgroundClip: 'text',
                    WebkitTextFillColor: 'transparent',
                    backgroundClip: 'text',
                  }}
                >
                  AETHERTRADE-SWARM
                </div>
                <div className="text-[10px] text-white/30 tracking-widest">
                  AI HANDELSPLATFORM
                </div>
              </div>
            </div>
            <p className="text-sm text-white/30 leading-relaxed max-w-xs">
              Volgende generatie multi-strategie kwantitatieve handelsintelligentie.
              9 pods, 4 regimes, verenigd door AI.
            </p>

            {/* Status indicators */}
            <div className="flex items-center gap-4 mt-4">
              {[
                { icon: <Activity className="w-3 h-3" />, label: 'API', status: 'Operationeel' },
                { icon: <Shield className="w-3 h-3" />, label: 'Risico', status: 'Normaal' },
              ].map((item) => (
                <div key={item.label} className="flex items-center gap-1.5">
                  <div className="text-[#00FF94]">{item.icon}</div>
                  <span className="text-xs text-white/30">
                    {item.label}: <span className="text-[#00FF94]">{item.status}</span>
                  </span>
                </div>
              ))}
            </div>
          </motion.div>

          {/* Links */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={inView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.6, delay: 0.1 }}
            className="grid grid-cols-2 gap-6"
          >
            <div>
              <h4 className="text-xs font-bold text-white/50 uppercase tracking-widest mb-4">Platform</h4>
              <ul className="space-y-2.5">
                {['Dashboard', 'Strategie Pods', 'Risicobeheer', 'Prestaties', 'Architectuur'].map((item) => (
                  <li key={item}>
                    <a
                      href="#"
                      className="text-sm text-white/30 hover:text-white/60 transition-colors"
                    >
                      {item}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <h4 className="text-xs font-bold text-white/50 uppercase tracking-widest mb-4">Ontwikkelaars</h4>
              <ul className="space-y-2.5">
                {['API Docs', 'SDK Referentie', 'Webhooks', 'Limieten', 'Status'].map((item) => (
                  <li key={item}>
                    <a
                      href="#"
                      className="text-sm text-white/30 hover:text-white/60 transition-colors"
                    >
                      {item}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          </motion.div>

          {/* Stats */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={inView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.6, delay: 0.2 }}
          >
            <h4 className="text-xs font-bold text-white/50 uppercase tracking-widest mb-4">
              Platform Statistieken
            </h4>
            <div className="space-y-3">
              {[
                { label: 'Beheerd Vermogen', value: '$847M', color: '#00D4FF' },
                { label: 'Dagelijkse Trades', value: '12.847', color: '#00FF94' },
                { label: 'Data Feeds', value: '500+', color: '#8B5CF6' },
                { label: 'Uptime (90d)', value: '99,99%', color: '#FFB800' },
              ].map((stat) => (
                <div key={stat.label} className="flex items-center justify-between">
                  <span className="text-xs text-white/30">{stat.label}</span>
                  <span className="text-sm font-bold tabular-nums" style={{ color: stat.color }}>
                    {stat.value}
                  </span>
                </div>
              ))}
            </div>
          </motion.div>
        </div>

        {/* Bottom bar */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={inView ? { opacity: 1 } : {}}
          transition={{ duration: 0.6, delay: 0.4 }}
          className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-8"
          style={{ borderTop: '1px solid rgba(255,255,255,0.06)' }}
        >
          <div className="flex items-center gap-2">
            <span className="text-xs text-white/20">Powered by</span>
            <span
              className="text-xs font-bold tracking-wider"
              style={{
                background: 'linear-gradient(135deg, #00D4FF, #8B5CF6)',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
                backgroundClip: 'text',
              }}
            >
              AetherLink B.V.
            </span>
            <span className="text-[10px] text-white/15 ml-1">
              © 2026 All rights reserved
            </span>
          </div>

          <div className="flex items-center gap-4">
            <span className="text-[10px] text-white/20">
              Gesimuleerde data voor demonstratiedoeleinden
            </span>
            <div className="flex items-center gap-1.5">
              <div
                className="w-1.5 h-1.5 rounded-full bg-[#00FF94]"
                style={{ boxShadow: '0 0 6px #00FF94' }}
              />
              <span className="text-[10px] text-white/30">Alle systemen nominaal</span>
            </div>
          </div>
        </motion.div>
      </div>
    </footer>
  )
}
