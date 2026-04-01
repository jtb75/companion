import { useState, useEffect, useRef, useCallback } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../../shared/api/client'
import { auth } from '../../shared/auth/firebase'
import { Card } from '../../shared/components/Card'
import { StatusBadge } from '../../shared/components/StatusBadge'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface PipelineStage {
  stage: string
  status: 'completed' | 'in_progress' | 'pending' | 'failed'
  duration_ms?: number
}

interface PipelineDocument {
  id: string
  user_name: string
  user_email: string
  source_channel: string
  status: string
  classification: string | null
  urgency_level: string | null
  card_summary: string | null
  created_at: string
  processed_at: string | null
  pipeline_stages: PipelineStage[]
}

interface DocumentsResponse {
  documents: PipelineDocument[]
  total: number
}

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

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

type StatusFilter = 'all' | 'processing' | 'completed' | 'failed'

const PIPELINE_STAGE_ORDER = [
  'Ingestion',
  'Classification',
  'Extraction',
  'Summarization',
  'Embedding',
  'Routing',
]

const API_BASE = import.meta.env.VITE_API_BASE_URL || ''

const placeholderHealth: PipelineHealth = {
  documents_in_flight: 0,
  stages: [
    { stage: 'Ingestion', success_rate: 0.99, avg_time_ms: 120, status: 'healthy' },
    { stage: 'Classification', success_rate: 0.97, avg_time_ms: 340, status: 'healthy' },
    { stage: 'Extraction', success_rate: 0.94, avg_time_ms: 520, status: 'healthy' },
    { stage: 'Summarization', success_rate: 0.96, avg_time_ms: 1800, status: 'healthy' },
    { stage: 'Routing', success_rate: 0.98, avg_time_ms: 45, status: 'healthy' },
    { stage: 'Tracking', success_rate: 1.0, avg_time_ms: 30, status: 'healthy' },
  ],
  recent_failures: [],
}

// ---------------------------------------------------------------------------
// Pipeline Stepper
// ---------------------------------------------------------------------------

