import { useQuery } from '@tanstack/react-query'
import { api } from '../../shared/api/client'
import { Card } from '../../shared/components/Card'

interface EngagementData {
  active_users: number
  new_users_7d: number
}

interface OnboardingData {
  total_accounts: number
  profiles_completed: number
  completion_rate: number
  pending_invites: number
}

interface RetentionData {
  total: number
  active: number
  invited: number
  deactivated: number
  pending_deletion: number
  active_rate: number
}

interface CheckinData {
  active_medications: number
  active_caregivers: number
}

interface DocumentData {
  total: number
  by_status: Record<string, number>
  by_classification: Record<string, number>
}

export function MetricsPage() {
  const { data: engagement } = useQuery({
    queryKey: ['metrics-engagement'],
    queryFn: () => api<EngagementData>('/admin/metrics/engagement'),
  })

  const { data: onboarding } = useQuery({
    queryKey: ['metrics-onboarding'],
    queryFn: () => api<OnboardingData>('/admin/metrics/onboarding'),
  })

  const { data: retention } = useQuery({
    queryKey: ['metrics-retention'],
    queryFn: () => api<RetentionData>('/admin/metrics/retention'),
  })

  const { data: checkin } = useQuery({
    queryKey: ['metrics-checkin'],
    queryFn: () => api<CheckinData>('/admin/metrics/checkin'),
  })

  const { data: docs } = useQuery({
    queryKey: ['metrics-documents'],
    queryFn: () => api<DocumentData>('/admin/metrics/documents'),
  })

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold text-gray-900">Platform Metrics</h1>

      {/* Top-level stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card title="Active Members">
          <p className="text-3xl font-bold text-companion-blue">{engagement?.active_users ?? '-'}</p>
          <p className="text-sm text-gray-500 mt-1">account_status = active</p>
        </Card>
        <Card title="New (7d)">
          <p className="text-3xl font-bold text-companion-teal">{engagement?.new_users_7d ?? '-'}</p>
          <p className="text-sm text-gray-500 mt-1">Created this week</p>
        </Card>
        <Card title="Active Medications">
          <p className="text-3xl font-bold text-companion-sage">{checkin?.active_medications ?? '-'}</p>
          <p className="text-sm text-gray-500 mt-1">Being tracked</p>
        </Card>
        <Card title="Active Caregivers">
          <p className="text-3xl font-bold text-companion-blue">{checkin?.active_caregivers ?? '-'}</p>
          <p className="text-sm text-gray-500 mt-1">Assigned & active</p>
        </Card>
      </div>

      {/* Onboarding funnel */}
      <Card title="Onboarding" subtitle="Profile completion funnel">
        <div className="grid grid-cols-3 gap-4">
          <div>
            <p className="text-2xl font-bold text-gray-900">{onboarding?.total_accounts ?? '-'}</p>
            <p className="text-xs text-gray-500">Total accounts</p>
          </div>
          <div>
            <p className="text-2xl font-bold text-gray-900">{onboarding?.profiles_completed ?? '-'}</p>
            <p className="text-xs text-gray-500">Profiles completed</p>
          </div>
          <div>
            <p className="text-2xl font-bold text-gray-900">{onboarding?.pending_invites ?? '-'}</p>
            <p className="text-xs text-gray-500">Pending invites</p>
          </div>
        </div>
        {onboarding && onboarding.total_accounts > 0 && (
          <div className="mt-3">
            <div className="flex items-center gap-2">
              <div className="flex-1 bg-gray-200 rounded-full h-2">
                <div className="h-2 rounded-full bg-companion-blue" style={{ width: `${onboarding.completion_rate * 100}%` }} />
              </div>
              <span className="text-sm text-gray-600 w-12 text-right">{Math.round(onboarding.completion_rate * 100)}%</span>
            </div>
          </div>
        )}
      </Card>

      {/* Account status breakdown */}
      <Card title="Account Status" subtitle="Breakdown by status">
        {retention ? (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <p className="text-2xl font-bold text-emerald-600">{retention.active}</p>
              <p className="text-xs text-gray-500">Active</p>
            </div>
            <div>
              <p className="text-2xl font-bold text-amber-600">{retention.invited}</p>
              <p className="text-xs text-gray-500">Invited</p>
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-500">{retention.deactivated}</p>
              <p className="text-xs text-gray-500">Deactivated</p>
            </div>
            <div>
              <p className="text-2xl font-bold text-red-600">{retention.pending_deletion}</p>
              <p className="text-xs text-gray-500">Pending Deletion</p>
            </div>
          </div>
        ) : (
          <p className="text-sm text-gray-400">Loading...</p>
        )}
      </Card>

      {/* Documents */}
      <Card title="Documents" subtitle="Total processed documents">
        {docs ? (
          <div className="space-y-3">
            <p className="text-2xl font-bold text-gray-900">{docs.total} total</p>
            {Object.keys(docs.by_classification).length > 0 && (
              <div>
                <p className="text-xs font-bold uppercase tracking-wide text-gray-500 mb-2">By Classification</p>
                <div className="flex flex-wrap gap-2">
                  {Object.entries(docs.by_classification).map(([cls, count]) => (
                    <span key={cls} className="inline-flex items-center gap-1 rounded-full bg-gray-100 px-3 py-1 text-xs font-medium text-gray-700">
                      {cls} <span className="text-gray-400">{count}</span>
                    </span>
                  ))}
                </div>
              </div>
            )}
            {Object.keys(docs.by_status).length > 0 && (
              <div>
                <p className="text-xs font-bold uppercase tracking-wide text-gray-500 mb-2">By Status</p>
                <div className="flex flex-wrap gap-2">
                  {Object.entries(docs.by_status).map(([status, count]) => (
                    <span key={status} className="inline-flex items-center gap-1 rounded-full bg-gray-100 px-3 py-1 text-xs font-medium text-gray-700">
                      {status} <span className="text-gray-400">{count}</span>
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : (
          <p className="text-sm text-gray-400">Loading...</p>
        )}
      </Card>
    </div>
  )
}
