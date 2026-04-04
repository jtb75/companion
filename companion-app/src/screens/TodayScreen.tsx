import React, { useCallback, useEffect, useState } from 'react'
import { View, Text, ScrollView, StyleSheet, TouchableOpacity, ActivityIndicator } from 'react-native'
import { useNavigation, useFocusEffect } from '@react-navigation/native'
import { api } from '../api/client'
import { colors, brand } from '../theme/colors'
import { useAuth } from '../auth/AuthProvider'
import { ScanButton } from '../components/ScanButton'
import { TodoCheckbox } from '../components/TodoCheckbox'

interface PendingReview {
  id: string
  source_description: string
  recommended_action: string
  is_urgent: boolean
  is_past_due: boolean
  is_duplicate: boolean
  card_summary: string | null
  classification: string | null
  proposed_data: Record<string, any>
}

interface TodayData {
  medications: { id: string; name: string; dosage: string; schedule: string[] }[]
  appointments: { id: string; provider_name: string; appointment_at: string }[]
  bills: { id: string; sender: string; amount: string; due_date: string }[]
  todos: { id: string; title: string; completed_at: string | null }[]
  pendingReviews: PendingReview[]
}

export function TodayScreen() {
  const { user } = useAuth()
  const navigation = useNavigation<any>()
  const [data, setData] = useState<TodayData | null>(null)
  const [loading, setLoading] = useState(true)
  const [greeting, setGreeting] = useState('')

  const handleToggleTodo = async (todoId: string) => {
    try {
      // Optimistic update
      setData((prev) => {
        if (!prev) return prev
        return {
          ...prev,
          todos: prev.todos.map((t) =>
            t.id === todoId ? { ...t, completed_at: new Date().toISOString() } : t
          ),
        }
      })
      await api(`/api/v1/todos/${todoId}/complete`, { method: 'POST' })
    } catch (err) {
      // Revert on failure
      loadData()
    }
  }

  useEffect(() => {
    const hour = new Date().getHours()
    if (hour < 12) setGreeting('Good morning')
    else if (hour < 17) setGreeting('Good afternoon')
    else setGreeting('Good evening')
  }, [])

  // Refresh data every time the screen comes into focus
  useFocusEffect(
    useCallback(() => {
      loadData()
    }, [])
  )

  const loadData = async () => {
    try {
      const [sections, meds, appts, bills, todos, reviews] = await Promise.all([
        api<any>('/api/v1/sections/today').catch(() => null),
        api<any>('/api/v1/medications').catch(() => ({ medications: [] })),
        api<any>('/api/v1/appointments').catch(() => ({ appointments: [] })),
        api<any>('/api/v1/bills').catch(() => ({ bills: [] })),
        api<any>('/api/v1/todos').catch(() => ({ todos: [] })),
        api<any>('/api/v1/reviews/pending').catch(() => ({ reviews: [] })),
      ])
      setData({
        medications: meds?.medications || [],
        appointments: appts?.appointments || [],
        bills: bills?.bills || [],
        todos: todos?.todos || [],
        pendingReviews: reviews?.reviews || [],
      })
    } catch {
      // Fallback
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color={colors.blue} />
      </View>
    )
  }

  const name = user?.displayName?.split(' ')[0] || 'there'
  const activeMeds = data?.medications?.filter((m: any) => m.is_active !== false) || []
  const upcomingAppts = data?.appointments?.slice(0, 3) || []
  const pendingTodos = data?.todos?.filter((t: any) => !t.completed_at)?.slice(0, 5) || []
  const dueBills = data?.bills?.slice(0, 3) || []

  return (
    <View style={{ flex: 1, backgroundColor: colors.cream }}>
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      {/* Greeting */}
      <View style={styles.header}>
        <Text style={styles.emoji}>{brand.emoji}</Text>
        <Text style={styles.greeting}>{greeting}, {name}</Text>
        <Text style={styles.subtitle}>Here's your day at a glance</Text>
      </View>

      {/* Mail Section */}
      {(data?.pendingReviews?.length ?? 0) > 0 && (
        <View style={styles.card}>
          <View style={styles.mailHeader}>
            <Text style={styles.mailIcon}>📬</Text>
            <Text style={styles.cardTitle}>MAIL</Text>
            <View style={styles.badge}>
              <Text style={styles.badgeText}>{data!.pendingReviews.length}</Text>
            </View>
          </View>
          {data!.pendingReviews.map((review) => {
            const sender = review.proposed_data?.sender
            const amount = review.proposed_data?.amount_due
            const title = sender || review.card_summary || 'New document'
            const subtitle = amount
              ? `$${amount}`
              : review.classification || 'Document to review'
            return (
              <TouchableOpacity
                key={review.id}
                style={[styles.mailRow, review.is_urgent && styles.mailRowUrgent]}
                onPress={() => navigation.navigate('Chat', { reviewId: review.id })}
                activeOpacity={0.7}
              >
                <View style={{ flex: 1 }}>
                  <Text style={styles.mailTitle}>{title}</Text>
                  <Text style={styles.mailSubtitle}>
                    {subtitle} · {review.source_description}
                  </Text>
                </View>
                <Text style={styles.mailArrow}>→</Text>
              </TouchableOpacity>
            )
          })}
        </View>
      )}

      {/* Medications */}
      {activeMeds.length > 0 && (
        <View style={styles.card}>
          <Text style={styles.cardTitle}>Medications</Text>
          {activeMeds.map((med: any) => (
            <View key={med.id} style={styles.row}>
              <View style={styles.dot} />
              <View style={{ flex: 1 }}>
                <Text style={styles.rowTitle}>{med.name} {med.dosage}</Text>
                <Text style={styles.rowSub}>{med.frequency}</Text>
              </View>
            </View>
          ))}
        </View>
      )}

      {/* Appointments */}
      {upcomingAppts.length > 0 && (
        <View style={styles.card}>
          <Text style={styles.cardTitle}>Upcoming Appointments</Text>
          {upcomingAppts.map((appt: any) => (
            <View key={appt.id} style={styles.row}>
              <View style={[styles.dot, { backgroundColor: colors.teal }]} />
              <View style={{ flex: 1 }}>
                <Text style={styles.rowTitle}>{appt.provider_name}</Text>
                <Text style={styles.rowSub}>
                  {new Date(appt.appointment_at).toLocaleDateString()} at{' '}
                  {new Date(appt.appointment_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </Text>
              </View>
            </View>
          ))}
        </View>
      )}

      {/* Todos */}
      {pendingTodos.length > 0 && (
        <View style={styles.card}>
          <Text style={styles.cardTitle}>To Do</Text>
          {pendingTodos.map((todo: any) => (
            <View key={todo.id} style={styles.row}>
              <TodoCheckbox
                completed={!!todo.completed_at}
                onPress={() => handleToggleTodo(todo.id)}
                size={20}
              />
              <Text style={[styles.rowTitle, !!todo.completed_at && styles.completedText]}>
                {todo.title}
              </Text>
            </View>
          ))}
        </View>
      )}

      {/* Bills */}
      {dueBills.length > 0 && (
        <View style={styles.card}>
          <Text style={styles.cardTitle}>Bills</Text>
          {dueBills.map((bill: any) => (
            <View key={bill.id} style={styles.row}>
              <View style={{ flex: 1 }}>
                <Text style={styles.rowTitle}>{bill.sender}</Text>
                <Text style={styles.rowSub}>
                  ${bill.amount} due {new Date(bill.due_date).toLocaleDateString()}
                </Text>
              </View>
            </View>
          ))}
        </View>
      )}

      {/* Empty state */}
      {!activeMeds.length && !upcomingAppts.length && !pendingTodos.length && !dueBills.length && !(data?.pendingReviews?.length) && (
        <View style={styles.card}>
          <Text style={styles.emptyText}>Nothing on your plate today. Nice!</Text>
        </View>
      )}
    </ScrollView>
    <ScanButton />
    </View>
  )
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.cream },
  content: { padding: 20, paddingBottom: 40 },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: colors.cream },
  header: { alignItems: 'center', marginBottom: 24 },
  emoji: { fontSize: 36, marginBottom: 4 },
  greeting: { fontSize: 22, fontWeight: '700', color: colors.gray900 },
  subtitle: { fontSize: 14, color: colors.gray500, marginTop: 2 },
  card: {
    backgroundColor: colors.white,
    borderRadius: 16,
    padding: 16,
    marginBottom: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
    elevation: 2,
  },
  cardTitle: { fontSize: 13, fontWeight: '700', color: colors.gray500, textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 12 },
  row: { flexDirection: 'row', alignItems: 'center', paddingVertical: 8, gap: 12 },
  dot: { width: 8, height: 8, borderRadius: 4, backgroundColor: colors.blue },
  checkbox: { width: 18, height: 18, borderRadius: 4, borderWidth: 2, borderColor: colors.gray300 },
  rowTitle: { fontSize: 15, fontWeight: '500', color: colors.gray800 },
  completedText: { textDecorationLine: 'line-through', color: colors.gray400 },
  rowSub: { fontSize: 13, color: colors.gray500, marginTop: 1 },
  emptyText: { fontSize: 15, color: colors.gray400, textAlign: 'center', paddingVertical: 20 },
  mailHeader: { flexDirection: 'row', alignItems: 'center', gap: 8, marginBottom: 12 },
  mailIcon: { fontSize: 18 },
  badge: { backgroundColor: colors.blue, borderRadius: 10, minWidth: 20, height: 20, alignItems: 'center', justifyContent: 'center', paddingHorizontal: 6 },
  badgeText: { color: colors.white, fontSize: 11, fontWeight: '700' },
  mailRow: { flexDirection: 'row', alignItems: 'center', paddingVertical: 12, borderTopWidth: 1, borderTopColor: colors.gray100 || '#f3f4f6' },
  mailRowUrgent: { backgroundColor: '#FDF3E7', marginHorizontal: -16, paddingHorizontal: 16, borderLeftWidth: 3, borderLeftColor: '#D4832A' },
  mailTitle: { fontSize: 15, fontWeight: '600', color: colors.gray800 },
  mailSubtitle: { fontSize: 13, color: colors.gray500, marginTop: 2 },
  mailArrow: { fontSize: 18, color: colors.gray400, marginLeft: 8 },
})
