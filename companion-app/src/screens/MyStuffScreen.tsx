import React, { useState } from 'react'
import { View, Text, ScrollView, TouchableOpacity, StyleSheet, ActivityIndicator } from 'react-native'
import { api } from '../api/client'
import { colors } from '../theme/colors'
import { ScanButton } from '../components/ScanButton'
import { TodoCheckbox } from '../components/TodoCheckbox'

type Tab = 'meds' | 'appointments' | 'bills' | 'todos'

export function MyStuffScreen() {
  const [tab, setTab] = useState<Tab>('meds')
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(false)

  const tabs: { key: Tab; label: string; endpoint: string }[] = [
    { key: 'meds', label: 'Meds', endpoint: '/api/v1/medications' },
    { key: 'appointments', label: 'Appts', endpoint: '/api/v1/appointments' },
    { key: 'bills', label: 'Bills', endpoint: '/api/v1/bills' },
    { key: 'todos', label: 'To Do', endpoint: '/api/v1/todos' },
  ]

  React.useEffect(() => {
    loadTab(tab)
  }, [tab])

  const loadTab = async (t: Tab) => {
    setLoading(true)
    try {
      const endpoint = tabs.find((tb) => tb.key === t)!.endpoint
      const res = await api<any>(endpoint)
      setData(res)
    } catch {
      setData(null)
    } finally {
      setLoading(false)
    }
  }

  const handleToggleTodo = async (todoId: string) => {
    try {
      // Optimistic update
      setData((prev: any) => {
        if (!prev || !prev.todos) return prev
        return {
          ...prev,
          todos: prev.todos.map((t: any) =>
            t.id === todoId ? { ...t, completed_at: new Date().toISOString() } : t
          ),
        }
      })
      await api(`/api/v1/todos/${todoId}/complete`, { method: 'POST' })
    } catch (err) {
      // Revert on failure
      loadTab('todos')
    }
  }

  const renderContent = () => {
    if (loading) return <ActivityIndicator size="large" color={colors.blue} style={{ marginTop: 40 }} />
    if (!data) return <Text style={styles.empty}>Unable to load data</Text>

    const items = data.medications || data.appointments || data.bills || data.todos || []
    if (items.length === 0) return <Text style={styles.empty}>Nothing here yet</Text>

    return items.map((item: any, i: number) => (
      <View key={item.id || i} style={styles.card}>
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: 12 }}>
          {tab === 'todos' && (
            <TodoCheckbox
              completed={!!item.completed_at}
              onPress={() => handleToggleTodo(item.id)}
              size={20}
            />
          )}
          <View style={{ flex: 1 }}>
            <Text style={[styles.itemTitle, tab === 'todos' && !!item.completed_at && styles.completedText]}>
              {item.name || item.provider_name || item.sender || item.title}
            </Text>
            {item.dosage && <Text style={styles.itemSub}>{item.dosage} - {item.frequency}</Text>}
            {item.appointment_at && (
              <Text style={styles.itemSub}>
                {new Date(item.appointment_at).toLocaleDateString()} at{' '}
                {new Date(item.appointment_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </Text>
            )}
            {item.amount && <Text style={styles.itemSub}>${item.amount} due {new Date(item.due_date).toLocaleDateString()}</Text>}
            {item.description && !item.amount && <Text style={styles.itemSub}>{item.description}</Text>}
          </View>
        </View>
      </View>
    ))
  }

  return (
    <View style={styles.container}>
      {/* Tab bar */}
      <View style={styles.tabBar}>
        {tabs.map((t) => (
          <TouchableOpacity
            key={t.key}
            style={[styles.tab, tab === t.key && styles.tabActive]}
            onPress={() => setTab(t.key)}
          >
            <Text style={[styles.tabText, tab === t.key && styles.tabTextActive]}>{t.label}</Text>
          </TouchableOpacity>
        ))}
      </View>

      <ScrollView contentContainerStyle={styles.content}>
        {renderContent()}
      </ScrollView>
      <ScanButton />
    </View>
  )
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.cream },
  tabBar: { flexDirection: 'row', backgroundColor: colors.white, borderBottomWidth: 1, borderBottomColor: colors.gray200, paddingHorizontal: 4 },
  tab: { flex: 1, paddingVertical: 12, alignItems: 'center' },
  tabActive: { borderBottomWidth: 2, borderBottomColor: colors.blue },
  tabText: { fontSize: 14, fontWeight: '500', color: colors.gray500 },
  tabTextActive: { color: colors.blue, fontWeight: '700' },
  content: { padding: 16, paddingBottom: 40 },
  card: {
    backgroundColor: colors.white,
    borderRadius: 12,
    padding: 14,
    marginBottom: 8,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.04,
    shadowRadius: 3,
    elevation: 1,
  },
  itemTitle: { fontSize: 15, fontWeight: '600', color: colors.gray800 },
  completedText: { textDecorationLine: 'line-through', color: colors.gray400 },
  itemSub: { fontSize: 13, color: colors.gray500, marginTop: 3 },
  empty: { fontSize: 15, color: colors.gray400, textAlign: 'center', marginTop: 40 },
})
