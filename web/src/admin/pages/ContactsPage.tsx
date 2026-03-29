import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../../shared/api/client'
import { Card } from '../../shared/components/Card'

interface ContactEntry {
  id: string
  user_id: string
  user_name: string
  contact_name: string
  contact_email: string | null
  contact_phone: string | null
  relationship_type: string
  access_tier: string
  is_active: boolean
}

interface ContactsResponse {
  contacts: ContactEntry[]
  total: number
}

interface UserOption {
  id: string
  email: string
  name: string
}

interface UsersResponse {
  users: UserOption[]
}

const RELATIONSHIP_TYPES = [
  { value: 'family', label: 'Family' },
  { value: 'case_worker', label: 'Case Worker' },
  { value: 'support_coordinator', label: 'Support Coordinator' },
  { value: 'group_home_staff', label: 'Group Home Staff' },
  { value: 'paid_support', label: 'Paid Support' },
]

const ACCESS_TIERS = [
  { value: 'tier_1', label: 'Tier 1' },
  { value: 'tier_2', label: 'Tier 2' },
  { value: 'tier_3', label: 'Tier 3' },
]

export function ContactsPage() {
  const queryClient = useQueryClient()
  const [userId, setUserId] = useState('')
  const [contactName, setContactName] = useState('')
  const [contactEmail, setContactEmail] = useState('')
  const [relationshipType, setRelationshipType] = useState('family')
  const [accessTier, setAccessTier] = useState('tier_1')
  const [status, setStatus] = useState<string | null>(null)

  const { data: contactsData, isLoading: contactsLoading } = useQuery({
    queryKey: ['admin-contacts'],
    queryFn: () => api<ContactsResponse>('/admin/contacts'),
  })

  const { data: usersData } = useQuery({
    queryKey: ['admin-all-users'],
    queryFn: () => api<UsersResponse>('/admin/users'),
  })

  const addMutation = useMutation({
    mutationFn: async () => {
      await api('/admin/contacts', {
        method: 'POST',
        body: JSON.stringify({
          user_id: userId,
          contact_name: contactName,
          contact_email: contactEmail || undefined,
          relationship_type: relationshipType,
          access_tier: accessTier,
        }),
      })
    },
    onSuccess: () => {
      setStatus('Contact added')
      setContactName('')
      setContactEmail('')
      setRelationshipType('family')
      setAccessTier('tier_1')
      queryClient.invalidateQueries({ queryKey: ['admin-contacts'] })
      setTimeout(() => setStatus(null), 3000)
    },
    onError: () => {
      setStatus('Failed to add contact')
      setTimeout(() => setStatus(null), 3000)
    },
  })

  const deleteMutation = useMutation({
    mutationFn: async (id: string) => {
      await api(`/admin/contacts/${id}`, { method: 'DELETE' })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-contacts'] })
    },
  })

  const contacts = Array.isArray(contactsData?.contacts) ? contactsData.contacts : []
  const users = Array.isArray(usersData?.users) ? usersData.users : []

  if (contactsLoading) {
    return <p className="text-gray-500">Loading contacts...</p>
  }

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold text-gray-900">Trusted Contacts Management</h1>

      <Card title="Add Trusted Contact">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <select
            value={userId}
            onChange={(e) => setUserId(e.target.value)}
            className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-companion-blue-light focus:border-companion-blue-light"
          >
            <option value="">Select user...</option>
            {users.map((u) => (
              <option key={u.id} value={u.id}>
                {u.name} ({u.email})
              </option>
            ))}
          </select>
          <input
            type="text"
            placeholder="Contact name"
            value={contactName}
            onChange={(e) => setContactName(e.target.value)}
            className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-companion-blue-light focus:border-companion-blue-light"
          />
          <input
            type="email"
            placeholder="Contact email (optional)"
            value={contactEmail}
            onChange={(e) => setContactEmail(e.target.value)}
            className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-companion-blue-light focus:border-companion-blue-light"
          />
          <select
            value={relationshipType}
            onChange={(e) => setRelationshipType(e.target.value)}
            className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-companion-blue-light focus:border-companion-blue-light"
          >
            {RELATIONSHIP_TYPES.map((r) => (
              <option key={r.value} value={r.value}>
                {r.label}
              </option>
            ))}
          </select>
          <select
            value={accessTier}
            onChange={(e) => setAccessTier(e.target.value)}
            className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-companion-blue-light focus:border-companion-blue-light"
          >
            {ACCESS_TIERS.map((t) => (
              <option key={t.value} value={t.value}>
                {t.label}
              </option>
            ))}
          </select>
          <button
            onClick={() => addMutation.mutate()}
            disabled={addMutation.isPending || !userId || !contactName}
            className="px-4 py-2 bg-companion-blue text-white rounded-lg text-sm font-medium hover:bg-companion-blue-mid disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {addMutation.isPending ? 'Adding...' : 'Add Contact'}
          </button>
        </div>
        {status && (
          <p
            className={`text-sm mt-2 ${status.includes('Failed') ? 'text-red-600' : 'text-green-600'}`}
          >
            {status}
          </p>
        )}
      </Card>

      <Card title="All Trusted Contacts" subtitle={`${contacts.length} contact(s)`}>
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left">
            <thead>
              <tr className="border-b border-gray-200 text-gray-500">
                <th className="py-2 pr-4 font-medium">User</th>
                <th className="py-2 pr-4 font-medium">Contact Name</th>
                <th className="py-2 pr-4 font-medium">Email</th>
                <th className="py-2 pr-4 font-medium">Relationship</th>
                <th className="py-2 pr-4 font-medium">Tier</th>
                <th className="py-2 pr-4 font-medium">Active</th>
                <th className="py-2 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              {contacts.map((c) => (
                <tr key={c.id} className="border-b border-gray-100">
                  <td className="py-2 pr-4 text-gray-900">{c.user_name}</td>
                  <td className="py-2 pr-4 text-gray-700">{c.contact_name}</td>
                  <td className="py-2 pr-4 text-gray-500">{c.contact_email ?? '-'}</td>
                  <td className="py-2 pr-4">
                    <span className="inline-block px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-700">
                      {c.relationship_type}
                    </span>
                  </td>
                  <td className="py-2 pr-4">
                    <span className="inline-block px-2 py-0.5 rounded text-xs font-medium bg-blue-50 text-blue-700">
                      {c.access_tier}
                    </span>
                  </td>
                  <td className="py-2 pr-4">
                    <span
                      className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${
                        c.is_active
                          ? 'bg-green-100 text-green-700'
                          : 'bg-red-100 text-red-700'
                      }`}
                    >
                      {c.is_active ? 'Yes' : 'No'}
                    </span>
                  </td>
                  <td className="py-2">
                    <button
                      onClick={() => deleteMutation.mutate(c.id)}
                      disabled={deleteMutation.isPending}
                      className="text-xs text-red-600 hover:text-red-800 font-medium"
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
              {contacts.length === 0 && (
                <tr>
                  <td colSpan={7} className="py-4 text-center text-gray-400">
                    No trusted contacts found
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  )
}
