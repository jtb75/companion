import { auth } from '../auth/firebase'

const API_BASE = import.meta.env.VITE_API_BASE_URL || ''

export async function api<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  }

  const user = auth.currentUser
  if (user) {
    const token = await user.getIdToken()
    headers['Authorization'] = `Bearer ${token}`
  }

  const res = await fetch(`${API_BASE}${path}`, {
    headers: { ...headers, ...options?.headers },
    signal: options?.signal,
    ...options,
  })

  // On 401, try refreshing the token and retry once
  if (res.status === 401 && user) {
    const freshToken = await user.getIdToken(true) // force refresh
    headers['Authorization'] = `Bearer ${freshToken}`
    const retry = await fetch(`${API_BASE}${path}`, {
      headers: { ...headers, ...options?.headers },
      ...options,
    })
    if (!retry.ok) {
      throw new Error(`API error: ${retry.status}`)
    }
    return retry.json()
  }

  if (!res.ok) {
    throw new Error(`API error: ${res.status}`)
  }

  if (res.status === 204) {
    return {} as T
  }

  return res.json()
}
