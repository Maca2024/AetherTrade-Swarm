const API_BASE = process.env.NEXT_PUBLIC_API_URL || ''

export class ApiError extends Error {
  status: number
  constructor(message: string, status: number) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

export async function apiFetch<T>(
  path: string,
  options?: RequestInit & { apiKey?: string }
): Promise<T> {
  const { apiKey, ...fetchOptions } = options ?? {}

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(apiKey ? { 'X-API-Key': apiKey } : {}),
    ...(fetchOptions.headers as Record<string, string> ?? {}),
  }

  const url = path.startsWith('http') ? path : `${API_BASE}${path}`

  const res = await fetch(url, {
    ...fetchOptions,
    headers,
  })

  if (!res.ok) {
    const body = await res.text().catch(() => 'Unknown error')
    throw new ApiError(body, res.status)
  }

  return res.json() as Promise<T>
}

// SWR fetcher factory — takes an optional API key
export function createSwrFetcher(apiKey?: string) {
  return <T>(path: string): Promise<T> =>
    apiFetch<T>(path, { apiKey })
}

// Default fetcher for public endpoints (like /health)
export const publicFetcher = <T>(path: string): Promise<T> =>
  apiFetch<T>(path)
