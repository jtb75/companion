import { useQuery } from '@tanstack/react-query'
import { api } from '../../shared/api/client'

interface Alert {
  id: string
  type: string
  message: string
  timestamp: string
}

const typeIcons: Record<string, string> = {
  medication: '\u{1F48A}',
  bill: '\u{1F4C4}',
  appointment: '\u{1F4C5}',
  safety: '\u26A0\uFE0F',
  default: '\u{1F514}',
}

export function AlertsPage() {
  const { data: alerts, isLoading, error } = useQuery({
    queryKey: ['caregiver-alerts'],
    queryFn: () => api<Alert[]>('/api/v1/caregiver/alerts'),
  })

  if (isLoading) {
    return <p className="text-gray-500">Loading alerts...</p>
  }

  if (error) {
    return <p className="text-red-500">Failed to load alerts.</p>
  }

  if (!alerts || alerts.length === 0) {
    return (
      <div className="text-center py-16">
        <p className="text-2xl text-companion-sage mb-2">All clear</p>
        <p className="text-gray-500">No alerts. Sam is managing well.</p>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      <h1 className="text-xl font-semibold text-gray-900 mb-4">Alerts</h1>
      {alerts.map((alert) => (
        <div
          key={alert.id}
          className="bg-white border border-gray-200 rounded-lg p-4 flex items-start gap-3 shadow-sm"
        >
          <span className="text-xl flex-shrink-0">
            {typeIcons[alert.type] || typeIcons.default}
          </span>
          <div className="flex-1 min-w-0">
            <p className="text-sm text-gray-900">{alert.message}</p>
            <p className="text-xs text-gray-400 mt-1">
              {new Date(alert.timestamp).toLocaleString()}
            </p>
          </div>
        </div>
      ))}
    </div>
  )
}
