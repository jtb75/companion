import React from 'react'
import { View, Text, TouchableOpacity, ScrollView, StyleSheet } from 'react-native'
import { useAuth } from '../auth/AuthProvider'
import { colors, brand } from '../theme/colors'

export function ProfileScreen() {
  const { user, signOut } = useAuth()

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      {/* User info */}
      <View style={styles.card}>
        <View style={styles.avatar}>
          <Text style={styles.avatarText}>
            {(user?.displayName || user?.email || '?')[0].toUpperCase()}
          </Text>
        </View>
        <Text style={styles.name}>{user?.displayName || 'Member'}</Text>
        <Text style={styles.email}>{user?.email}</Text>
      </View>

      {/* Settings placeholder */}
      <View style={styles.card}>
        <Text style={styles.sectionTitle}>Settings</Text>
        <View style={styles.settingRow}>
          <Text style={styles.settingLabel}>Quiet Hours</Text>
          <Text style={styles.settingValue}>9pm - 8am</Text>
        </View>
        <View style={styles.settingRow}>
          <Text style={styles.settingLabel}>Check-in Time</Text>
          <Text style={styles.settingValue}>9:00 AM</Text>
        </View>
        <View style={styles.settingRow}>
          <Text style={styles.settingLabel}>Voice</Text>
          <Text style={styles.settingValue}>Warm</Text>
        </View>
      </View>

      {/* Sign out */}
      <TouchableOpacity style={styles.signOutButton} onPress={signOut}>
        <Text style={styles.signOutText}>Sign Out</Text>
      </TouchableOpacity>

      <Text style={styles.version}>{brand.name} v1.0.0</Text>
    </ScrollView>
  )
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.cream },
  content: { padding: 20, paddingBottom: 40 },
  card: {
    backgroundColor: colors.white,
    borderRadius: 16,
    padding: 20,
    marginBottom: 12,
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
    elevation: 2,
  },
  avatar: {
    width: 64,
    height: 64,
    borderRadius: 32,
    backgroundColor: colors.blue,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 12,
  },
  avatarText: { fontSize: 24, fontWeight: '700', color: colors.white },
  name: { fontSize: 18, fontWeight: '700', color: colors.gray900 },
  email: { fontSize: 14, color: colors.gray500, marginTop: 2 },
  sectionTitle: { fontSize: 13, fontWeight: '700', color: colors.gray500, textTransform: 'uppercase', letterSpacing: 0.5, alignSelf: 'flex-start', marginBottom: 12 },
  settingRow: { flexDirection: 'row', justifyContent: 'space-between', width: '100%', paddingVertical: 10, borderTopWidth: 1, borderTopColor: colors.gray100 },
  settingLabel: { fontSize: 15, color: colors.gray700 },
  settingValue: { fontSize: 15, color: colors.gray500 },
  signOutButton: { backgroundColor: colors.white, borderRadius: 12, padding: 14, alignItems: 'center', marginTop: 8, borderWidth: 1, borderColor: colors.gray200 },
  signOutText: { fontSize: 15, fontWeight: '600', color: colors.rose },
  version: { fontSize: 12, color: colors.gray400, textAlign: 'center', marginTop: 20 },
})
