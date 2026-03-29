import { useQuery } from '@tanstack/react-query'
import { api } from '../../shared/api/client'

interface ActivityEntry {
  id: string
  action: string
  timestamp: string
}

const placeholderActivity: ActivityEntry[] = [
  { id: '1', action: 'You viewed the dashboard', timestamp: '2026-03-27T14:15:00Z' },
  { id: '2', action: 'You checked medication adherence', timestamp: '2026-03-27T10:30:00Z' },
  { id: '3', action: 'You reviewed upcoming bills', timestamp: '2026-03-26T16:45:00Z' },
]

interface Props {
  userId: string
}

export function ActivityPage({ userId }: Props) {
  const { data: activity, isLoading } = useQuery({
    queryKey: ['caregiver-activity', userId],
    queryFn: async () => {
      try {
        return await api<ActivityEntry[]>(`/api/v1/caregiver/activity?user_id=${userId}`)
      } catch {
        return placeholderActivity
      }
    },
    enabled: !!userId,
  })

  const entries = Array.isArray(activity) ? activity : placeholderActivity

  if (isLoading) {
    return <p className="text-gray-500">Loading activity...</p>
  }

  return (
    <div>
      <h1 className="text-xl font-semibold text-gray-900 mb-4">Your Activity</h1>
      {entries.length === 0 ? (
        <p className="text-gray-500">No activity recorded yet.</p>
      ) : (
        <ul className="space-y-2">
          {entries.map((entry) => {
            const dt = new Date(entry.timestamp)
            const formatted = dt.toLocaleDateString('en-US', {
              month: 'long',
              day: 'numeric',
            }) + ' at ' + dt.toLocaleTimeString('en-US', {
              hour: 'numeric',
              minute: '2-digit',
            })
            return (
              <li
                key={entry.id}
                className="bg-white border border-gray-200 rounded-lg px-4 py-3 text-sm text-gray-700 shadow-sm"
              >
                {entry.action} on {formatted}.
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}
