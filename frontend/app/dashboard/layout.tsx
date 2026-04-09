'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
  LayoutDashboard,
  Activity,
  Layers,
  Briefcase,
  Shield,
  Settings,
  ChevronLeft,
  ChevronRight,
  Menu,
  X,
  TrendingUp,
  TrendingDown,
  Minus,
  AlertTriangle,
  Wifi,
  WifiOff,
  Zap,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { useRegime, useApiStatus } from '@/lib/hooks'
import { REGIMES } from '@/lib/data'

const NAV_ITEMS = [
  {
    href: '/dashboard',
    label: 'Overzicht',
    icon: LayoutDashboard,
    exact: true,
  },
  {
    href: '/dashboard/regime',
    label: 'Regime',
    icon: Activity,
    exact: false,
  },
  {
    href: '/dashboard/pods',
    label: 'Strategie Pods',
    icon: Layers,
    exact: false,
  },
  {
    href: '/dashboard/portfolio',
    label: 'Portefeuille',
    icon: Briefcase,
    exact: false,
  },
  {
    href: '/dashboard/risk',
    label: 'Risicobeheer',
    icon: Shield,
    exact: false,
  },
  {
    href: '/dashboard/settings',
    label: 'Instellingen',
    icon: Settings,
    exact: false,
  },
]

const REGIME_ICONS = {
  bull: TrendingUp,
  bear: TrendingDown,
  crisis: AlertTriangle,
  range: Minus,
}

