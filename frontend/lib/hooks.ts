'use client'

import useSWR from 'swr'
import { createSwrFetcher, publicFetcher } from './fetcher'
import type { ApiRegimeResponse, ApiPodListResponse, ApiPerformanceMetrics, ApiRiskDashboard, ApiKillSwitchesResponse, ApiHealthResponse } from './api'

// Store API key in memory (set once after first key generation)
let _apiKey: string | null = null

export function setApiKey(key: string): void {
  _apiKey = key
  // Also persist to sessionStorage for tab refreshes
  if (typeof window !== 'undefined') {
    sessionStorage.setItem('oracle_api_key', key)
  }
}

export function getApiKey(): string | null {
  if (_apiKey) return _apiKey
  if (typeof window !== 'undefined') {
    _apiKey = sessionStorage.getItem('oracle_api_key')
  }
  return _apiKey
}

function useAuthFetcher() {
  const key = getApiKey()
  return key ? createSwrFetcher(key) : null
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || ''

// ---------------------------------------------------------------------------
// SWR hooks — return null/fallback when API unavailable
// ---------------------------------------------------------------------------

export function useHealth() {
  return useSWR<ApiHealthResponse>(
    `${API_BASE}/health`,
    publicFetcher,
    {
      refreshInterval: 30000,
      revalidateOnFocus: false,
      shouldRetryOnError: false,
    }
  )
}

export function useRegime() {
  const fetcher = useAuthFetcher()
  return useSWR<ApiRegimeResponse>(
    fetcher ? `${API_BASE}/api/v1/regime` : null,
    fetcher,
    {
      refreshInterval: 10000,
      revalidateOnFocus: false,
      shouldRetryOnError: false,
    }
  )
}

export function useStrategies() {
  const fetcher = useAuthFetcher()
  return useSWR<ApiPodListResponse>(
    fetcher ? `${API_BASE}/api/v1/strategies` : null,
    fetcher,
    {
      refreshInterval: 15000,
      revalidateOnFocus: false,
      shouldRetryOnError: false,
    }
  )
}

export function usePerformance() {
  const fetcher = useAuthFetcher()
  return useSWR<ApiPerformanceMetrics>(
    fetcher ? `${API_BASE}/api/v1/portfolio/performance` : null,
    fetcher,
    {
      refreshInterval: 30000,
      revalidateOnFocus: false,
      shouldRetryOnError: false,
    }
  )
}

export function useRiskDashboard() {
  const fetcher = useAuthFetcher()
  return useSWR<ApiRiskDashboard>(
    fetcher ? `${API_BASE}/api/v1/risk` : null,
    fetcher,
    {
      refreshInterval: 15000,
      revalidateOnFocus: false,
      shouldRetryOnError: false,
    }
  )
}

export function useKillSwitches() {
  const fetcher = useAuthFetcher()
  return useSWR<ApiKillSwitchesResponse>(
    fetcher ? `${API_BASE}/api/v1/risk/kill-switches` : null,
    fetcher,
    {
      refreshInterval: 15000,
      revalidateOnFocus: false,
      shouldRetryOnError: false,
    }
  )
}

// Check if API is reachable (used to decide live vs simulated)
export function useApiStatus() {
  const { data, error } = useHealth()
  return {
    isConnected: !!data && !error,
    isLoading: !data && !error,
    health: data,
  }
}
