import React, { createContext, useContext, useEffect, useState } from 'react'
import auth, { FirebaseAuthTypes } from '@react-native-firebase/auth'
import { GoogleSignin } from '@react-native-google-signin/google-signin'

interface AuthContextType {
  user: FirebaseAuthTypes.User | null
  loading: boolean
  signInWithGoogle: () => Promise<void>
  signOut: () => Promise<void>
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  loading: true,
  signInWithGoogle: async () => {},
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

  const signOut = async () => {
    await auth().signOut()
  }

  return (
    <AuthContext.Provider value={{ user, loading, signInWithGoogle, signOut }}>
      {children}
    </AuthContext.Provider>
  )
}
