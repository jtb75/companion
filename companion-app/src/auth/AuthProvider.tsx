import React, { createContext, useContext, useEffect, useState } from 'react'
import auth, { FirebaseAuthTypes } from '@react-native-firebase/auth'
import messaging from '@react-native-firebase/messaging'
import { GoogleSignin } from '@react-native-google-signin/google-signin'
import { api } from '../api/client'

interface AuthContextType {
  user: FirebaseAuthTypes.User | null
  loading: boolean
  signInWithGoogle: () => Promise<void>
  signInWithEmail: (email: string, password: string) => Promise<void>
  registerWithEmail: (email: string, password: string) => Promise<void>
  signOut: () => Promise<void>
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  loading: true,
  signInWithGoogle: async () => {},
  signInWithEmail: async () => {},
  registerWithEmail: async () => {},
  signOut: async () => {},
})

export function useAuth() {
  return useContext(AuthContext)
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<FirebaseAuthTypes.User | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    GoogleSignin.configure({
      scopes: ['email', 'profile'],
    })
    const unsubscribe = auth().onAuthStateChanged((u) => {
      setUser(u)
      setLoading(false)
    })
    return unsubscribe
  }, [])

  const signInWithGoogle = async () => {
    await GoogleSignin.hasPlayServices()
    const signInResult = await GoogleSignin.signIn()
    const idToken = signInResult?.data?.idToken
    if (!idToken) throw new Error('No ID token')
    const credential = auth.GoogleAuthProvider.credential(idToken)
    await auth().signInWithCredential(credential)
  }

  const signInWithEmail = async (email: string, password: string) => {
    await auth().signInWithEmailAndPassword(email, password)
  }

  const registerWithEmail = async (email: string, password: string) => {
    await auth().createUserWithEmailAndPassword(email, password)
  }

  const signOut = async () => {
    try {
      const token = await messaging().getToken()
      await api('/api/v1/me/devices', {
        method: 'DELETE',
        body: JSON.stringify({ fcm_token: token }),
      })
    } catch (err) {
      console.log('[AuthProvider] failed to deactivate FCM token:', err)
    }
    await auth().signOut()
  }

  return (
    <AuthContext.Provider value={{ user, loading, signInWithGoogle, signInWithEmail, registerWithEmail, signOut }}>
      {children}
    </AuthContext.Provider>
  )
}
