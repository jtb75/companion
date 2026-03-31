import React from 'react'
import { View, Text, TouchableOpacity, StyleSheet, ActivityIndicator } from 'react-native'
import { useAuth } from './AuthProvider'
import { colors, brand } from '../theme/colors'

export function LoginScreen() {
  const { signInWithGoogle, loading } = useAuth()
  const [error, setError] = React.useState('')
  const [signingIn, setSigningIn] = React.useState(false)

  const handleSignIn = async () => {
    setError('')
    setSigningIn(true)
    try {
      await signInWithGoogle()
    } catch (e: any) {
      setError(e.message || 'Sign in failed')
    } finally {
      setSigningIn(false)
    }
  }

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color={colors.blue} />
      </View>
    )
  }

  return (
    <View style={styles.container}>
      <View style={styles.card}>
        <Text style={styles.emoji}>{brand.emoji}</Text>
        <Text style={styles.title}>{brand.name}</Text>
        <Text style={styles.subtitle}>Your daily independence assistant</Text>

        <TouchableOpacity
          style={styles.button}
          onPress={handleSignIn}
          disabled={signingIn}
        >
          {signingIn ? (
            <ActivityIndicator color={colors.white} />
          ) : (
            <Text style={styles.buttonText}>Sign in with Google</Text>
          )}
        </TouchableOpacity>

        {error ? <Text style={styles.error}>{error}</Text> : null}
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
  center: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: colors.cream,
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
  emoji: { fontSize: 48, marginBottom: 8 },
  title: { fontSize: 24, fontWeight: '700', color: colors.blue, marginBottom: 4 },
  subtitle: { fontSize: 14, color: colors.gray500, marginBottom: 32 },
  button: {
    backgroundColor: colors.blue,
    borderRadius: 12,
    paddingVertical: 14,
    paddingHorizontal: 32,
    width: '100%',
    alignItems: 'center',
  },
  buttonText: { color: colors.white, fontSize: 16, fontWeight: '600' },
  error: { color: colors.rose, fontSize: 13, marginTop: 16, textAlign: 'center' },
})
