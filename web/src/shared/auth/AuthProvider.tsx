import { createContext, useContext, useEffect, useState, ReactNode } from 'react'
import {
  User,
  onAuthStateChanged,
  signInWithPopup,
  signInWithEmailAndPassword,
  signOut,
  createUserWithEmailAndPassword,
} from 'firebase/auth'
import { auth, googleProvider } from './firebase'

interface AuthContextType {
  user: User | null
  loading: boolean
  role: string | null        // "admin", "caregiver", "unauthorized", null (checking)
  adminRole: string | null   // "viewer", "editor", "admin"
  authorized: boolean | null // null = still checking, true/false = result
  caregiverUsers: Array<{ user_id: string; contact_name: string; access_tier: string }> | null
  loginWithGoogle: () => Promise<void>
  loginWithEmail: (email: string, password: string) => Promise<void>
  registerWithEmail: (email: string, password: string) => Promise<void>
  logout: () => Promise<void>
  getToken: () => Promise<string | null>
}

const AuthContext = createContext<AuthContextType | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const [role, setRole] = useState<string | null>(null)
  const [adminRole, setAdminRole] = useState<string | null>(null)
  const [authorized, setAuthorized] = useState<boolean | null>(null)
  const [caregiverUsers, setCaregiverUsers] = useState<Array<{ user_id: string; contact_name: string; access_tier: string }> | null>(null)

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, (user) => {
      setUser(user)
      setLoading(false)
    })
    return unsubscribe
  }, [])

  useEffect(() => {
    if (!user) {
      setRole(null)
      setAuthorized(null)
      setAdminRole(null)
      setCaregiverUsers(null)
      return
    }

    // Skip if already authorized (avoid re-check on token refresh)
    if (authorized !== null) return

    // Check authorization
    const checkAuth = async () => {
      try {
        const token = await user.getIdToken()
        const res = await fetch(
          `${import.meta.env.VITE_API_BASE_URL || ''}/api/v1/auth/check`,
          { headers: { Authorization: `Bearer ${token}` } }
        )
        if (res.ok) {
          const data = await res.json()
          setRole(data.role)
          setAdminRole(data.admin_role || null)
          setAuthorized(true)
          setCaregiverUsers(data.caregiver_users || null)
        } else {
          setRole('unauthorized')
          setAuthorized(false)
        }
      } catch {
        setRole('unauthorized')
        setAuthorized(false)
      }
    }
    checkAuth()
  }, [user, authorized])

  const loginWithGoogle = async () => {
    await signInWithPopup(auth, googleProvider)
  }

  const loginWithEmail = async (email: string, password: string) => {
    await signInWithEmailAndPassword(auth, email, password)
  }

  const registerWithEmail = async (email: string, password: string) => {
    await createUserWithEmailAndPassword(auth, email, password)
  }

  const logout = async () => {
    await signOut(auth)
  }

  const getToken = async (): Promise<string | null> => {
    if (!user) return null
    return user.getIdToken()
  }

  return (
    <AuthContext.Provider value={{
      user, loading, role, adminRole, authorized, caregiverUsers,
      loginWithGoogle, loginWithEmail,
      registerWithEmail, logout, getToken,
    }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth must be used within AuthProvider')
  return context
}