function PipelineStepper({ stages }: { stages: PipelineStage[] }) {
  // Build a map of stage status from the document's pipeline_stages
  const stageMap = new Map<string, PipelineStage>()
  stages.forEach((s) => stageMap.set(s.stage, s))

  return (
    <div className="flex items-center gap-0">
      {PIPELINE_STAGE_ORDER.map((name, i) => {
        const stage = stageMap.get(name)
        const status = stage?.status ?? 'pending'

        return (
          <div key={name} className="flex items-center">
            {/* Connector line */}
            {i > 0 && (
              <div
                className={`h-0.5 w-6 sm:w-8 ${
                  status === 'completed' ? 'bg-emerald-400' : 'bg-gray-200'
                }`}
              />
            )}
            {/* Stage dot + label */}
            <div className="flex flex-col items-center">
              <div
                className={`flex h-7 w-7 items-center justify-center rounded-full border-2 text-xs font-bold transition-all ${
                  status === 'completed'
                    ? 'border-emerald-500 bg-emerald-500 text-white'
                    : status === 'in_progress'
                      ? 'border-companion-blue bg-companion-blue/10 text-companion-blue animate-pulse'
                      : status === 'failed'
                        ? 'border-rose-500 bg-rose-500 text-white'
                        : 'border-gray-300 bg-white text-gray-300'
                }`}
              >
                {status === 'completed' ? (
                  <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" strokeWidth={3} stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                  </svg>
                ) : status === 'failed' ? (
                  <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" strokeWidth={3} stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                  </svg>
                ) : status === 'in_progress' ? (
                  <div className="h-2 w-2 rounded-full bg-companion-blue" />
                ) : (
                  <div className="h-2 w-2 rounded-full bg-gray-300" />
                )}
              </div>
              <span
                className={`mt-1 text-[10px] leading-tight whitespace-nowrap ${
                  status === 'completed'
                    ? 'text-emerald-600 font-medium'
                    : status === 'in_progress'
                      ? 'text-companion-blue font-medium'
                      : status === 'failed'
                        ? 'text-rose-600 font-medium'
                        : 'text-gray-400'
                }`}
              >
                {name}
              </span>
            </div>
          </div>
        )
      })}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Document Card
// ---------------------------------------------------------------------------

function DocumentCard({
  doc,
  onCancel,
  onResubmit,
}: {
  doc: PipelineDocument
  onCancel: (id: string) => void
  onResubmit: (id: string) => void
}) {
  const sourceLabel = doc.source_channel === 'camera_scan' ? 'Camera Scan' : doc.source_channel === 'email' ? 'Email' : doc.source_channel || 'Unknown'
  const uploadTime = new Date(doc.created_at).toLocaleString()

  const urgencyColors: Record<string, string> = {
    high: 'bg-rose-100 text-rose-800',
    medium: 'bg-amber-100 text-amber-800',
    low: 'bg-emerald-100 text-emerald-800',
  }

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
      <div className="flex flex-col lg:flex-row lg:items-center gap-4">
        {/* Left: Member info */}
        <div className="min-w-0 shrink-0 lg:w-48">
          <p className="text-sm font-semibold text-gray-900 truncate">{doc.user_name}</p>
          <p className="text-xs text-gray-500 truncate">{doc.user_email}</p>
          <div className="mt-1 flex items-center gap-2">
            <span className="inline-flex items-center rounded-full bg-gray-100 px-2 py-0.5 text-[10px] font-medium text-gray-600">
              {sourceLabel}
            </span>
            <span className="text-[10px] text-gray-400">{uploadTime}</span>
          </div>
        </div>

        {/* Center: Stepper */}
        <div className="flex-1 flex justify-center overflow-x-auto">
          <PipelineStepper stages={doc.pipeline_stages ?? []} />
        </div>

        {/* Right: Badges + summary */}
        <div className="shrink-0 lg:w-52 flex flex-col gap-1.5 items-end">
          <div className="flex items-center gap-1.5 flex-wrap justify-end">
            {doc.classification && (
              <span className="inline-flex items-center rounded-full bg-sky-100 px-2.5 py-0.5 text-xs font-medium text-sky-800">
                {doc.classification}
              </span>
            )}
            {doc.urgency_level && (
              <span
                className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${urgencyColors[doc.urgency_level] || 'bg-gray-100 text-gray-700'}`}
              >
                {doc.urgency_level}
              </span>
            )}
          </div>
          {doc.card_summary && (
            <p className="text-xs text-gray-500 text-right line-clamp-2">{doc.card_summary}</p>
          )}
        </div>
      </div>

      {/* Bottom actions */}
      <div className="mt-3 flex items-center justify-end gap-2 border-t border-gray-100 pt-3">
        <button
          onClick={() => onCancel(doc.id)}
          className="rounded-md border border-rose-300 px-3 py-1 text-xs font-medium text-rose-600 hover:bg-rose-50 transition-colors"
        >
          Cancel
        </button>
        <button
          onClick={() => onResubmit(doc.id)}
          className="rounded-md border border-companion-blue px-3 py-1 text-xs font-medium text-companion-blue hover:bg-companion-blue/5 transition-colors"
        >
          Resubmit
        </button>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// WebSocket Hook
// ---------------------------------------------------------------------------

function usePipelineWebSocket(
  onMessage: (data: PipelineDocument) => void,
) {
  const [connected, setConnected] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimer = useRef<ReturnType<typeof setTimeout>>()
  const onMessageRef = useRef(onMessage)
  onMessageRef.current = onMessage

  const connect = useCallback(async () => {
    try {
      const user = auth.currentUser
      if (!user) return
      const token = await user.getIdToken()
      const wsBase = API_BASE.replace(/^https:\/\//, 'wss://').replace(/^http:\/\//, 'ws://')
      const url = `${wsBase}/ws/pipeline?token=${token}`

      const ws = new WebSocket(url)
      wsRef.current = ws

      ws.onopen = () => setConnected(true)

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data) as PipelineDocument
          onMessageRef.current(data)
        } catch {
          // ignore malformed messages
        }
      }

      ws.onclose = () => {
        setConnected(false)
        reconnectTimer.current = setTimeout(() => connect(), 3000)
      }

      ws.onerror = () => {
        ws.close()
      }
    } catch {
      setConnected(false)
      reconnectTimer.current = setTimeout(() => connect(), 3000)
    }
  }, [])

  useEffect(() => {
    connect()
    return () => {
      clearTimeout(reconnectTimer.current)
      wsRef.current?.close()
    }
  }, [connect])

  return connected
}

// ---------------------------------------------------------------------------
// Reprocess Button
// ---------------------------------------------------------------------------

function ReprocessButton() {
  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState<string | null>(null)
  const queryClient = useQueryClient()

  const handleReprocess = async () => {
    setBusy(true)
    setResult(null)
    try {
      const res = await api<{ reprocessed: number; results: { id: string; status: string; classification?: string; error?: string }[] }>(
        '/admin/workers/reprocess-documents',
        { method: 'POST' },
      )
      const summary = res.results
        .map((r) => (r.status === 'processed' ? `${r.classification}` : `failed: ${r.error}`))
        .join(', ')
      setResult(`${res.reprocessed} docs: ${summary}`)
      queryClient.invalidateQueries({ queryKey: ['pipeline-documents'] })
      queryClient.invalidateQueries({ queryKey: ['pipeline-health'] })
    } catch (e: any) {
      setResult(`Error: ${e.message}`)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex items-center gap-3">
      <button
        onClick={handleReprocess}
        disabled={busy}
        className="rounded-lg bg-companion-blue px-4 py-2 text-sm font-medium text-white hover:bg-companion-blue-mid disabled:opacity-50 transition-colors"
      >
        {busy ? 'Reprocessing...' : 'Reprocess Stuck'}
      </button>
      {result && <p className="text-xs text-gray-500 max-w-xs truncate">{result}</p>}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main Page
// ---------------------------------------------------------------------------

export function PipelinePage() {
  const queryClient = useQueryClient()
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all')
  const [documents, setDocuments] = useState<PipelineDocument[]>([])

  // --- Fetch documents ---
  const { data: docsData, isLoading: docsLoading } = useQuery({
    queryKey: ['pipeline-documents', statusFilter],
    queryFn: async () => {
      const params = new URLSearchParams({ limit: '50', offset: '0' })
      if (statusFilter !== 'all') params.set('status', statusFilter)
      return api<DocumentsResponse>(`/admin/documents?${params.toString()}`)
    },
  })

  // Sync fetched data into local state
  useEffect(() => {
    if (docsData?.documents) {
      setDocuments(docsData.documents)
    }
  }, [docsData])

  // --- Fetch pipeline health (stage health cards) ---
  const { data: healthData } = useQuery({
    queryKey: ['pipeline-health'],
    queryFn: async () => {
      try {
        const raw = await api<Record<string, unknown>>('/admin/pipeline/health')
        let stages: StageHealth[] = []
        if (Array.isArray(raw.stages)) {
          stages = raw.stages
        } else if (raw.stages && typeof raw.stages === 'object') {
          stages = Object.entries(raw.stages as Record<string, Record<string, unknown>>).map(
            ([name, s]) => ({
              stage: name.charAt(0).toUpperCase() + name.slice(1),
              success_rate: (s.success_rate as number) ?? 1,
              avg_time_ms: (s.avg_ms as number) ?? 0,
              status: ((s.success_rate as number) >= 0.95
                ? 'healthy'
                : (s.success_rate as number) >= 0.85
                  ? 'warning'
                  : 'critical') as StageHealth['status'],
            }),
          )
        }
        return {
          documents_in_flight: (raw.documents_in_flight as number) ?? 0,
          stages,
          recent_failures: Array.isArray(raw.recent_failures)
            ? (raw.recent_failures as PipelineHealth['recent_failures'])
            : [],
        }
      } catch {
        return placeholderHealth
      }
    },
  })

  const health = healthData ?? placeholderHealth

  // --- WebSocket for real-time updates ---
  const wsConnected = usePipelineWebSocket((updatedDoc) => {
    setDocuments((prev) => {
      // WebSocket sends stage events, not full documents
      // Match by document_id and update pipeline_stages
      const docId = updatedDoc.id
        || (updatedDoc as any).document_id
      if (!docId) return prev
      const idx = prev.findIndex((d) => d.id === docId)
      if (idx < 0) {
        // Unknown doc — refetch instead of adding broken entry
        queryClient.invalidateQueries({
          queryKey: ['pipeline-documents'],
        })
        return prev
      }
      const next = [...prev]
      const existing = { ...next[idx] }
      // If the event has stage info, update the stages
      const stage = (updatedDoc as any).stage
      const stageStatus = (updatedDoc as any).status
      if (stage && stageStatus) {
        const stages = [...(existing.pipeline_stages || [])]
        const si = stages.findIndex(
          (s) => s.stage === stage
        )
        if (si >= 0) {
          stages[si] = { ...stages[si], status: stageStatus }
        } else {
          stages.push({
            stage,
            status: stageStatus,
          })
        }
        existing.pipeline_stages = stages
      }
      // Merge any other fields from a full document update
      if (updatedDoc.status) existing.status = updatedDoc.status
      if (updatedDoc.classification) {
        existing.classification = updatedDoc.classification
      }
      if (updatedDoc.card_summary) {
        existing.card_summary = updatedDoc.card_summary
      }
      next[idx] = existing
      return next
    })
  })

  // --- Actions ---
  const handleCancel = async (id: string) => {
    if (!window.confirm('Cancel processing for this document?')) return
    try {
      await api(`/admin/documents/${id}/cancel`, { method: 'POST' })
      queryClient.invalidateQueries({ queryKey: ['pipeline-documents'] })
    } catch (e: any) {
      alert(`Failed to cancel: ${e.message}`)
    }
  }

  const handleResubmit = async (id: string) => {
    if (!window.confirm('Resubmit this document for processing?')) return
    try {
      await api(`/admin/documents/${id}/resubmit`, { method: 'POST' })
      queryClient.invalidateQueries({ queryKey: ['pipeline-documents'] })
    } catch (e: any) {
      alert(`Failed to resubmit: ${e.message}`)
    }
  }

  // --- Counts per status ---
  const total = docsData?.total ?? documents.length
  const countByStatus = (s: string) => documents.filter((d) => d.status === s).length

  const filters: { key: StatusFilter; label: string; count: number }[] = [
    { key: 'all', label: 'All', count: total },
    { key: 'processing', label: 'Processing', count: countByStatus('processing') },
    { key: 'completed', label: 'Completed', count: countByStatus('completed') },
    { key: 'failed', label: 'Failed', count: countByStatus('failed') },
  ]

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center gap-3">
          <h1 className="text-xl font-semibold text-gray-900">Pipeline</h1>
          {/* Live indicator */}
          <div className="flex items-center gap-1.5">
            <div
              className={`h-2 w-2 rounded-full ${wsConnected ? 'bg-emerald-500 animate-pulse' : 'bg-rose-500'}`}
            />
            <span className={`text-xs font-medium ${wsConnected ? 'text-emerald-600' : 'text-rose-600'}`}>
              {wsConnected ? 'Live' : 'Disconnected'}
            </span>
          </div>
        </div>
        <ReprocessButton />
      </div>

      {/* Pill filters */}
      <div className="flex items-center gap-2 flex-wrap">
        {filters.map(({ key, label, count }) => (
          <button
            key={key}
            onClick={() => setStatusFilter(key)}
            className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium ring-1 transition-colors ${
              statusFilter === key
                ? key === 'failed'
                  ? 'bg-rose-100 text-rose-800 ring-rose-300'
                  : key === 'processing'
                    ? 'bg-sky-100 text-sky-800 ring-sky-300'
                    : key === 'completed'
                      ? 'bg-emerald-100 text-emerald-800 ring-emerald-300'
                      : 'bg-companion-blue/10 text-companion-blue ring-companion-blue/30'
                : 'bg-white text-gray-500 ring-gray-200 hover:bg-gray-50'
            }`}
          >
            {label}
            <span className={`${statusFilter === key ? 'opacity-70' : 'text-gray-400'}`}>
              {count}
            </span>
          </button>
        ))}
      </div>

      {/* Document list */}
      {docsLoading ? (
        <p className="text-gray-500">Loading documents...</p>
      ) : documents.length === 0 ? (
        <div className="rounded-lg border border-gray-200 bg-white p-8 text-center text-sm text-gray-500">
          No documents found.
        </div>
      ) : (
        <div className="space-y-3">
          {documents.map((doc) => (
            <DocumentCard
              key={doc.id}
              doc={doc}
              onCancel={handleCancel}
              onResubmit={handleResubmit}
            />
          ))}
        </div>
      )}

      {/* Stage health cards */}
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

      {/* Recent failures */}
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
