import type { Metadata, Viewport } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'

const inter = Inter({
  subsets: ['latin'],
  variable: '--font-inter',
  display: 'swap',
  preload: true,
})

export const metadata: Metadata = {
  title: 'AETHERTRADE-SWARM — AI-Driven Multi-Strategy Trading Platform',
  description:
    '9 Strategy Pods. 4 Regimes. 1 Unified Intelligence. Powered by AetherLink B.V.',
  keywords: ['algorithmic trading', 'AI trading', 'multi-strategy', 'quantitative finance', 'hedge fund'],
  authors: [{ name: 'AetherLink B.V.' }],
  openGraph: {
    title: 'AETHERTRADE-SWARM Trading Platform',
    description: 'Next-generation AI-driven multi-strategy trading intelligence',
    type: 'website',
  },
}

export const viewport: Viewport = {
  themeColor: '#04040A',
  width: 'device-width',
  initialScale: 1,
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className="dark">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
      </head>
      <body className={`${inter.variable} font-sans antialiased bg-void-900 text-white overflow-x-hidden`}>
        {children}
      </body>
    </html>
  )
}
