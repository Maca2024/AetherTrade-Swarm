import { type ClassValue, clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs))
}

export function formatNumber(value: number, decimals = 2): string {
  return new Intl.NumberFormat('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value)
}

export function formatPercent(value: number, decimals = 1): string {
  const formatted = Math.abs(value).toFixed(decimals)
  return `${value >= 0 ? '+' : '-'}${formatted}%`
}

export function formatCurrency(value: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    notation: 'compact',
    maximumFractionDigits: 1,
  }).format(value)
}

export function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max)
}

export function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * t
}

// Map a value from one range to another
export function mapRange(
  value: number,
  inMin: number,
  inMax: number,
  outMin: number,
  outMax: number
): number {
  return ((value - inMin) / (inMax - inMin)) * (outMax - outMin) + outMin
}

// Get color intensity for correlation matrix
export function correlationToColor(value: number): string {
  if (value === 1.0) return 'rgba(0, 212, 255, 0.9)'
  if (value > 0.5) return `rgba(0, 212, 255, ${mapRange(value, 0.5, 1, 0.4, 0.8)})`
  if (value > 0.2) return `rgba(139, 92, 246, ${mapRange(value, 0.2, 0.5, 0.2, 0.5)})`
  if (value > 0) return `rgba(255, 255, 255, ${mapRange(value, 0, 0.2, 0.05, 0.2)})`
  if (value > -0.2) return `rgba(255, 51, 102, ${mapRange(value, -0.2, 0, 0.1, 0.25)})`
  return `rgba(255, 51, 102, ${mapRange(value, -1, -0.2, 0.5, 0.3)})`
}

// Debounce utility
export function debounce<T extends (...args: unknown[]) => unknown>(
  fn: T,
  delay: number
): (...args: Parameters<T>) => void {
  let timeoutId: ReturnType<typeof setTimeout>
  return (...args: Parameters<T>) => {
    clearTimeout(timeoutId)
    timeoutId = setTimeout(() => fn(...args), delay)
  }
}

// Generate a masked API key string
export function maskApiKey(key: string): string {
  if (key.length <= 8) return '*'.repeat(key.length)
  return key.slice(0, 8) + '•'.repeat(24) + key.slice(-4)
}

export function generateApiKey(): string {
  const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
  const prefix = 'os_live_'
  let result = prefix
  for (let i = 0; i < 32; i++) {
    result += chars.charAt(Math.floor(Math.random() * chars.length))
  }
  return result
}
