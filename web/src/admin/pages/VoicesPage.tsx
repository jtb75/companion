import { useState } from 'react'
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
  const [voices, setVoices] = useState<VoiceProfile[]>(defaultVoices)

  const updateVoice = (id: string, field: keyof VoiceProfile, value: number) => {
    setVoices((prev) =>
      prev.map((v) => (v.id === id ? { ...v, [field]: value } : v))
    )
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
    </div>
  )
}
