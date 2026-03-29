import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../../shared/api/client'

interface User {
  id: string
  name: string
  email: string
}

interface Contact {
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

const RELATIONSHIPS = [
  { value: 'family', label: 'Family' },
  { value: 'case_worker', label: 'Case Worker' },
  { value: 'support_coordinator', label: 'Support Coordinator' },
  { value: 'group_home_staff', label: 'Group Home Staff' },
  { value: 'paid_support', label: 'Paid Support' },
]

const TIERS = [
  { value: 'tier_1', label: 'Tier 1 — Alerts Only' },
  { value: 'tier_2', label: 'Tier 2 — Read-Only Dashboard' },
  { value: 'tier_3', label: 'Tier 3 — Scoped Collaboration' },
]

const RELATIONSHIP_COLORS: Record<string, string> = {
  family: 'bg-emerald-100 text-emerald-800',
  FAMILY: 'bg-emerald-100 text-emerald-800',
  case_worker: 'bg-sky-100 text-sky-800',
  CASE_WORKER: 'bg-sky-100 text-sky-800',
  support_coordinator: 'bg-violet-100 text-violet-800',
  SUPPORT_COORDINATOR: 'bg-violet-100 text-violet-800',
  group_home_staff: 'bg-amber-100 text-amber-800',
  GROUP_HOME_STAFF: 'bg-amber-100 text-amber-800',
  paid_support: 'bg-orange-100 text-orange-800',
  PAID_SUPPORT: 'bg-orange-100 text-orange-800',
}

const TIER_COLORS: Record<string, string> = {
  tier_1: 'bg-gray-100 text-gray-700',
  TIER_1: 'bg-gray-100 text-gray-700',
  tier_2: 'bg-blue-100 text-blue-700',
  TIER_2: 'bg-blue-100 text-blue-700',
  tier_3: 'bg-indigo-100 text-indigo-700',
  TIER_3: 'bg-indigo-100 text-indigo-700',
}

function relationshipLabel(value: string): string {
  const v = value.toLowerCase()
  return RELATIONSHIPS.find((r) => r.value === v)?.label ?? value
}

function tierLabel(value: string): string {
  return TIERS.find((t) => t.value === value)?.label ?? value
}

export function ContactsPage() {
  const queryClient = useQueryClient()
  const [search, setSearch] = useState('')
  const [searchMode, setSearchMode] = useState<'user' | 'caregiver'>('user')
  const [expandedUser, setExpandedUser] = useState<string | null>(null)
  const [addingFor, setAddingFor] = useState<string | null>(null)
  const [newContact, setNewContact] = useState({
    contact_name: '',
    contact_email: '',
    relationship_type: 'family',
    access_tier: 'tier_1',
  })

  const { data: usersData, isLoading: usersLoading } = useQuery({
    queryKey: ['admin-companion-users'],
    queryFn: () => api<{ users: User[] }>('/admin/users'),
  })

  const { data: contactsData, isLoading: contactsLoading } = useQuery({
    queryKey: ['admin-contacts'],
    queryFn: () => api<{ contacts: Contact[] }>('/admin/contacts'),
  })

  const users = Array.isArray(usersData?.users) ? usersData.users : []
  const contacts = Array.isArray(contactsData?.contacts) ? contactsData.contacts : []

  const searchLower = search.toLowerCase()

  const filteredUsers = users.filter((u) => {
    if (!search) return true
    if (searchMode === 'user') {
      return (
        u.name.toLowerCase().includes(searchLower) ||
        u.email.toLowerCase().includes(searchLower)
      )
    }
    // Caregiver search: show users who have a caregiver matching the search
    return contacts.some(
      (c) =>
        c.user_id === u.id &&
        (c.contact_name.toLowerCase().includes(searchLower) ||
          (c.contact_email?.toLowerCase().includes(searchLower) ?? false))
    )
  })

  const contactsByUser = (userId: string) =>
    contacts.filter((c) => c.user_id === userId)

  const addMutation = useMutation({
    mutationFn: (data: Record<string, string>) =>
      api('/admin/contacts', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-contacts'] })
      setAddingFor(null)
      setNewContact({
        contact_name: '',
        contact_email: '',
        relationship_type: 'family',
        access_tier: 'tier_1',
      })
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (contactId: string) =>
      api(`/admin/contacts/${contactId}`, { method: 'DELETE' }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-contacts'] })
    },
  })

  const toggleExpand = (userId: string) => {
    if (expandedUser === userId) {
      setExpandedUser(null)
      setAddingFor(null)
    } else {
      setExpandedUser(userId)
      setAddingFor(null)
    }
  }

  const handleAdd = (userId: string) => {
    addMutation.mutate({
      user_id: userId,
      ...newContact,
    })
  }

  const startAdding = (userId: string) => {
    setAddingFor(userId)
    setNewContact({
      contact_name: '',
      contact_email: '',
      relationship_type: 'family',
      access_tier: 'tier_1',
    })
  }

  const isLoading = usersLoading || contactsLoading

  if (isLoading) {
    return <p className="text-gray-500 p-6">Loading contacts...</p>
  }

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold text-gray-900">
        Trusted Contacts Management
      </h1>

      {/* Search bar */}
      <div className="relative">
        <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3">
          <svg
            className="h-5 w-5 text-gray-400"
            viewBox="0 0 20 20"
            fill="currentColor"
            aria-hidden="true"
          >
            <path
              fillRule="evenodd"
              d="M9 3.5a5.5 5.5 0 100 11 5.5 5.5 0 000-11zM2 9a7 7 0 1112.452 4.391l3.328 3.329a.75.75 0 11-1.06 1.06l-3.329-3.328A7 7 0 012 9z"
              clipRule="evenodd"
            />
          </svg>
        </div>
        <input
          type="text"
          placeholder={
            searchMode === 'user'
              ? 'Search users by name or email...'
              : 'Search by caregiver name or email...'
          }
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="block w-full rounded-lg border border-gray-300 bg-white py-2.5 pl-10 pr-4 text-sm text-gray-900 placeholder-gray-400 focus:border-companion-blue-light focus:outline-none focus:ring-2 focus:ring-companion-blue-light"
        />
      </div>

      {/* Search mode toggle */}
      <div className="flex gap-1 text-xs">
        <button
          onClick={() => { setSearchMode('user'); setSearch('') }}
          className={`px-3 py-1 rounded-full transition ${
            searchMode === 'user'
              ? 'bg-companion-blue text-white'
              : 'bg-gray-100 text-gray-500 hover:bg-gray-200'
          }`}
        >
          Search by User
        </button>
        <button
          onClick={() => { setSearchMode('caregiver'); setSearch('') }}
          className={`px-3 py-1 rounded-full transition ${
            searchMode === 'caregiver'
              ? 'bg-companion-blue text-white'
              : 'bg-gray-100 text-gray-500 hover:bg-gray-200'
          }`}
        >
          Search by Caregiver
        </button>
      </div>

      {/* User list */}
      <div className="overflow-hidden rounded-lg border border-gray-200 bg-white shadow-sm">
        {filteredUsers.length === 0 ? (
          <div className="px-6 py-12 text-center text-sm text-gray-400">
            No users found
          </div>
        ) : (
          filteredUsers.map((user) => {
            const userContacts = contactsByUser(user.id)
            const isExpanded = expandedUser === user.id
            const isAdding = addingFor === user.id
            const caregiverCount = userContacts.length

            return (
              <div key={user.id} className="border-b border-gray-100 last:border-b-0">
                {/* User row */}
                <button
                  type="button"
                  onClick={() => toggleExpand(user.id)}
                  className="flex w-full items-center justify-between px-5 py-3.5 text-left transition-colors hover:bg-gray-50"
                >
                  <div className="min-w-0 flex-1">
                    <span className="text-sm font-medium text-gray-900">
                      {user.name}
                    </span>
                    <span className="ml-3 text-sm text-gray-500">
                      {user.email}
                    </span>
                  </div>
                  <div className="ml-4 flex items-center gap-3">
                    <span className="text-xs text-gray-400">
                      {caregiverCount === 0
                        ? 'No caregivers'
                        : caregiverCount === 1
                          ? '1 caregiver'
                          : `${caregiverCount} caregivers`}
                    </span>
                    <span className="text-xs text-gray-400 transition-transform duration-200">
                      {isExpanded ? '\u25BC' : '\u25B6'}
                    </span>
                  </div>
                </button>

                {/* Expanded section */}
                {isExpanded && (
                  <div className="border-t border-gray-100 bg-gray-50 px-5 py-4">
                    {/* Caregiver list */}
                    {userContacts.length > 0 ? (
                      <div className="space-y-2">
                        {userContacts.map((c) => (
                          <div
                            key={c.id}
                            className="flex items-center justify-between rounded-md bg-white px-4 py-2.5 shadow-sm ring-1 ring-gray-100"
                          >
                            <div className="flex min-w-0 flex-1 items-center gap-3">
                              <span className="text-sm font-medium text-gray-800">
                                {c.contact_name}
                              </span>
                              <span className="text-sm text-gray-500">
                                {c.contact_email ?? ''}
                              </span>
                              <span
                                className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${
                                  RELATIONSHIP_COLORS[c.relationship_type] ??
                                  'bg-gray-100 text-gray-700'
                                }`}
                              >
                                {relationshipLabel(c.relationship_type)}
                              </span>
                              <span
                                className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${
                                  TIER_COLORS[c.access_tier] ??
                                  'bg-gray-100 text-gray-700'
                                }`}
                              >
                                {tierLabel(c.access_tier)}
                              </span>
                            </div>
                            <button
                              type="button"
                              onClick={() => deleteMutation.mutate(c.id)}
                              disabled={deleteMutation.isPending}
                              className="ml-3 flex-shrink-0 text-sm text-gray-400 transition-colors hover:text-companion-rose disabled:opacity-50"
                              title="Remove caregiver"
                            >
                              &#10005;
                            </button>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="text-sm text-gray-400">
                        No caregivers assigned yet.
                      </p>
                    )}

                    {/* Add Caregiver section */}
                    {!isAdding ? (
                      <button
                        type="button"
                        onClick={() => startAdding(user.id)}
                        className="mt-3 inline-flex items-center gap-1.5 rounded-md bg-companion-blue px-3 py-1.5 text-xs font-medium text-white transition-colors hover:bg-companion-blue-mid"
                      >
                        <span className="text-sm leading-none">+</span>
                        Add Caregiver
                      </button>
                    ) : (
                      <div className="mt-3 rounded-md border border-gray-200 bg-white p-4">
                        <div className="flex flex-wrap items-end gap-3">
                          <div className="flex-1 min-w-[160px]">
                            <label className="mb-1 block text-xs font-medium text-gray-600">
                              Contact Name
                            </label>
                            <input
                              type="text"
                              value={newContact.contact_name}
                              onChange={(e) =>
                                setNewContact({
                                  ...newContact,
                                  contact_name: e.target.value,
                                })
                              }
                              placeholder="Full name"
                              className="block w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:border-companion-blue-light focus:outline-none focus:ring-1 focus:ring-companion-blue-light"
                            />
                          </div>
                          <div className="flex-1 min-w-[180px]">
                            <label className="mb-1 block text-xs font-medium text-gray-600">
                              Contact Email
                            </label>
                            <input
                              type="email"
                              value={newContact.contact_email}
                              onChange={(e) =>
                                setNewContact({
                                  ...newContact,
                                  contact_email: e.target.value,
                                })
                              }
                              placeholder="email@example.com"
                              className="block w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:border-companion-blue-light focus:outline-none focus:ring-1 focus:ring-companion-blue-light"
                            />
                          </div>
                          <div className="min-w-[150px]">
                            <label className="mb-1 block text-xs font-medium text-gray-600">
                              Relationship
                            </label>
                            <select
                              value={newContact.relationship_type}
                              onChange={(e) =>
                                setNewContact({
                                  ...newContact,
                                  relationship_type: e.target.value,
                                })
                              }
                              className="block w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:border-companion-blue-light focus:outline-none focus:ring-1 focus:ring-companion-blue-light"
                            >
                              {RELATIONSHIPS.map((r) => (
                                <option key={r.value} value={r.value}>
                                  {r.label}
                                </option>
                              ))}
                            </select>
                          </div>
                          <div className="min-w-[200px]">
                            <label className="mb-1 block text-xs font-medium text-gray-600">
                              Access Tier
                            </label>
                            <select
                              value={newContact.access_tier}
                              onChange={(e) =>
                                setNewContact({
                                  ...newContact,
                                  access_tier: e.target.value,
                                })
                              }
                              className="block w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:border-companion-blue-light focus:outline-none focus:ring-1 focus:ring-companion-blue-light"
                            >
                              {TIERS.map((t) => (
                                <option key={t.value} value={t.value}>
                                  {t.label}
                                </option>
                              ))}
                            </select>
                          </div>
                          <div className="flex items-center gap-2">
                            <button
                              type="button"
                              onClick={() => handleAdd(user.id)}
                              disabled={
                                addMutation.isPending ||
                                !newContact.contact_name.trim()
                              }
                              className="rounded-md bg-companion-blue px-4 py-1.5 text-sm font-medium text-white transition-colors hover:bg-companion-blue-mid disabled:cursor-not-allowed disabled:opacity-50"
                            >
                              {addMutation.isPending ? 'Saving...' : 'Save'}
                            </button>
                            <button
                              type="button"
                              onClick={() => setAddingFor(null)}
                              className="rounded-md px-3 py-1.5 text-sm font-medium text-gray-500 transition-colors hover:text-gray-700"
                            >
                              Cancel
                            </button>
                          </div>
                        </div>
                        {addMutation.isError && (
                          <p className="mt-2 text-xs text-companion-rose">
                            Failed to add caregiver. Please try again.
                          </p>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}
