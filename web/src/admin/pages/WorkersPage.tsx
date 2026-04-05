import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { api } from '../../shared/api/client'
import { Card } from '../../shared/components/Card'

interface WorkerResult {
  triggered: boolean
  [key: string]: unknown
}

interface Person {
  id: string
  first_name: string
  email: string
  is_user: boolean
  account_status: string
}

export function WorkersPage() {
  const [lastResult, setLastResult] = useState<string | null>(null)
  const [selectedUser, setSelectedUser] = useState<string>('')
  const [runningPath, setRunningPath] = useState<string | null>(null)

  // Fetch users for the picker
  const { data: people } = useQuery({
    queryKey: ['admin-people-workers'],
    queryFn: async () => {
      const res = await api<{ people: Person[] }>('/admin/people')
      return res.people.filter((p) => p.is_user && p.account_status === 'active')
    },
  })

  const runWorker = async (path: string) => {
    setRunningPath(path)
    setLastResult(null)
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), 60000)
    try {
      const url = selectedUser ? `${path}?user_id=${selectedUser}` : path
      const data = await api<WorkerResult>(`/admin/workers${url}`, {
        method: 'POST',
        signal: controller.signal,
      })
      setLastResult(JSON.stringify(data, null, 2))
    } catch (err: any) {
      if (err.name === 'AbortError') {
        setLastResult('Error: Request timed out after 60s. Worker may still be running.')
      } else {
        setLastResult(`Error: ${err.message || 'Worker trigger failed'}`)
      }
    } finally {
      clearTimeout(timeoutId)
      setRunningPath(null)
    }
  }

  const WorkerButton = ({
    label,
    path,
    description,
    danger = false,
    supportsUser = false,
  }: {
    label: string
    path: string
    description: string
    danger?: boolean
    supportsUser?: boolean
  }) => (
    <div className="flex items-center justify-between gap-3 p-3 bg-gray-50 rounded-lg border border-gray-200">
      <div className="space-y-0.5 flex-1 min-w-0">
        <h3 className="text-sm font-medium text-gray-900">{label}</h3>
        <p className="text-[11px] text-gray-500">{description}</p>
      </div>
      <div className="flex items-center gap-2 shrink-0">
        {supportsUser && selectedUser && (
          <span className="text-[10px] text-companion-blue bg-companion-blue/10 px-2 py-0.5 rounded-full">
            1 user
          </span>
        )}
        <button
          onClick={() => runWorker(path)}
          disabled={runningPath !== null}
          className={`px-3 py-1.5 rounded-lg text-xs font-medium transition ${
            danger
              ? 'bg-red-600 text-white hover:bg-red-700'
              : 'bg-companion-blue text-white hover:bg-companion-blue-mid'
          } disabled:opacity-50`}
        >
          {runningPath === path ? 'Running...' : 'Run'}
        </button>
      </div>
    </div>
  )

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-900">Background Workers</h1>
      </div>

      {/* User scope picker */}
      <div className="flex items-center gap-3 rounded-lg border border-gray-200 bg-white px-4 py-3">
        <label className="text-xs font-medium text-gray-500 whitespace-nowrap">Target:</label>
        <select
          value={selectedUser}
          onChange={(e) => setSelectedUser(e.target.value)}
          className="flex-1 rounded-md border border-gray-300 px-3 py-1.5 text-sm"
        >
          <option value="">All users (batch)</option>
          {people?.map((p) => (
            <option key={p.id} value={p.id}>
              {p.first_name} — {p.email}
            </option>
          ))}
        </select>
        {selectedUser && (
          <button
            onClick={() => setSelectedUser('')}
            className="text-xs text-gray-400 hover:text-gray-600"
          >
            Clear
          </button>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="space-y-6">
          <Card title="Notifications" subtitle="Trigger push notifications and check-ins">
            <div className="space-y-3">
              <WorkerButton
                label="Morning Check-in"
                path="/morning-checkin"
                description="Send personalized LLM briefing with today's appointments, meds, and bills."
                supportsUser
              />
              <WorkerButton
                label="Medication Reminders"
                path="/medication-reminders"
                description="Check medication schedules and send reminders for due doses."
                supportsUser
              />
              <WorkerButton
                label="Escalation Check"
                path="/escalation"
                description="Scan for unanswered questions that need caregiver attention."
              />
            </div>
          </Card>

          <Card title="Maintenance" subtitle="System cleanup and recovery">
            <div className="space-y-3">
              <WorkerButton
                label="Reprocess Documents"
                path="/reprocess-documents"
                description="Retry documents stuck in RECEIVED or PROCESSING status."
              />
              <WorkerButton
                label="Data Retention"
                path="/retention"
                description="Process document retention phases (Full → Metadata Only)."
              />
              <WorkerButton
                label="Hard Deletion"
                path="/deletion"
                description="Permanently delete accounts scheduled for removal."
                danger
              />
            </div>
          </Card>
        </div>

        <div>
          <Card title="Worker Console" subtitle="Output from last triggered worker">
            {lastResult ? (
              <pre className="p-4 bg-gray-900 text-green-400 font-mono text-[11px] rounded-lg overflow-auto max-h-[500px] whitespace-pre-wrap">
                {lastResult}
              </pre>
            ) : (
              <div className="flex flex-col items-center justify-center h-[200px] text-gray-400 italic text-sm">
                No worker activity in this session.
              </div>
            )}
          </Card>
        </div>
      </div>
    </div>
  )
}
