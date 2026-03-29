import { useState, useEffect } from 'react'
import { useAuth } from './AuthProvider'
import { api } from '../api/client'
import { useQuery, useMutation } from '@tanstack/react-query'

interface UserProfile {
  email: string
  first_name: string | null
  last_name: string | null
  phone: string | null
  preferred_name: string | null
}

export default function ProfilePage() {
  const { user } = useAuth()

  const { data, isLoading } = useQuery({
    queryKey: ['my-profile'],
    queryFn: () => api<UserProfile>('/api/v1/me'),
    enabled: !!user,
  })

  const [firstName, setFirstName] = useState('')
  const [lastName, setLastName] = useState('')
  const [preferredName, setPreferredName] = useState('')
  const [phone, setPhone] = useState('')
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    if (data) {
      setFirstName(data.first_name || '')
      setLastName(data.last_name || '')
      setPreferredName(data.preferred_name || '')
      setPhone(data.phone || '')
    }
  }, [data])

  const mutation = useMutation({
    mutationFn: (profileData: Record<string, string | null>) =>
      api('/api/v1/auth/complete-profile', {
        method: 'POST',
        body: JSON.stringify(profileData),
      }),
    onSuccess: () => {
      setSaved(true)
      setTimeout(() => setSaved(false), 3000)
    },
  })

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault()
    mutation.mutate({
      first_name: firstName.trim(),
      last_name: lastName.trim(),
      preferred_name: preferredName.trim() || firstName.trim(),
      phone: phone.trim() || null,
    })
  }

  if (isLoading) {
    return (
      <div className="max-w-lg mx-auto mt-12">
        <p className="text-gray-400">Loading profile...</p>
      </div>
    )
  }

  return (
    <div className="max-w-lg mx-auto mt-8">
      <h1 className="text-xl font-semibold text-gray-900 mb-6">My Profile</h1>

      <form onSubmit={handleSave} className="bg-white rounded-xl border border-gray-200 shadow-sm p-6 space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Email
          </label>
          <input
            type="email"
            value={user?.email || ''}
            disabled
            className="w-full px-4 py-2.5 bg-gray-50 border border-gray-200 rounded-lg text-sm text-gray-500"
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              First Name
            </label>
            <input
              type="text"
              value={firstName}
              onChange={(e) => setFirstName(e.target.value)}
              className="w-full px-4 py-2.5 border border-gray-200 rounded-lg text-sm focus:border-companion-blue focus:outline-none focus:ring-2 focus:ring-companion-blue-light"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Last Name
            </label>
            <input
              type="text"
              value={lastName}
              onChange={(e) => setLastName(e.target.value)}
              className="w-full px-4 py-2.5 border border-gray-200 rounded-lg text-sm focus:border-companion-blue focus:outline-none focus:ring-2 focus:ring-companion-blue-light"
            />
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Preferred Name
          </label>
          <input
            type="text"
            value={preferredName}
            onChange={(e) => setPreferredName(e.target.value)}
            placeholder="What Arlo calls you (defaults to first name)"
            className="w-full px-4 py-2.5 border border-gray-200 rounded-lg text-sm focus:border-companion-blue focus:outline-none focus:ring-2 focus:ring-companion-blue-light"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Phone
          </label>
          <input
            type="tel"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            placeholder="Optional"
            className="w-full px-4 py-2.5 border border-gray-200 rounded-lg text-sm focus:border-companion-blue focus:outline-none focus:ring-2 focus:ring-companion-blue-light"
          />
        </div>

        <div className="flex items-center gap-3 pt-2">
          <button
            type="submit"
            disabled={mutation.isPending}
            className="bg-companion-blue text-white font-medium px-6 py-2.5 rounded-lg hover:bg-companion-blue-mid transition disabled:opacity-50"
          >
            {mutation.isPending ? 'Saving...' : 'Save Changes'}
          </button>
          {saved && (
            <span className="text-sm text-green-600">✓ Profile updated</span>
          )}
          {mutation.isError && (
            <span className="text-sm text-red-500">Failed to save</span>
          )}
        </div>
      </form>
    </div>
  )
}
