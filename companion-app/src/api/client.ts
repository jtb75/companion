import auth from '@react-native-firebase/auth'

export const API_BASE = __DEV__
  ? 'https://companion-staging-backend-381910341082.us-central1.run.app'
  : 'https://companion-staging-backend-381910341082.us-central1.run.app'

export async function api<T>(path: string, options?: RequestInit): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  }

  const user = auth().currentUser
  if (user) {
    const token = await user.getIdToken()
    headers['Authorization'] = `Bearer ${token}`
  }

  const res = await fetch(`${API_BASE}${path}`, {
    headers: { ...headers, ...options?.headers },
    ...options,
  })

  if (!res.ok) {
    throw new Error(`API error: ${res.status}`)
  }

  if (res.status === 204) {
    return {} as T
  }

  return res.json()
}
