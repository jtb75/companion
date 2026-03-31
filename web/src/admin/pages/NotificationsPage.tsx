import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../../shared/api/client'
import { Card } from '../../shared/components/Card'

interface NotificationSettings {
  caregiver_med_missed: boolean
  caregiver_bill_due: boolean
  caregiver_appt_reminder: boolean
  caregiver_daily_digest: boolean
  escalation_approaching: boolean
  escalation_past: boolean
  escalation_pipeline_failure: boolean
}

const defaults: NotificationSettings = {
  caregiver_med_missed: true,
  caregiver_bill_due: true,
  caregiver_appt_reminder: true,
  caregiver_daily_digest: false,
  escalation_approaching: true,
  escalation_past: true,
  escalation_pipeline_failure: true,
}

export function NotificationsPage() {
  const queryClient = useQueryClient()
  const [settings, setSettings] = useState<NotificationSettings>(defaults)
  const [configId, setConfigId] = useState<string | null>(null)
  const [saveStatus, setSaveStatus] = useState<string | null>(null)
  const [dirty, setDirty] = useState(false)

  const { isLoading } = useQuery({
    queryKey: ['config-notifications'],
    queryFn: async () => {
      try {
        const data = await api<{ entries: { id: string; key: string; value: unknown; category: string }[] }>(
          '/admin/config'
        )
        const match = data.entries.find(
          (e) => e.category.toLowerCase() === 'notification_default' && e.key === 'settings'
        )
        if (match) {
          setConfigId(match.id)
          const val = match.value as NotificationSettings
          setSettings({ ...defaults, ...val })
          return val
        }
        return defaults
      } catch {
        return defaults
      }
    },
  })

  const toggle = (key: keyof NotificationSettings) => {
    setSettings((prev) => ({ ...prev, [key]: !prev[key] }))
    setDirty(true)
  }

  const mutation = useMutation({
    mutationFn: async (vals: NotificationSettings) => {
      if (configId) {
        await api(`/admin/config/${configId}`, {
          method: 'PATCH',
          body: JSON.stringify({ value: vals, reason: 'Updated via admin dashboard' }),
        })
      } else {
        await api('/admin/config', {
          method: 'POST',
          body: JSON.stringify({
            category: 'notification_default',
            key: 'settings',
            value: vals,
            description: 'Notification toggle settings',
          }),
        })
      }
    },
    onSuccess: () => {
      setSaveStatus('Saved successfully')
      setDirty(false)
      queryClient.invalidateQueries({ queryKey: ['config-notifications'] })
      setTimeout(() => setSaveStatus(null), 3000)
    },
    onError: () => {
      setSaveStatus('Failed to save')
      setTimeout(() => setSaveStatus(null), 3000)
    },
  })

  if (isLoading) {
    return <p className="text-gray-500">Loading notification settings...</p>
  }

  const Check = ({ label, field }: { label: string; field: keyof NotificationSettings }) => (
    <label className="flex items-center gap-3">
      <input
        type="checkbox"
        checked={settings[field]}
        onChange={() => toggle(field)}
        className="rounded border-gray-300 text-companion-blue focus:ring-companion-blue-light"
      />
      <span className="text-sm text-gray-700">{label}</span>
    </label>
  )

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold text-gray-900">Notification Settings</h1>

      <Card title="Caregiver Notifications" subtitle="Configure when caregivers receive alerts">
        <div className="space-y-3">
          <Check label="Medication missed (2+ hours overdue)" field="caregiver_med_missed" />
          <Check label="Bill due within 3 days" field="caregiver_bill_due" />
          <Check label="Appointment reminder (24 hours before)" field="caregiver_appt_reminder" />
          <Check label="Daily summary digest" field="caregiver_daily_digest" />
        </div>
      </Card>

      <Card title="Escalation Notifications" subtitle="Configure when ops team gets notified">
        <div className="space-y-3">
          <Check label="Question approaching threshold (80%)" field="escalation_approaching" />
          <Check label="Question past threshold" field="escalation_past" />
          <Check label="Pipeline stage failure rate above 10%" field="escalation_pipeline_failure" />
        </div>
      </Card>

      <div className="flex items-center justify-between">
        <div>
          {saveStatus && (
            <p className={`text-sm ${saveStatus.includes('Failed') ? 'text-red-600' : 'text-green-600'}`}>
              {saveStatus}
            </p>
          )}
        </div>
        <button
          onClick={() => mutation.mutate(settings)}
          disabled={mutation.isPending || !dirty}
          className="px-4 py-2 bg-companion-blue text-white rounded-lg text-sm font-medium hover:bg-companion-blue-mid disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {mutation.isPending ? 'Saving...' : 'Save Settings'}
        </button>
      </div>
    </div>
  )
}
