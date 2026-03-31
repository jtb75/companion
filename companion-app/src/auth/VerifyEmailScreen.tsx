import React from 'react'
import { View, Text, TouchableOpacity, StyleSheet, ActivityIndicator } from 'react-native'
import auth from '@react-native-firebase/auth'
import { useAuth } from './AuthProvider'
import { colors, brand } from '../theme/colors'

export function VerifyEmailScreen() {
  const { resendVerification, signOut } = useAuth()
  const [sending, setSending] = React.useState(false)
  const [sent, setSent] = React.useState(false)
  const [checking, setChecking] = React.useState(false)

  const handleResend = async () => {
    setSending(true)
    try {
      await resendVerification()
      setSent(true)
      setTimeout(() => setSent(false), 5000)
    } catch {}
    setSending(false)
  }

  const handleCheckVerification = async () => {
    setChecking(true)
    try {
      await auth().currentUser?.reload()
      const user = auth().currentUser
      if (user?.emailVerified) {
        // Force a state refresh by getting a new token
        await user.getIdToken(true)
        // The onAuthStateChanged won't fire for emailVerified changes,
        // so we trigger a sign-out/sign-in cycle
        const email = user.email
        // Reload the app state
        await auth().currentUser?.reload()
      }
    } catch {}
    setChecking(false)
  }

  return (
    <View style={styles.container}>
      <View style={styles.card}>
        <Text style={styles.emoji}>{brand.emoji}</Text>
        <Text style={styles.title}>Check Your Email</Text>
        <Text style={styles.message}>
          We sent a verification link to your email address. Please click the link to verify your account.
        </Text>

        <TouchableOpacity
          style={styles.checkButton}
          onPress={handleCheckVerification}
          disabled={checking}
        >
          {checking ? (
            <ActivityIndicator color={colors.white} />
          ) : (
            <Text style={styles.checkButtonText}>I've Verified My Email</Text>
          )}
        </TouchableOpacity>

        <TouchableOpacity
          style={styles.resendButton}
          onPress={handleResend}
          disabled={sending}
        >
          <Text style={styles.resendText}>
            {sent ? 'Email sent!' : sending ? 'Sending...' : 'Resend verification email'}
          </Text>
        </TouchableOpacity>

        <TouchableOpacity style={styles.signOutButton} onPress={signOut}>
          <Text style={styles.signOutText}>Sign out</Text>
        </TouchableOpacity>
      </View>
    </View>
  )
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: colors.cream,
    padding: 24,
  },
  card: {
    backgroundColor: colors.white,
    borderRadius: 20,
    padding: 32,
    width: '100%',
    maxWidth: 360,
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.08,
    shadowRadius: 12,
    elevation: 4,
  },
  emoji: { fontSize: 48, marginBottom: 12 },
  title: { fontSize: 22, fontWeight: '700', color: colors.blue, marginBottom: 12 },
  message: { fontSize: 14, color: colors.gray600, textAlign: 'center', lineHeight: 20, marginBottom: 24 },
  checkButton: {
    backgroundColor: colors.blue,
    borderRadius: 12,
    paddingVertical: 14,
    width: '100%',
    alignItems: 'center',
    marginBottom: 12,
  },
  checkButtonText: { color: colors.white, fontSize: 16, fontWeight: '600' },
  resendButton: { paddingVertical: 8 },
  resendText: { fontSize: 14, color: colors.blue, fontWeight: '500' },
  signOutButton: { paddingVertical: 8, marginTop: 8 },
  signOutText: { fontSize: 13, color: colors.gray500 },
})
