import React from 'react'
import {
  View, Text, TextInput, TouchableOpacity,
  StyleSheet, ActivityIndicator, KeyboardAvoidingView, Platform,
} from 'react-native'
import auth from '@react-native-firebase/auth'
import { useAuth } from './AuthProvider'
import { colors, brand } from '../theme/colors'

export function LoginScreen() {
  const { signInWithGoogle, signInWithEmail, registerWithEmail, loading } = useAuth()
  const [email, setEmail] = React.useState('')
  const [password, setPassword] = React.useState('')
  const [error, setError] = React.useState('')
  const [busy, setBusy] = React.useState(false)
  const [mode, setMode] = React.useState<'login' | 'register'>('login')

  const handleGoogle = async () => {
    setError('')
    setBusy(true)
    try {
      await signInWithGoogle()
    } catch (e: any) {
      setError(e.message || 'Google sign in failed')
    } finally {
      setBusy(false)
    }
  }

  const handleEmail = async () => {
    if (!email.trim() || !password.trim()) {
      setError('Email and password are required')
      return
    }
    setError('')
    setBusy(true)
    try {
      if (mode === 'register') {
        await registerWithEmail(email.trim(), password)
      } else {
        await signInWithEmail(email.trim(), password)
      }
    } catch (e: any) {
      const msg = e.code === 'auth/user-not-found' ? 'No account found with this email'
        : e.code === 'auth/wrong-password' ? 'Incorrect password'
        : e.code === 'auth/email-already-in-use' ? 'An account with this email already exists'
        : e.code === 'auth/weak-password' ? 'Password must be at least 6 characters'
        : e.code === 'auth/invalid-email' ? 'Please enter a valid email'
        : e.message || 'Authentication failed'
      setError(msg)
    } finally {
      setBusy(false)
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
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
    >
      <View style={styles.card}>
        <Text style={styles.emoji}>{brand.emoji}</Text>
        <Text style={styles.title}>{brand.name}</Text>
        <Text style={styles.subtitle}>Your daily independence assistant</Text>

        <TouchableOpacity style={styles.googleButton} onPress={handleGoogle} disabled={busy}>
          <Text style={styles.googleText}>Sign in with Google</Text>
        </TouchableOpacity>

        <View style={styles.divider}>
          <View style={styles.dividerLine} />
          <Text style={styles.dividerText}>or</Text>
          <View style={styles.dividerLine} />
        </View>

        <TextInput
          style={styles.input}
          placeholder="Email"
          placeholderTextColor={colors.gray400}
          value={email}
          onChangeText={setEmail}
          autoCapitalize="none"
          keyboardType="email-address"
        />
        <TextInput
          style={styles.input}
          placeholder="Password"
          placeholderTextColor={colors.gray400}
          value={password}
          onChangeText={setPassword}
          secureTextEntry
        />

        <TouchableOpacity style={styles.button} onPress={handleEmail} disabled={busy}>
          {busy ? (
            <ActivityIndicator color={colors.white} />
          ) : (
            <Text style={styles.buttonText}>
              {mode === 'login' ? 'Sign In' : 'Create Account'}
            </Text>
          )}
        </TouchableOpacity>

        {error ? <Text style={styles.error}>{error}</Text> : null}

        {mode === 'login' && (
          <TouchableOpacity
            style={styles.forgotButton}
            onPress={async () => {
              if (!email.trim()) {
                setError('Enter your email first, then tap Forgot Password')
                return
              }
              try {
                await auth().sendPasswordResetEmail(email.trim())
                setError('')
                setPassword('')
                setBusy(false)
                // Use error style for success message too (simple)
                setError('Password reset email sent! Check your inbox.')
              } catch (e: any) {
                setError(
                  e.code === 'auth/user-not-found'
                    ? 'No account found with this email'
                    : 'Could not send reset email. Try again.'
                )
              }
            }}
          >
            <Text style={styles.forgotText}>Forgot password?</Text>
          </TouchableOpacity>
        )}

        <TouchableOpacity
          style={styles.toggleButton}
          onPress={() => { setMode(mode === 'login' ? 'register' : 'login'); setError('') }}
        >
          <Text style={styles.toggleText}>
            {mode === 'login' ? "Don't have an account? " : 'Already have an account? '}
            <Text style={styles.toggleLink}>
              {mode === 'login' ? 'Register' : 'Sign in'}
            </Text>
          </Text>
        </TouchableOpacity>
      </View>
    </KeyboardAvoidingView>
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
  subtitle: { fontSize: 14, color: colors.gray500, marginBottom: 24 },
  googleButton: {
    backgroundColor: colors.white,
    borderWidth: 2,
    borderColor: colors.gray200,
    borderRadius: 12,
    paddingVertical: 14,
    width: '100%',
    alignItems: 'center',
  },
  googleText: { color: colors.gray700, fontSize: 16, fontWeight: '600' },
  divider: {
    flexDirection: 'row',
    alignItems: 'center',
    width: '100%',
    marginVertical: 20,
  },
  dividerLine: { flex: 1, height: 1, backgroundColor: colors.gray200 },
  dividerText: { paddingHorizontal: 12, fontSize: 13, color: colors.gray400 },
  input: {
    width: '100%',
    borderWidth: 2,
    borderColor: colors.gray200,
    borderRadius: 12,
    paddingVertical: 12,
    paddingHorizontal: 16,
    fontSize: 15,
    color: colors.gray800,
    marginBottom: 10,
  },
  button: {
    backgroundColor: colors.blue,
    borderRadius: 12,
    paddingVertical: 14,
    width: '100%',
    alignItems: 'center',
    marginTop: 4,
  },
  buttonText: { color: colors.white, fontSize: 16, fontWeight: '600' },
  error: { color: colors.rose, fontSize: 13, marginTop: 12, textAlign: 'center' },
  forgotButton: { marginTop: 8 },
  forgotText: { fontSize: 13, color: colors.blue, fontWeight: '500' },
  toggleButton: { marginTop: 16 },
  toggleText: { fontSize: 13, color: colors.gray500 },
  toggleLink: { color: colors.blue, fontWeight: '600' },
})
