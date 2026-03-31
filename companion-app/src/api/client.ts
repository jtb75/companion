import auth from '@react-native-firebase/auth'

const API_BASE = __DEV__
  ? 'http://localhost:8000'
  : 'https://companion-staging-backend-44gbcsdrnq-uc.a.run.app'

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

  return res.json()
}
