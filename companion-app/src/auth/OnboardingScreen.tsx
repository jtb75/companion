import React, { useState } from 'react'
import {
  View, Text, TextInput, TouchableOpacity,
  StyleSheet, ActivityIndicator, KeyboardAvoidingView, Platform, ScrollView,
} from 'react-native'
import { colors, brand } from '../theme/colors'
import { api } from '../api/client'

interface Props {
  onComplete: () => void
}

export function OnboardingScreen({ onComplete }: Props) {
  const [firstName, setFirstName] = useState('')
  const [lastName, setLastName] = useState('')
  const [preferredName, setPreferredName] = useState('')
  const [phone, setPhone] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async () => {
    if (!firstName.trim()) {
      setError('First name is required')
      return
    }
    setError('')
    setBusy(true)
    try {
      await api('/api/v1/auth/complete-profile', {
        method: 'POST',
        body: JSON.stringify({
          first_name: firstName.trim(),
          last_name: lastName.trim(),
          preferred_name: preferredName.trim() || firstName.trim(),
          phone: phone.trim() || null,
        }),
      })
      onComplete()
    } catch (e: any) {
      setError(e.message || 'Failed to save profile')
    } finally {
      setBusy(false)
    }
  }

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
    >
      <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">
        <View style={styles.card}>
          <Text style={styles.emoji}>{brand.emoji}</Text>
          <Text style={styles.title}>Welcome!</Text>
          <Text style={styles.subtitle}>Let's set up your profile</Text>

          <TextInput
            style={styles.input}
            placeholder="First name *"
            placeholderTextColor={colors.gray400}
            value={firstName}
            onChangeText={setFirstName}
            autoCapitalize="words"
            autoFocus
          />
          <TextInput
            style={styles.input}
            placeholder="Last name"
            placeholderTextColor={colors.gray400}
            value={lastName}
            onChangeText={setLastName}
            autoCapitalize="words"
          />
          <TextInput
            style={styles.input}
            placeholder="What should we call you?"
            placeholderTextColor={colors.gray400}
            value={preferredName}
            onChangeText={setPreferredName}
            autoCapitalize="words"
          />
          <TextInput
            style={styles.input}
            placeholder="Phone number (optional)"
            placeholderTextColor={colors.gray400}
            value={phone}
            onChangeText={setPhone}
            keyboardType="phone-pad"
          />

          {error ? <Text style={styles.error}>{error}</Text> : null}

          <TouchableOpacity style={styles.button} onPress={handleSubmit} disabled={busy}>
            {busy ? (
              <ActivityIndicator color={colors.white} />
            ) : (
              <Text style={styles.buttonText}>Get Started</Text>
            )}
          </TouchableOpacity>
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  )
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.cream,
  },
  scroll: {
    flexGrow: 1,
    justifyContent: 'center',
    alignItems: 'center',
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
  emoji: { fontSize: 48, marginBottom: 8 },
  title: { fontSize: 24, fontWeight: '700', color: colors.blue, marginBottom: 4 },
  subtitle: { fontSize: 14, color: colors.gray500, marginBottom: 24 },
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
    marginTop: 8,
  },
  buttonText: { color: colors.white, fontSize: 16, fontWeight: '600' },
  error: { color: colors.rose, fontSize: 13, marginTop: 4, marginBottom: 4, textAlign: 'center' },
})
