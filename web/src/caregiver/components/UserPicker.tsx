import { useQuery } from '@tanstack/react-query'
import { api } from '../../shared/api/client'

interface Charge {
  user_id: string
  name: string
  email: string
  access_tier: string
  relationship: string
}

interface Props {
  selectedUserId: string | null
  onSelect: (userId: string) => void
}

export function UserPicker({ selectedUserId, onSelect }: Props) {
  const { data, isLoading } = useQuery({
    queryKey: ['my-charges'],
    queryFn: () => api<{ charges: Charge[] }>('/api/v1/auth/my-charges'),
  })

  const charges = Array.isArray(data?.charges) ? data.charges : []

  if (isLoading) {
    return <div className="text-gray-400 text-sm">Loading charges...</div>
  }

  if (charges.length === 0) {
    return (
      <div className="bg-amber-50 border border-amber-200 rounded-xl p-6 text-center">
        <h3 className="font-semibold text-amber-800 mb-1">No Charges Assigned</h3>
        <p className="text-amber-600 text-sm">
          You are not assigned as a caregiver for any users.
          Contact an administrator to be assigned.
        </p>
      </div>
    )
  }

  // Auto-select if only one charge
  if (charges.length === 1 && !selectedUserId) {
    setTimeout(() => onSelect(charges[0].user_id), 0)
  }

  return (
    <div className="mb-6">
      <label className="block text-sm font-medium text-gray-600 mb-2">
        Viewing data for:
      </label>
      <div className="flex flex-wrap gap-3">
        {charges.map((charge) => (
          <button
            key={charge.user_id}
            onClick={() => onSelect(charge.user_id)}
            className={`px-4 py-3 rounded-xl border-2 text-left transition ${
              selectedUserId === charge.user_id
                ? 'border-companion-blue bg-blue-50 text-companion-blue'
                : 'border-gray-200 bg-white text-gray-700 hover:border-gray-300'
            }`}
          >
            <div className="font-medium">{charge.name}</div>
            <div className="text-xs text-gray-400 mt-0.5">
              {charge.relationship} · Tier {charge.access_tier.replace('TIER_', '')}
            </div>
          </button>
        ))}
      </div>
    </div>
  )
}
