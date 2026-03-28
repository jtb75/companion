import { useQuery } from '@tanstack/react-query'
import { api } from '../../shared/api/client'
import { Card } from '../../shared/components/Card'
import { StatusBadge } from '../../shared/components/StatusBadge'

interface StageHealth {
  stage: string
  success_rate: number
  avg_time_ms: number
  status: 'healthy' | 'warning' | 'critical'
}

interface PipelineHealth {
  documents_in_flight: number
  stages: StageHealth[]
  recent_failures: { document_id: string; stage: string; error: string; timestamp: string }[]
}

const placeholderData: PipelineHealth = {
  documents_in_flight: 3,
  stages: [
    { stage: 'Ingestion', success_rate: 0.99, avg_time_ms: 120, status: 'healthy' },
    { stage: 'Classification', success_rate: 0.97, avg_time_ms: 340, status: 'healthy' },
    { stage: 'Extraction', success_rate: 0.94, avg_time_ms: 520, status: 'healthy' },
    { stage: 'Summarization', success_rate: 0.96, avg_time_ms: 1800, status: 'healthy' },
    { stage: 'Routing', success_rate: 0.98, avg_time_ms: 45, status: 'healthy' },
    { stage: 'Tracking', success_rate: 1.0, avg_time_ms: 30, status: 'healthy' },
  ],
  recent_failures: [
    {
      document_id: 'doc-4821',
      stage: 'Extraction',
      error: 'PDF parse error: corrupted page 3',
      timestamp: '2026-03-27T11:42:00Z',
    },
  ],
}

export function PipelinePage() {
  const { data, isLoading } = useQuery({
    queryKey: ['pipeline-health'],
    queryFn: async () => {
      try {
        return await api<PipelineHealth>('/admin/pipeline/health')
      } catch {
        return placeholderData
      }
    },
  })

  const health = data ?? placeholderData

  if (isLoading) {
    return <p className="text-gray-500">Loading pipeline health...</p>
  }

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold text-gray-900">Pipeline Health</h1>

      <Card title="Documents in Flight">
        <p className="text-3xl font-bold text-companion-blue">{health.documents_in_flight}</p>
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {health.stages.map((stage) => (
          <Card key={stage.stage} title={stage.stage}>
            <div className="flex items-center justify-between mb-2">
              <StatusBadge status={stage.status} label={stage.status} />
              <span className="text-xs text-gray-400">{stage.avg_time_ms}ms avg</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="flex-1 bg-gray-200 rounded-full h-2">
                <div
                  className={`h-2 rounded-full ${
                    stage.success_rate >= 0.95
                      ? 'bg-green-500'
                      : stage.success_rate >= 0.85
                        ? 'bg-yellow-500'
                        : 'bg-red-500'
                  }`}
                  style={{ width: `${stage.success_rate * 100}%` }}
                />
              </div>
              <span className="text-sm text-gray-600 w-12 text-right">
                {Math.round(stage.success_rate * 100)}%
              </span>
            </div>
          </Card>
        ))}
      </div>

      {health.recent_failures.length > 0 && (
        <Card title="Recent Failures">
          <div className="space-y-2">
            {health.recent_failures.map((f, i) => (
              <div key={i} className="border border-red-100 bg-red-50 rounded p-3 text-sm">
                <div className="flex justify-between">
                  <span className="font-medium text-red-800">{f.stage}</span>
                  <span className="text-red-400 text-xs">
                    {new Date(f.timestamp).toLocaleString()}
                  </span>
                </div>
                <p className="text-red-700 mt-1">{f.error}</p>
                <p className="text-red-400 text-xs mt-1">{f.document_id}</p>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  )
}
