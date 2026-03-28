import { useQuery } from '@tanstack/react-query'
import { api } from '../../shared/api/client'
import { Card } from '../../shared/components/Card'

interface Escalation {
  id: string
  question_text: string
  context_type: string
  hours_open: number
  threshold_hours: number
}

const placeholderData: Escalation[] = [
  {
    id: 'esc-1',
    question_text: 'What is the copay for the new prescription?',
    context_type: 'insurance',
    hours_open: 22,
    threshold_hours: 24,
  },
  {
    id: 'esc-2',
    question_text: 'When is the next property tax payment due?',
    context_type: 'financial',
    hours_open: 18,
    threshold_hours: 48,
  },
  {
    id: 'esc-3',
    question_text: 'Can I reschedule the dentist appointment?',
    context_type: 'medical',
    hours_open: 46,
    threshold_hours: 24,
  },
]

export function EscalationsPage() {
  const { data, isLoading } = useQuery({
    queryKey: ['escalations'],
    queryFn: async () => {
      try {
        return await api<Escalation[]>('/admin/escalations')
      } catch {
        return placeholderData
      }
    },
  })

  const escalations = Array.isArray(data) ? data : placeholderData

  if (isLoading) {
    return <p className="text-gray-500">Loading escalations...</p>
  }

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold text-gray-900">Open Escalations</h1>

      {escalations.length === 0 ? (
        <p className="text-gray-500">No open escalations.</p>
      ) : (
        <div className="space-y-3">
          {escalations.map((esc) => {
            const pct = Math.min((esc.hours_open / esc.threshold_hours) * 100, 100)
            const overdue = esc.hours_open >= esc.threshold_hours
            return (
              <Card key={esc.id} title={esc.question_text} subtitle={esc.context_type}>
                <div className="flex items-center gap-3">
                  <div className="flex-1 bg-gray-200 rounded-full h-2.5">
                    <div
                      className={`h-2.5 rounded-full ${overdue ? 'bg-companion-rose' : 'bg-companion-amber'}`}
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                  <span className={`text-sm font-medium ${overdue ? 'text-companion-rose' : 'text-gray-600'}`}>
                    {esc.hours_open}h / {esc.threshold_hours}h
                  </span>
                </div>
                {overdue && (
                  <p className="text-xs text-companion-rose mt-2 font-medium">
                    Past threshold - needs immediate attention
                  </p>
                )}
              </Card>
            )
          })}
        </div>
      )}
    </div>
  )
}
