import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../../shared/api/client'
import { Card } from '../../shared/components/Card'

interface ConfigEntry {
  category: string
  key: string
  value: string
  version: number
  updated_by: string
  updated_at: string
}

const placeholderPrompt: ConfigEntry = {
  category: 'arlo_persona',
  key: 'system_prompt',
  value: `You are Arlo, a warm and patient digital companion for older adults. You help with daily tasks like managing mail, paying bills, and keeping track of appointments. You speak clearly, avoid jargon, and always confirm before taking action. You are not a replacement for human connection - you are a helpful tool that makes daily life a little easier.`,
  version: 3,
  updated_by: 'admin@companion.dev',
  updated_at: '2026-03-25T10:00:00Z',
}

export function PromptsPage() {
  const queryClient = useQueryClient()
  const [editValue, setEditValue] = useState<string | null>(null)
  const [saveStatus, setSaveStatus] = useState<string | null>(null)

  const { data: config, isLoading } = useQuery({
    queryKey: ['config-arlo-persona'],
    queryFn: async () => {
      try {
        const entries = await api<ConfigEntry[]>('/admin/config?category=arlo_persona')
        return entries[0] ?? placeholderPrompt
      } catch {
        return placeholderPrompt
      }
    },
  })

  const prompt = config ?? placeholderPrompt

  const mutation = useMutation({
    mutationFn: async (value: string) => {
      await api('/admin/config', {
        method: 'PATCH',
        body: JSON.stringify({
          category: 'arlo_persona',
          key: 'system_prompt',
          value,
        }),
      })
    },
    onSuccess: () => {
      setSaveStatus('Saved successfully')
      setEditValue(null)
      queryClient.invalidateQueries({ queryKey: ['config-arlo-persona'] })
      setTimeout(() => setSaveStatus(null), 3000)
    },
    onError: () => {
      setSaveStatus('Failed to save (API may not be connected)')
      setTimeout(() => setSaveStatus(null), 3000)
    },
  })

  if (isLoading) {
    return <p className="text-gray-500">Loading prompt config...</p>
  }

  const currentValue = editValue ?? prompt.value

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold text-gray-900">Arlo Prompt Config</h1>

      <Card
        title="System Prompt"
        subtitle={`Version ${prompt.version} - Last updated by ${prompt.updated_by}`}
      >
        <textarea
          className="w-full h-64 border border-gray-300 rounded-lg p-3 text-sm font-mono text-gray-800 focus:ring-2 focus:ring-companion-blue-light focus:border-companion-blue-light"
          value={currentValue}
          onChange={(e) => setEditValue(e.target.value)}
        />
        <div className="flex items-center justify-between mt-3">
          <div>
            {saveStatus && (
              <p className={`text-sm ${saveStatus.includes('Failed') ? 'text-red-600' : 'text-green-600'}`}>
                {saveStatus}
              </p>
            )}
          </div>
          <button
            onClick={() => mutation.mutate(currentValue)}
            disabled={mutation.isPending || editValue === null}
            className="px-4 py-2 bg-companion-blue text-white rounded-lg text-sm font-medium hover:bg-companion-blue-mid disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {mutation.isPending ? 'Saving...' : 'Save'}
          </button>
        </div>
      </Card>
    </div>
  )
}
