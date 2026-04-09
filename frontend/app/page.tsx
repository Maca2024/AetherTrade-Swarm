import dynamic from 'next/dynamic'
import HeroSection from '@/components/HeroSection'
import RegimeIndicator from '@/components/RegimeIndicator'

// Lazy load below-fold sections
const StrategyPodsGrid = dynamic(() => import('@/components/StrategyPodsGrid'), {
  loading: () => <SectionSkeleton />,
})
const PerformanceDashboard = dynamic(() => import('@/components/PerformanceDashboard'), {
  loading: () => <SectionSkeleton />,
})
const ArchitectureViz = dynamic(() => import('@/components/ArchitectureViz'), {
  loading: () => <SectionSkeleton />,
})
const RiskPanel = dynamic(() => import('@/components/RiskPanel'), {
  loading: () => <SectionSkeleton />,
})
const ApiSection = dynamic(() => import('@/components/ApiSection'), {
  loading: () => <SectionSkeleton />,
})
const Footer = dynamic(() => import('@/components/Footer'))
const OracleChat = dynamic(() => import('@/components/OracleChat'), { ssr: false })

function SectionSkeleton() {
  return (
    <div className="py-20 px-4 sm:px-6 max-w-7xl mx-auto">
      <div className="h-12 w-64 mx-auto rounded-xl bg-white/5 mb-8 animate-pulse" />
      <div className="grid grid-cols-3 gap-4">
        {Array.from({ length: 9 }).map((_, i) => (
          <div key={i} className="h-48 rounded-2xl bg-white/3 animate-pulse" />
        ))}
      </div>
    </div>
  )
}

function SectionDivider({ color = '#00D4FF' }: { color?: string }) {
  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6">
      <div
        className="h-px w-full"
        style={{
          background: `linear-gradient(90deg, transparent, ${color}30, transparent)`,
        }}
      />
    </div>
  )
}

export default function OracleSwarmPage() {
  return (
    <main className="relative min-h-screen bg-void-900">
      {/* Persistent ambient background */}
      <div
        className="fixed inset-0 pointer-events-none"
        aria-hidden="true"
        style={{ zIndex: 0 }}
      >
        {/* Top-left deep blue orb */}
        <div
          className="absolute -top-1/4 -left-1/4 w-3/4 h-3/4 rounded-full opacity-[0.03]"
          style={{
            background: 'radial-gradient(circle, #00D4FF 0%, transparent 70%)',
            filter: 'blur(80px)',
          }}
        />
        {/* Bottom-right purple orb */}
        <div
          className="absolute -bottom-1/4 -right-1/4 w-3/4 h-3/4 rounded-full opacity-[0.04]"
          style={{
            background: 'radial-gradient(circle, #8B5CF6 0%, transparent 70%)',
            filter: 'blur(100px)',
          }}
        />
        {/* Center subtle red */}
        <div
          className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-1/2 h-1/2 rounded-full opacity-[0.02]"
          style={{
            background: 'radial-gradient(circle, #FF3366 0%, transparent 70%)',
            filter: 'blur(120px)',
          }}
        />
      </div>

      {/* Page content stack */}
      <div className="relative z-10">
        {/* 1. Hero */}
        <HeroSection />

        {/* 2. Sticky Regime Bar */}
        <RegimeIndicator />

        {/* 3. Strategy Pods */}
        <StrategyPodsGrid />

        <SectionDivider color="#00D4FF" />

        {/* 4. Performance */}
        <PerformanceDashboard />

        <SectionDivider color="#00FF94" />

        {/* 5. Architecture */}
        <ArchitectureViz />

        <SectionDivider color="#8B5CF6" />

        {/* 6. Risk */}
        <RiskPanel />

        <SectionDivider color="#FF3366" />

        {/* 7. API */}
        <ApiSection />

        {/* Footer */}
        <Footer />
      </div>

      {/* Floating chatbot */}
      <OracleChat />
    </main>
  )
}
