import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { api } from '../../shared/api/client'
import { Card } from '../../shared/components/Card'

interface WorkerResult {
  triggered: boolean
  triggered_count?: number
  total_users?: number
  reprocessed?: number
  results?: any[]
}

export function WorkersPage() {
  const [lastResult, setLastResult] = useState<string | null>(null)

  const mutation = useMutation({
    mutationFn: async (path: string) => {
      return await api<WorkerResult>(`/admin/workers${path}`, { method: 'POST' })
    },
    onSuccess: (data) => {
      setLastResult(JSON.stringify(data, null, 2))
    },
    onError: (err: any) => {
      setLastResult(`Error: ${err.message || 'Worker trigger failed'}`)
    },
  })

  const WorkerButton = ({ 
    label, 
    path, 
    description, 
    danger = false 
  }: { 
    label: string; 
    path: string; 
    description: string;
    danger?: boolean
  }) => (
    <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg border border-gray-200">
      <div className="space-y-1">
        <h3 className="text-sm font-medium text-gray-900">{label}</h3>
        <p className="text-xs text-gray-500">{description}</p>
      </div>
      <button
        onClick={() => mutation.mutate(path)}
        disabled={mutation.isPending}
        className={`px-4 py-2 rounded-lg text-sm font-medium transition ${
          danger 
            ? 'bg-red-600 text-white hover:bg-red-700' 
            : 'bg-companion-blue text-white hover:bg-companion-blue-mid'
        } disabled:opacity-50`}
      >
        {mutation.isPending ? 'Running...' : 'Trigger'}
      </button>
    </div>
  )

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-900">Background Workers</h1>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="space-y-6">
          <Card title="Scheduled Tasks" subtitle="Manually fire daily or periodic workers">
            <div className="space-y-4">
              <WorkerButton 
                label="Morning Check-in" 
                path="/morning-checkin" 
                description="Trigger daily greetings and LLM briefings for all users immediately."
              />
              <WorkerButton 
                label="Escalation Check" 
                path="/escalation" 
                description="Scan for unanswered questions that need caregiver attention."
              />
              <WorkerButton 
                label="Data Retention" 
                path="/retention" 
                description="Process document retention phases (Full -> Metadata Only)."
              />
            </div>
          </Card>

          <Card title="Maintenance" subtitle="Clean up or retry system processes">
            <div className="space-y-4">
              <WorkerButton 
                label="Reprocess Documents" 
                path="/reprocess-documents" 
                description="Find documents stuck in processing and retry the full pipeline."
              />
              <WorkerButton 
                label="Hard Deletion" 
                path="/deletion" 
                description="Permanently wipe records marked for deletion from the database."
                danger
              />
            </div>
          </Card>
        </div>

        <div className="space-y-6">
          <Card title="Worker Console" subtitle="Results from the last triggered worker">
            {lastResult ? (
              <pre className="p-4 bg-gray-900 text-green-400 font-mono text-xs rounded-lg overflow-auto max-h-[400px]">
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
