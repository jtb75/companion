import React, { createContext, useContext, useEffect, useState } from 'react'
import auth, { FirebaseAuthTypes } from '@react-native-firebase/auth'
import { GoogleSignin } from '@react-native-google-signin/google-signin'

interface AuthContextType {
  user: FirebaseAuthTypes.User | null
  loading: boolean
  needsVerification: boolean
  signInWithGoogle: () => Promise<void>
  signInWithEmail: (email: string, password: string) => Promise<void>
  registerWithEmail: (email: string, password: string) => Promise<void>
  resendVerification: () => Promise<void>
  signOut: () => Promise<void>
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  loading: true,
  needsVerification: false,
  signInWithGoogle: async () => {},
  signInWithEmail: async () => {},
  registerWithEmail: async () => {},
  resendVerification: async () => {},
  signOut: async () => {},
})

export function useAuth() {
  return useContext(AuthContext)
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<FirebaseAuthTypes.User | null>(null)
  const [loading, setLoading] = useState(true)
  const [needsVerification, setNeedsVerification] = useState(false)

  useEffect(() => {
    GoogleSignin.configure({
      scopes: ['email', 'profile'],
    })
    const unsubscribe = auth().onAuthStateChanged((u) => {
      if (u && !u.emailVerified && u.providerData.some((p) => p.providerId === 'password')) {
        setNeedsVerification(true)
      } else {
        setNeedsVerification(false)
      }
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
    const result = await auth().createUserWithEmailAndPassword(email, password)
    await result.user.sendEmailVerification()
    setNeedsVerification(true)
  }

  const resendVerification = async () => {
    const currentUser = auth().currentUser
    if (currentUser) {
      await currentUser.sendEmailVerification()
    }
  }

  const signOut = async () => {
    setNeedsVerification(false)
    await auth().signOut()
  }

  return (
    <AuthContext.Provider value={{ user, loading, needsVerification, signInWithGoogle, signInWithEmail, registerWithEmail, resendVerification, signOut }}>
      {children}
    </AuthContext.Provider>
  )
}