function RegimeBadge() {
  const { data: apiRegime } = useRegime()
  const { isConnected } = useApiStatus()
  const [cycleIndex, setCycleIndex] = useState(0)

  useEffect(() => {
    if (apiRegime) return
    const interval = setInterval(() => {
      setCycleIndex((prev) => (prev + 1) % REGIMES.length)
    }, 12000)
    return () => clearInterval(interval)
  }, [apiRegime])

  const regime = apiRegime
    ? {
        type: apiRegime.regime as 'bull' | 'bear' | 'crisis' | 'range',
        label:
          apiRegime.regime === 'bull'
            ? 'BULL MARKET'
            : apiRegime.regime === 'bear'
            ? 'BEAR MARKET'
            : apiRegime.regime === 'crisis'
            ? 'CRISIS MODE'
            : 'RANGE-BOUND',
        confidence: Math.round(apiRegime.confidence * 100),
        color:
          apiRegime.regime === 'bull'
            ? '#00FF94'
            : apiRegime.regime === 'bear'
            ? '#FF3366'
            : apiRegime.regime === 'crisis'
            ? '#FFB800'
            : '#00D4FF',
      }
    : {
        type: REGIMES[cycleIndex].type,
        label: REGIMES[cycleIndex].label,
        confidence: REGIMES[cycleIndex].confidence,
        color: REGIMES[cycleIndex].color,
      }

  const Icon = REGIME_ICONS[regime.type]

  return (
    <div className="flex items-center gap-2">
      <div
        className="w-1.5 h-1.5 rounded-full"
        style={{ background: regime.color, boxShadow: `0 0 6px ${regime.color}` }}
      />
      <Icon className="w-3.5 h-3.5" style={{ color: regime.color }} />
      <span className="text-xs font-bold tracking-wider" style={{ color: regime.color }}>
        {regime.label}
      </span>
      <span className="text-xs text-white/30 tabular-nums">{regime.confidence}%</span>
      <div
        className={cn(
          'flex items-center gap-1 ml-1 px-1.5 py-0.5 rounded text-[10px] font-medium',
          isConnected ? 'text-[#00FF94] bg-[#00FF94]/10' : 'text-white/30 bg-white/5'
        )}
      >
        {isConnected ? (
          <>
            <Wifi className="w-2.5 h-2.5" />
            LIVE
          </>
        ) : (
          <>
            <WifiOff className="w-2.5 h-2.5" />
            DEMO
          </>
        )}
      </div>
    </div>
  )
}

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const [collapsed, setCollapsed] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)

  // Close mobile nav on route change
  useEffect(() => {
    setMobileOpen(false)
  }, [pathname])

  function isActive(item: (typeof NAV_ITEMS)[0]): boolean {
    if (item.exact) return pathname === item.href
    return pathname.startsWith(item.href)
  }

  const SidebarContent = () => (
    <>
      {/* Logo / Brand */}
      <div
        className={cn(
          'flex items-center gap-3 px-4 py-5 border-b border-white/5',
          collapsed && 'justify-center px-3'
        )}
      >
        <div
          className="flex-shrink-0 w-8 h-8 rounded-xl flex items-center justify-center"
          style={{
            background: 'linear-gradient(135deg, #7C3AED 0%, #00D4FF 100%)',
            boxShadow: '0 0 20px rgba(124,58,237,0.4)',
          }}
        >
          <Zap className="w-4 h-4 text-white" />
        </div>
        {!collapsed && (
          <div className="min-w-0">
            <div className="text-sm font-black text-white tracking-tight truncate">
              AETHERTRADE
            </div>
            <div className="text-[10px] text-white/30 tracking-widest uppercase truncate">
              Swarm Platform
            </div>
          </div>
        )}
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-4 px-2 space-y-0.5" aria-label="Dashboard navigation">
        {NAV_ITEMS.map((item) => {
          const active = isActive(item)
          const Icon = item.icon
          return (
            <Link
              key={item.href}
              href={item.href}
              aria-current={active ? 'page' : undefined}
              className={cn(
                'group flex items-center gap-3 rounded-xl transition-all duration-200',
                collapsed ? 'px-3 py-3 justify-center' : 'px-3 py-2.5',
                active
                  ? 'bg-[#7C3AED]/20 text-white'
                  : 'text-white/40 hover:text-white hover:bg-white/5'
              )}
              style={
                active
                  ? { boxShadow: 'inset 0 0 0 1px rgba(124,58,237,0.3)' }
                  : undefined
              }
              title={collapsed ? item.label : undefined}
            >
              <Icon
                className={cn('w-4 h-4 flex-shrink-0 transition-colors', active && 'text-[#7C3AED]')}
                style={active ? { filter: 'drop-shadow(0 0 6px #7C3AED)' } : undefined}
              />
              {!collapsed && (
                <span className="text-sm font-medium truncate">{item.label}</span>
              )}
              {active && !collapsed && (
                <div className="ml-auto w-1.5 h-1.5 rounded-full bg-[#7C3AED] flex-shrink-0" />
              )}
            </Link>
          )
        })}
      </nav>

      {/* Footer */}
      {!collapsed && (
        <div className="px-4 pb-4 pt-2 border-t border-white/5">
          <div className="text-[10px] text-white/20 text-center">
            AetherLink B.V. &copy; 2026
          </div>
        </div>
      )}
    </>
  )

  return (
    <div className="flex min-h-screen bg-[#0A0A0F]">
      {/* Mobile overlay */}
      {mobileOpen && (
        <div
          className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40 lg:hidden"
          onClick={() => setMobileOpen(false)}
          aria-hidden="true"
        />
      )}

      {/* Mobile sidebar */}
      <aside
        className={cn(
          'fixed top-0 left-0 bottom-0 z-50 w-64 flex flex-col',
          'bg-[#0D0D14] border-r border-white/5',
          'transition-transform duration-300 ease-in-out lg:hidden',
          mobileOpen ? 'translate-x-0' : '-translate-x-full'
        )}
        aria-label="Mobile navigation"
      >
        <button
          onClick={() => setMobileOpen(false)}
          className="absolute top-4 right-4 w-7 h-7 rounded-lg bg-white/5 flex items-center justify-center text-white/40 hover:text-white hover:bg-white/10 transition-colors"
          aria-label="Close navigation"
        >
          <X className="w-4 h-4" />
        </button>
        <SidebarContent />
      </aside>

      {/* Desktop sidebar */}
      <aside
        className={cn(
          'hidden lg:flex flex-col flex-shrink-0 sticky top-0 h-screen',
          'bg-[#0D0D14] border-r border-white/5',
          'transition-all duration-300 ease-in-out',
          collapsed ? 'w-16' : 'w-64'
        )}
        aria-label="Dashboard navigation"
      >
        <SidebarContent />

        {/* Collapse toggle */}
        <button
          onClick={() => setCollapsed(!collapsed)}
          className={cn(
            'absolute -right-3 top-20 w-6 h-6 rounded-full',
            'bg-[#1A1A2E] border border-white/10',
            'flex items-center justify-center',
            'text-white/30 hover:text-white hover:border-white/30',
            'transition-all duration-200',
            'shadow-lg shadow-black/50'
          )}
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {collapsed ? (
            <ChevronRight className="w-3.5 h-3.5" />
          ) : (
            <ChevronLeft className="w-3.5 h-3.5" />
          )}
        </button>
      </aside>

      {/* Main content */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top bar */}
        <header
          className="sticky top-0 z-30 flex items-center justify-between px-4 sm:px-6 h-14 border-b border-white/5"
          style={{
            background: 'rgba(10,10,15,0.9)',
            backdropFilter: 'blur(20px)',
            WebkitBackdropFilter: 'blur(20px)',
          }}
        >
          <div className="flex items-center gap-3">
            {/* Mobile menu button */}
            <button
              onClick={() => setMobileOpen(true)}
              className="lg:hidden w-8 h-8 rounded-lg bg-white/5 flex items-center justify-center text-white/40 hover:text-white hover:bg-white/10 transition-colors"
              aria-label="Open navigation"
              aria-expanded={mobileOpen}
            >
              <Menu className="w-4 h-4" />
            </button>

            {/* Breadcrumb-style page title */}
            <div className="flex items-center gap-2 text-sm">
              <span className="text-white/20">Dashboard</span>
              {pathname !== '/dashboard' && (
                <>
                  <span className="text-white/10">/</span>
                  <span className="text-white/70 capitalize">
                    {pathname.split('/').at(-1)}
                  </span>
                </>
              )}
            </div>
          </div>

          {/* Regime badge in top bar */}
          <RegimeBadge />
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-auto">
          {children}
        </main>
      </div>
    </div>
  )
}
