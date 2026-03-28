import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../../shared/api/client'
import { Card } from '../../shared/components/Card'

interface ThresholdConfig {
  classification_confidence: number
  junk_cutoff: number
}

const placeholderThresholds: ThresholdConfig = {
  classification_confidence: 0.85,
  junk_cutoff: 0.3,
}

export function ThresholdsPage() {
  const queryClient = useQueryClient()
  const [values, setValues] = useState<ThresholdConfig | null>(null)
  const [saveStatus, setSaveStatus] = useState<string | null>(null)

  const { data: config, isLoading } = useQuery({
    queryKey: ['config-pipeline-threshold'],
    queryFn: async () => {
      try {
        const entries = await api<{ key: string; value: string }[]>(
          '/admin/config?category=pipeline_threshold'
        )
        const obj: Record<string, number> = {}
        for (const e of entries) {
          obj[e.key] = parseFloat(e.value)
        }
        return {
          classification_confidence: obj.classification_confidence ?? placeholderThresholds.classification_confidence,
          junk_cutoff: obj.junk_cutoff ?? placeholderThresholds.junk_cutoff,
        }
      } catch {
        return placeholderThresholds
      }
    },
  })

  const thresholds = values ?? config ?? placeholderThresholds

  const mutation = useMutation({
    mutationFn: async (vals: ThresholdConfig) => {
      await Promise.all([
        api('/admin/config', {
          method: 'PATCH',
          body: JSON.stringify({
            category: 'pipeline_threshold',
            key: 'classification_confidence',
            value: String(vals.classification_confidence),
          }),
        }),
        api('/admin/config', {
          method: 'PATCH',
          body: JSON.stringify({
            category: 'pipeline_threshold',
            key: 'junk_cutoff',
            value: String(vals.junk_cutoff),
          }),
        }),
      ])
    },
    onSuccess: () => {
      setSaveStatus('Saved successfully')
      queryClient.invalidateQueries({ queryKey: ['config-pipeline-threshold'] })
      setTimeout(() => setSaveStatus(null), 3000)
    },
    onError: () => {
      setSaveStatus('Failed to save (API may not be connected)')
      setTimeout(() => setSaveStatus(null), 3000)
    },
  })

  if (isLoading) {
    return <p className="text-gray-500">Loading thresholds...</p>
  }

  const update = (key: keyof ThresholdConfig, val: number) => {
    setValues({ ...thresholds, [key]: val })
  }

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold text-gray-900">Pipeline Thresholds</h1>

      <Card title="Classification Confidence" subtitle="Minimum confidence to accept a classification result">
        <div className="flex items-center gap-4">
          <input
            type="range"
            min="0"
            max="1"
            step="0.01"
            value={thresholds.classification_confidence}
            onChange={(e) => update('classification_confidence', parseFloat(e.target.value))}
            className="flex-1"
          />
          <span className="text-sm font-mono w-12 text-right text-gray-700">
            {thresholds.classification_confidence.toFixed(2)}
          </span>
        </div>
      </Card>

      <Card title="Junk Cutoff" subtitle="Score below which documents are classified as junk">
        <div className="flex items-center gap-4">
          <input
            type="range"
            min="0"
            max="1"
            step="0.01"
            value={thresholds.junk_cutoff}
            onChange={(e) => update('junk_cutoff', parseFloat(e.target.value))}
            className="flex-1"
          />
          <span className="text-sm font-mono w-12 text-right text-gray-700">
            {thresholds.junk_cutoff.toFixed(2)}
          </span>
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
          onClick={() => mutation.mutate(thresholds)}
          disabled={mutation.isPending || values === null}
          className="px-4 py-2 bg-companion-blue text-white rounded-lg text-sm font-medium hover:bg-companion-blue-mid disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {mutation.isPending ? 'Saving...' : 'Save Thresholds'}
        </button>
      </div>
    </div>
  )
}
