import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../../shared/api/client'
import { Card } from '../../shared/components/Card'

interface VoiceProfile {
  id: string
  name: string
  pitch: number
  speaking_rate: number
}

const defaultVoices: VoiceProfile[] = [
  { id: 'warm', name: 'Warm', pitch: 0.0, speaking_rate: 0.9 },
  { id: 'calm', name: 'Calm', pitch: -0.5, speaking_rate: 0.8 },
  { id: 'bright', name: 'Bright', pitch: 1.0, speaking_rate: 1.0 },
  { id: 'clear', name: 'Clear', pitch: 0.0, speaking_rate: 1.1 },
]

export function VoicesPage() {
  const queryClient = useQueryClient()
  const [voices, setVoices] = useState<VoiceProfile[]>(defaultVoices)
  const [configIds, setConfigIds] = useState<Record<string, string>>({})
  const [saveStatus, setSaveStatus] = useState<string | null>(null)
  const [dirty, setDirty] = useState(false)

  const { isLoading } = useQuery({
    queryKey: ['config-voice-profiles'],
    queryFn: async () => {
      try {
        const entries = await api<{ id: string; key: string; value: string }[]>(
          '/admin/config?category=voice_profile'
        )
        if (entries.length > 0) {
          const ids: Record<string, string> = {}
          const loaded: VoiceProfile[] = entries.map((e) => {
            ids[e.key] = e.id
            const parsed = typeof e.value === 'string' ? JSON.parse(e.value) : e.value
            return {
              id: e.key,
              name: parsed.name ?? e.key,
              pitch: parsed.pitch ?? 0,
              speaking_rate: parsed.speaking_rate ?? 1.0,
            }
          })
          setConfigIds(ids)
          setVoices(loaded)
          return loaded
        }
        return defaultVoices
      } catch {
        return defaultVoices
      }
    },
  })

  const updateVoice = (id: string, field: keyof VoiceProfile, value: number) => {
    setVoices((prev) =>
      prev.map((v) => (v.id === id ? { ...v, [field]: value } : v))
    )
    setDirty(true)
  }

  const mutation = useMutation({
    mutationFn: async (voiceList: VoiceProfile[]) => {
      await Promise.all(
        voiceList.map(async (voice) => {
          const payload = {
            name: voice.name,
            pitch: voice.pitch,
            speaking_rate: voice.speaking_rate,
          }
          if (configIds[voice.id]) {
            await api(`/admin/config/${configIds[voice.id]}`, {
              method: 'PATCH',
              body: JSON.stringify({
                value: payload,
                reason: 'Updated via admin dashboard',
              }),
            })
          } else {
            await api('/admin/config', {
              method: 'POST',
              body: JSON.stringify({
                category: 'voice_profile',
                key: voice.id,
                value: payload,
                description: `Voice profile: ${voice.name}`,
              }),
            })
          }
        })
      )
    },
    onSuccess: () => {
      setSaveStatus('Saved successfully')
      setDirty(false)
      queryClient.invalidateQueries({ queryKey: ['config-voice-profiles'] })
      setTimeout(() => setSaveStatus(null), 3000)
    },
    onError: () => {
      setSaveStatus('Failed to save (API may not be connected)')
      setTimeout(() => setSaveStatus(null), 3000)
    },
  })

  if (isLoading) {
    return <p className="text-gray-500">Loading voice profiles...</p>
  }

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold text-gray-900">Voice Profiles</h1>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {voices.map((voice) => (
          <Card key={voice.id} title={voice.name}>
            <div className="space-y-4">
              <div>
                <label className="block text-sm text-gray-600 mb-1">
                  Pitch: {voice.pitch.toFixed(1)}
                </label>
                <input
                  type="range"
                  min="-2"
                  max="2"
                  step="0.1"
                  value={voice.pitch}
                  onChange={(e) => updateVoice(voice.id, 'pitch', parseFloat(e.target.value))}
                  className="w-full"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-600 mb-1">
                  Speaking Rate: {voice.speaking_rate.toFixed(1)}x
                </label>
                <input
                  type="range"
                  min="0.5"
                  max="2.0"
                  step="0.1"
                  value={voice.speaking_rate}
                  onChange={(e) => updateVoice(voice.id, 'speaking_rate', parseFloat(e.target.value))}
                  className="w-full"
                />
              </div>
              <button
                className="px-3 py-1.5 bg-gray-100 text-gray-600 rounded text-sm hover:bg-gray-200"
                onClick={() => alert(`Preview for "${voice.name}" voice is not yet connected.`)}
              >
                Preview
              </button>
            </div>
          </Card>
        ))}
      </div>

      <div className="flex items-center justify-between">
        <div>
          {saveStatus && (
            <p className={`text-sm ${saveStatus.includes('Failed') ? 'text-red-600' : 'text-green-600'}`}>
              {saveStatus}
            </p>
          )}
        </div>
        <button
          onClick={() => mutation.mutate(voices)}
          disabled={mutation.isPending || !dirty}
          className="px-4 py-2 bg-companion-blue text-white rounded-lg text-sm font-medium hover:bg-companion-blue-mid disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {mutation.isPending ? 'Saving...' : 'Save Voices'}
        </button>
      </div>
    </div>
  )
}
