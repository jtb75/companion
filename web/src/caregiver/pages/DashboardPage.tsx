import { useQuery } from '@tanstack/react-query'
import { api } from '../../shared/api/client'
import { Card } from '../../shared/components/Card'
import { StatusBadge } from '../../shared/components/StatusBadge'

interface DashboardData {
  status: 'managing_well' | 'needs_attention'
  tasks: { completed: number; total: number }
  medication_adherence: number
  upcoming_bills: { description: string; due_date: string; amount: string }[]
  upcoming_appointments: { description: string; date: string }[]
}

const placeholderData: DashboardData = {
  status: 'managing_well',
  tasks: { completed: 4, total: 5 },
  medication_adherence: 0.92,
  upcoming_bills: [
    { description: 'Electric bill', due_date: '2026-04-01', amount: '$142.50' },
    { description: 'Internet', due_date: '2026-04-05', amount: '$65.00' },
  ],
  upcoming_appointments: [
    { description: 'Dr. Chen - Annual checkup', date: '2026-04-03' },
  ],
}

interface Props {
  userId: string
}

export function DashboardPage({ userId }: Props) {
  const { data, isLoading } = useQuery({
    queryKey: ['caregiver-dashboard', userId],
    queryFn: async () => {
      try {
        return await api<DashboardData>(`/api/v1/caregiver/dashboard?user_id=${userId}`)
      } catch {
        return placeholderData
      }
    },
    enabled: !!userId,
  })

  const raw = data ?? placeholderData
  const dashboard = {
    status: raw.status ?? 'managing_well',
    tasks: raw.tasks ?? { completed: 0, total: 0 },
    medication_adherence: raw.medication_adherence ?? 0,
    upcoming_bills: Array.isArray(raw.upcoming_bills)
      ? raw.upcoming_bills : [],
    upcoming_appointments: Array.isArray(raw.upcoming_appointments)
      ? raw.upcoming_appointments : [],
  }

  if (isLoading) {
    return <p className="text-gray-500">Loading dashboard...</p>
  }

  const adherencePct = Math.round(dashboard.medication_adherence * 100)

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold text-gray-900">Caregiver Dashboard</h1>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {/* Status */}
        <Card title="Status">
          <StatusBadge
            status={dashboard.status === 'managing_well' ? 'healthy' : 'warning'}
            label={dashboard.status === 'managing_well' ? 'Managing Well' : 'Needs Attention'}
          />
        </Card>

        {/* Tasks */}
        <Card title="Tasks" subtitle={`${dashboard.tasks.completed} of ${dashboard.tasks.total} completed`}>
          <div className="w-full bg-gray-200 rounded-full h-2.5">
            <div
              className="bg-companion-sage h-2.5 rounded-full"
              style={{ width: `${dashboard.tasks.total > 0 ? (dashboard.tasks.completed / dashboard.tasks.total) * 100 : 0}%` }}
            />
          </div>
        </Card>

        {/* Medication Adherence */}
        <Card title="Medication Adherence" subtitle={`${adherencePct}%`}>
          <div className="w-full bg-gray-200 rounded-full h-2.5">
            <div
              className={`h-2.5 rounded-full ${adherencePct >= 80 ? 'bg-companion-sage' : 'bg-companion-amber'}`}
              style={{ width: `${adherencePct}%` }}
            />
          </div>
        </Card>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Upcoming Bills */}
        <Card title="Upcoming Bills">
          {dashboard.upcoming_bills.length === 0 ? (
            <p className="text-sm text-gray-500">No upcoming bills.</p>
          ) : (
            <ul className="space-y-2">
              {dashboard.upcoming_bills.map((bill, i) => (
                <li key={i} className="flex justify-between text-sm">
                  <span className="text-gray-700">{bill.description}</span>
                  <span className="text-gray-500">
                    {bill.amount} &middot; {new Date(bill.due_date).toLocaleDateString()}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </Card>

        {/* Upcoming Appointments */}
        <Card title="Upcoming Appointments">
          {dashboard.upcoming_appointments.length === 0 ? (
            <p className="text-sm text-gray-500">No upcoming appointments.</p>
          ) : (
            <ul className="space-y-2">
              {dashboard.upcoming_appointments.map((appt, i) => (
                <li key={i} className="flex justify-between text-sm">
                  <span className="text-gray-700">{appt.description}</span>
                  <span className="text-gray-500">{new Date(appt.date).toLocaleDateString()}</span>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>

      {/* Recent Documents */}
      {(raw as any).recent_documents?.length > 0 && (
        <Card title="Recent Documents">
          <ul className="space-y-3">
            {(raw as any).recent_documents.map((doc: any, i: number) => {
              const statusLabels: Record<string, { text: string; color: string }> = {
                pending: { text: 'Waiting for review', color: 'text-amber-600' },
                presented: { text: 'In review', color: 'text-blue-600' },
                confirmed: { text: 'Reviewed and added', color: 'text-green-600' },
                skipped: { text: 'Skipped', color: 'text-gray-400' },
                auto_created: { text: 'Added automatically', color: 'text-gray-500' },
              }
              const statusInfo = statusLabels[doc.review_status] || { text: doc.review_status, color: 'text-gray-500' }
              return (
                <li key={i} className="flex items-start justify-between gap-2">
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium text-gray-700 truncate">
                      {doc.card_summary || doc.source_description}
                    </p>
                    <p className="text-xs text-gray-400">
                      {doc.classification} · {doc.source_description}
                      {doc.created_at && ` · ${new Date(doc.created_at).toLocaleDateString()}`}
                    </p>
                  </div>
                  <span className={`text-xs font-medium whitespace-nowrap ${statusInfo.color}`}>
                    {statusInfo.text}
                  </span>
                </li>
              )
            })}
          </ul>
        </Card>
      )}
    </div>
  )
}
