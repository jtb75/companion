import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../../shared/api/client'

interface CaregiverAssignment {
  contact_id: string
  user_id: string
  user_name: string
  contact_name: string
  relationship: string
  tier: string
  is_active: boolean
}

interface Person {
  id: string | null
  email: string
  first_name: string | null
  last_name: string | null
  phone: string | null
  preferred_name: string | null
  display_name: string | null
  is_user: boolean
  is_admin: boolean
  admin_id: string | null
  admin_role: string | null
  caregiver_for: CaregiverAssignment[]
  created_at: string | null
}

interface UserOption {
  id: string
  email: string
  name: string
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

const ADMIN_ROLES = [
  { value: 'viewer', label: 'Viewer' },
  { value: 'editor', label: 'Editor' },
  { value: 'admin', label: 'Admin' },
]

function relationshipLabel(value: string): string {
  const v = value.toLowerCase()
  return RELATIONSHIPS.find((r) => r.value === v)?.label ?? value
}

function tierLabel(value: string): string {
  const v = value.toLowerCase()
  return TIERS.find((t) => t.value === v)?.label ?? value
}

export function PeoplePage() {
  const queryClient = useQueryClient()
  const [search, setSearch] = useState('')
  const [expandedEmail, setExpandedEmail] = useState<string | null>(null)
  const [showAddForm, setShowAddForm] = useState(false)
  const [assigningEmail, setAssigningEmail] = useState<string | null>(null)

  // Edit form state
  const [editForm, setEditForm] = useState<{
    first_name: string
    last_name: string
    preferred_name: string
    phone: string
    is_admin: boolean
    admin_role: string
  }>({ first_name: '', last_name: '', preferred_name: '', phone: '', is_admin: false, admin_role: 'viewer' })

  // New person form state
  const [newPerson, setNewPerson] = useState({
    email: '',
    first_name: '',
    last_name: '',
    phone: '',
    is_user: true,
    is_admin: false,
    admin_role: 'viewer',
  })

  // New caregiver assignment form state
  const [newAssignment, setNewAssignment] = useState({
    user_id: '',
    contact_name: '',
    relationship: 'family',
    tier: 'tier_1',
  })

  const { data: peopleData, isLoading } = useQuery({
    queryKey: ['admin-people'],
    queryFn: () => api<{ people: Person[]; total: number }>('/admin/people'),
  })

  const { data: usersData } = useQuery({
    queryKey: ['admin-users-list'],
    queryFn: () => api<{ users: UserOption[] }>('/admin/users'),
  })

  const people = Array.isArray(peopleData?.people) ? peopleData.people : []
  const userOptions = Array.isArray(usersData?.users) ? usersData.users : []

  const searchLower = search.toLowerCase()
  const filteredPeople = people.filter((p) => {
    if (!search) return true
    const name = (p.display_name || p.first_name || '').toLowerCase()
    const email = (p.email || '').toLowerCase()
    const roles: string[] = []
    if (p.is_user) roles.push('user')
    if (p.is_admin) roles.push('admin', p.admin_role || '')
    if (Array.isArray(p.caregiver_for) && p.caregiver_for.length > 0) roles.push('caregiver')
    const roleStr = roles.join(' ')
    return (
      name.includes(searchLower) ||
      email.includes(searchLower) ||
      roleStr.includes(searchLower)
    )
  })

  const createMutation = useMutation({
    mutationFn: (data: typeof newPerson) =>
      api('/admin/people', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-people'] })
      queryClient.invalidateQueries({ queryKey: ['admin-users-list'] })
      setShowAddForm(false)
      setNewPerson({
        email: '',
        first_name: '',
        last_name: '',
        phone: '',
        is_user: true,
        is_admin: false,
        admin_role: 'viewer',
      })
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({ email, data }: { email: string; data: Record<string, unknown> }) =>
      api(`/admin/people/${encodeURIComponent(email)}`, {
        method: 'PATCH',
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-people'] })
    },
  })

  const addCaregiverMutation = useMutation({
    mutationFn: ({ email, data }: { email: string; data: Record<string, string> }) =>
      api(`/admin/people/${encodeURIComponent(email)}/caregiver`, {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-people'] })
      setAssigningEmail(null)
      setNewAssignment({ user_id: '', contact_name: '', relationship: 'family', tier: 'tier_1' })
    },
  })

  const removeCaregiverMutation = useMutation({
    mutationFn: (contactId: string) =>
      api(`/admin/people/caregiver/${contactId}`, { method: 'DELETE' }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-people'] })
    },
  })

  const toggleExpand = (person: Person) => {
    if (expandedEmail === person.email) {
      setExpandedEmail(null)
      setAssigningEmail(null)
    } else {
      setExpandedEmail(person.email)
      setAssigningEmail(null)
      setEditForm({
        first_name: person.first_name || '',
        last_name: person.last_name || '',
        preferred_name: person.preferred_name || '',
        phone: person.phone || '',
        is_admin: person.is_admin,
        admin_role: person.admin_role || 'viewer',
      })
    }
  }

  const handleSave = (email: string) => {
    updateMutation.mutate({
      email,
      data: {
        first_name: editForm.first_name,
        last_name: editForm.last_name,
        preferred_name: editForm.preferred_name,
        phone: editForm.phone,
        is_admin: editForm.is_admin,
        admin_role: editForm.admin_role,
      },
    })
  }

  const handleAddCaregiver = (email: string) => {
    addCaregiverMutation.mutate({
      email,
      data: {
        user_id: newAssignment.user_id,
        contact_name: newAssignment.contact_name || email,
        relationship: newAssignment.relationship,
        tier: newAssignment.tier,
      },
    })
  }

  if (isLoading) {
    return <p className="text-gray-500 p-6">Loading people...</p>
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-900">People</h1>
        <button
          type="button"
          onClick={() => setShowAddForm(!showAddForm)}
          className="inline-flex items-center gap-1.5 rounded-md bg-companion-blue px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-companion-blue-mid"
        >
          <span className="text-base leading-none">+</span>
          Add Person
        </button>
      </div>

      {/* Add Person form */}
      {showAddForm && (
        <div className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
          <h2 className="mb-4 text-sm font-semibold text-gray-700">New Person</h2>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-600">Email *</label>
              <input
                type="email"
                value={newPerson.email}
                onChange={(e) => setNewPerson({ ...newPerson, email: e.target.value })}
                placeholder="email@example.com"
                className="block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-companion-blue-light focus:outline-none focus:ring-1 focus:ring-companion-blue-light"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-600">First Name</label>
              <input
                type="text"
                value={newPerson.first_name}
                onChange={(e) => setNewPerson({ ...newPerson, first_name: e.target.value })}
                className="block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-companion-blue-light focus:outline-none focus:ring-1 focus:ring-companion-blue-light"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-600">Last Name</label>
              <input
                type="text"
                value={newPerson.last_name}
                onChange={(e) => setNewPerson({ ...newPerson, last_name: e.target.value })}
                className="block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-companion-blue-light focus:outline-none focus:ring-1 focus:ring-companion-blue-light"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-600">Phone</label>
              <input
                type="tel"
                value={newPerson.phone}
                onChange={(e) => setNewPerson({ ...newPerson, phone: e.target.value })}
                className="block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-companion-blue-light focus:outline-none focus:ring-1 focus:ring-companion-blue-light"
              />
            </div>
          </div>
          <div className="mt-4 flex items-center gap-6">
            <label className="flex items-center gap-2 text-sm text-gray-700">
              <input
                type="checkbox"
                checked={newPerson.is_user}
                onChange={(e) => setNewPerson({ ...newPerson, is_user: e.target.checked })}
                className="rounded border-gray-300 text-companion-blue focus:ring-companion-blue-light"
              />
              Create as User
            </label>
            <label className="flex items-center gap-2 text-sm text-gray-700">
              <input
                type="checkbox"
                checked={newPerson.is_admin}
                onChange={(e) => setNewPerson({ ...newPerson, is_admin: e.target.checked })}
                className="rounded border-gray-300 text-companion-blue focus:ring-companion-blue-light"
              />
              Create as Admin
            </label>
            {newPerson.is_admin && (
              <select
                value={newPerson.admin_role}
                onChange={(e) => setNewPerson({ ...newPerson, admin_role: e.target.value })}
                className="rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:border-companion-blue-light focus:outline-none focus:ring-1 focus:ring-companion-blue-light"
              >
                {ADMIN_ROLES.map((r) => (
                  <option key={r.value} value={r.value}>{r.label}</option>
                ))}
              </select>
            )}
          </div>
          <div className="mt-4 flex items-center gap-2">
            <button
              type="button"
              onClick={() => createMutation.mutate(newPerson)}
              disabled={createMutation.isPending || !newPerson.email.trim()}
              className="rounded-md bg-companion-blue px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-companion-blue-mid disabled:cursor-not-allowed disabled:opacity-50"
            >
              {createMutation.isPending ? 'Creating...' : 'Create'}
            </button>
            <button
              type="button"
              onClick={() => setShowAddForm(false)}
              className="rounded-md px-4 py-2 text-sm font-medium text-gray-500 transition-colors hover:text-gray-700"
            >
              Cancel
            </button>
          </div>
          {createMutation.isError && (
            <p className="mt-2 text-xs text-companion-rose">
              Failed to create person. Please check the email is unique and try again.
            </p>
          )}
        </div>
      )}

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
          placeholder="Search by name, email, or role..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="block w-full rounded-lg border border-gray-300 bg-white py-2.5 pl-10 pr-4 text-sm text-gray-900 placeholder-gray-400 focus:border-companion-blue-light focus:outline-none focus:ring-2 focus:ring-companion-blue-light"
        />
      </div>

      {/* Summary */}
      <p className="text-xs text-gray-400">
        {filteredPeople.length} of {people.length} people
      </p>

      {/* People list */}
      <div className="overflow-hidden rounded-lg border border-gray-200 bg-white shadow-sm">
        {filteredPeople.length === 0 ? (
          <div className="px-6 py-12 text-center text-sm text-gray-400">
            No people found
          </div>
        ) : (
          filteredPeople.map((person) => {
            const isExpanded = expandedEmail === person.email
            const assignments = Array.isArray(person.caregiver_for) ? person.caregiver_for : []

            return (
              <div key={person.email} className="border-b border-gray-100 last:border-b-0">
                {/* Person row */}
                <button
                  type="button"
                  onClick={() => toggleExpand(person)}
                  className="flex w-full items-center justify-between px-5 py-3.5 text-left transition-colors hover:bg-gray-50"
                >
                  <div className="min-w-0 flex-1">
                    <span className="text-sm font-medium text-gray-900">
                      {person.display_name || person.first_name || person.email}
                    </span>
                    <span className="ml-3 text-sm text-gray-500">{person.email}</span>
                  </div>
                  <div className="ml-4 flex items-center gap-2">
                    {person.is_user && (
                      <span className="inline-flex items-center rounded-full bg-emerald-100 px-2.5 py-0.5 text-xs font-medium text-emerald-800">
                        User
                      </span>
                    )}
                    {person.is_admin && (
                      <span className="inline-flex items-center rounded-full bg-red-100 px-2.5 py-0.5 text-xs font-medium text-red-800">
                        Admin{person.admin_role ? ` (${person.admin_role})` : ''}
                      </span>
                    )}
                    {assignments.length > 0 &&
                      assignments.map((a) => (
                        <span
                          key={a.contact_id}
                          className="inline-flex items-center rounded-full bg-sky-100 px-2.5 py-0.5 text-xs font-medium text-sky-800"
                        >
                          Caregiver for: {a.user_name}
                        </span>
                      ))}
                    <span className="ml-2 text-xs text-gray-400 transition-transform duration-200">
                      {isExpanded ? '\u25BC' : '\u25B6'}
                    </span>
                  </div>
                </button>

                {/* Expanded section */}
                {isExpanded && (
                  <div className="border-t border-gray-100 bg-gray-50 px-5 py-5 space-y-5">
                    {/* Profile Section */}
                    <div className="rounded-lg border border-gray-200 bg-white p-4">
                      <h3 className="mb-3 text-xs font-bold uppercase tracking-wide text-gray-500">
                        Profile
                      </h3>
                      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
                        <div>
                          <label className="mb-1 block text-xs font-medium text-gray-500">
                            First Name
                          </label>
                          <input
                            type="text"
                            value={editForm.first_name}
                            onChange={(e) =>
                              setEditForm({ ...editForm, first_name: e.target.value })
                            }
                            className="block w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:border-companion-blue-light focus:outline-none focus:ring-1 focus:ring-companion-blue-light"
                          />
                        </div>
                        <div>
                          <label className="mb-1 block text-xs font-medium text-gray-500">
                            Last Name
                          </label>
                          <input
                            type="text"
                            value={editForm.last_name}
                            onChange={(e) =>
                              setEditForm({ ...editForm, last_name: e.target.value })
                            }
                            className="block w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:border-companion-blue-light focus:outline-none focus:ring-1 focus:ring-companion-blue-light"
                          />
                        </div>
                        <div>
                          <label className="mb-1 block text-xs font-medium text-gray-500">
                            Preferred Name
                          </label>
                          <input
                            type="text"
                            value={editForm.preferred_name}
                            onChange={(e) =>
                              setEditForm({ ...editForm, preferred_name: e.target.value })
                            }
                            placeholder="What D.D. calls them"
                            className="block w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:border-companion-blue-light focus:outline-none focus:ring-1 focus:ring-companion-blue-light"
                          />
                        </div>
                        <div>
                          <label className="mb-1 block text-xs font-medium text-gray-500">
                            Phone
                          </label>
                          <input
                            type="tel"
                            value={editForm.phone}
                            onChange={(e) =>
                              setEditForm({ ...editForm, phone: e.target.value })
                            }
                            className="block w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:border-companion-blue-light focus:outline-none focus:ring-1 focus:ring-companion-blue-light"
                          />
                        </div>
                        <div>
                          <label className="mb-1 block text-xs font-medium text-gray-500">
                            Email
                          </label>
                          <input
                            type="email"
                            value={person.email}
                            readOnly
                            className="block w-full rounded-md border border-gray-200 bg-gray-50 px-3 py-1.5 text-sm text-gray-500 cursor-not-allowed"
                          />
                        </div>
                      </div>
                    </div>

                    {/* Roles Section */}
                    <div className="rounded-lg border border-gray-200 bg-white p-4">
                      <h3 className="mb-3 text-xs font-bold uppercase tracking-wide text-gray-500">
                        Roles
                      </h3>
                      <div className="flex items-center gap-6">
                        {person.is_user && (
                          <span className="inline-flex items-center rounded-full bg-emerald-100 px-3 py-1 text-xs font-medium text-emerald-800">
                            Companion User
                          </span>
                        )}
                        <label className="flex items-center gap-2 text-sm text-gray-700">
                          <input
                            type="checkbox"
                            checked={editForm.is_admin}
                            onChange={(e) =>
                              setEditForm({ ...editForm, is_admin: e.target.checked })
                            }
                            className="rounded border-gray-300 text-companion-blue focus:ring-companion-blue-light"
                          />
                          Admin
                        </label>
                        {editForm.is_admin && (
                          <select
                            value={editForm.admin_role}
                            onChange={(e) =>
                              setEditForm({ ...editForm, admin_role: e.target.value })
                            }
                            className="rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:border-companion-blue-light focus:outline-none focus:ring-1 focus:ring-companion-blue-light"
                          >
                            {ADMIN_ROLES.map((r) => (
                              <option key={r.value} value={r.value}>
                                {r.label}
                              </option>
                            ))}
                          </select>
                        )}
                      </div>
                    </div>

                    {/* Save button for profile + roles */}
                    <div className="flex items-center gap-3">
                      <button
                        type="button"
                        onClick={() => handleSave(person.email)}
                        disabled={updateMutation.isPending}
                        className="rounded-md bg-companion-blue px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-companion-blue-mid disabled:cursor-not-allowed disabled:opacity-50"
                      >
                        {updateMutation.isPending ? 'Saving...' : 'Save Changes'}
                      </button>
                      {updateMutation.isSuccess && (
                        <span className="text-xs text-emerald-600">Saved</span>
                      )}
                      {updateMutation.isError && (
                        <span className="text-xs text-companion-rose">Save failed</span>
                      )}
                    </div>

                    {/* Caregiver Assignments Section */}
                    <div className="rounded-lg border border-gray-200 bg-white p-4">
                      <h3 className="mb-3 text-xs font-bold uppercase tracking-wide text-gray-500">
                        Caregiver Assignments
                      </h3>
                      {assignments.length > 0 ? (
                        <div className="space-y-2">
                          {assignments.map((a) => (
                            <div
                              key={a.contact_id}
                              className="flex items-center justify-between rounded-md bg-gray-50 px-4 py-2.5 ring-1 ring-gray-100"
                            >
                              <div className="flex min-w-0 flex-1 items-center gap-3">
                                <span className="text-sm font-medium text-gray-800">
                                  Caregiver for {a.user_name}
                                </span>
                                <span className="text-sm text-gray-500">
                                  as {a.contact_name}
                                </span>
                                <span className="inline-flex items-center rounded-full bg-sky-100 px-2 py-0.5 text-xs font-medium text-sky-800">
                                  {relationshipLabel(a.relationship)}
                                </span>
                                <span className="inline-flex items-center rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-700">
                                  {tierLabel(a.tier)}
                                </span>
                                {!a.is_active && (
                                  <span className="inline-flex items-center rounded-full bg-yellow-100 px-2 py-0.5 text-xs font-medium text-yellow-800">
                                    Inactive
                                  </span>
                                )}
                              </div>
                              <button
                                type="button"
                                onClick={() => removeCaregiverMutation.mutate(a.contact_id)}
                                disabled={removeCaregiverMutation.isPending}
                                className="ml-3 flex-shrink-0 text-sm text-gray-400 transition-colors hover:text-companion-rose disabled:opacity-50"
                                title="Remove assignment"
                              >
                                &#10005;
                              </button>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <p className="text-sm text-gray-400">No caregiver assignments.</p>
                      )}

                      {/* Assign as caregiver */}
                      {assigningEmail !== person.email ? (
                        <button
                          type="button"
                          onClick={() => {
                            setAssigningEmail(person.email)
                            setNewAssignment({
                              user_id: '',
                              contact_name: person.display_name || person.first_name || person.email,
                              relationship: 'family',
                              tier: 'tier_1',
                            })
                          }}
                          className="mt-3 inline-flex items-center gap-1.5 rounded-md bg-companion-blue px-3 py-1.5 text-xs font-medium text-white transition-colors hover:bg-companion-blue-mid"
                        >
                          <span className="text-sm leading-none">+</span>
                          Assign as Caregiver
                        </button>
                      ) : (
                        <div className="mt-3 rounded-md border border-gray-200 bg-gray-50 p-4">
                          <div className="flex flex-wrap items-end gap-3">
                            <div className="min-w-[200px] flex-1">
                              <label className="mb-1 block text-xs font-medium text-gray-600">
                                User (care recipient)
                              </label>
                              <select
                                value={newAssignment.user_id}
                                onChange={(e) =>
                                  setNewAssignment({ ...newAssignment, user_id: e.target.value })
                                }
                                className="block w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:border-companion-blue-light focus:outline-none focus:ring-1 focus:ring-companion-blue-light"
                              >
                                <option value="">Select a user...</option>
                                {userOptions.map((u) => (
                                  <option key={u.id} value={u.id}>
                                    {u.name} ({u.email})
                                  </option>
                                ))}
                              </select>
                            </div>
                            <div className="min-w-[150px]">
                              <label className="mb-1 block text-xs font-medium text-gray-600">
                                Contact Name
                              </label>
                              <input
                                type="text"
                                value={newAssignment.contact_name}
                                onChange={(e) =>
                                  setNewAssignment({ ...newAssignment, contact_name: e.target.value })
                                }
                                className="block w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:border-companion-blue-light focus:outline-none focus:ring-1 focus:ring-companion-blue-light"
                              />
                            </div>
                            <div className="min-w-[150px]">
                              <label className="mb-1 block text-xs font-medium text-gray-600">
                                Relationship
                              </label>
                              <select
                                value={newAssignment.relationship}
                                onChange={(e) =>
                                  setNewAssignment({ ...newAssignment, relationship: e.target.value })
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
                                value={newAssignment.tier}
                                onChange={(e) =>
                                  setNewAssignment({ ...newAssignment, tier: e.target.value })
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
                                onClick={() => handleAddCaregiver(person.email)}
                                disabled={
                                  addCaregiverMutation.isPending || !newAssignment.user_id
                                }
                                className="rounded-md bg-companion-blue px-4 py-1.5 text-sm font-medium text-white transition-colors hover:bg-companion-blue-mid disabled:cursor-not-allowed disabled:opacity-50"
                              >
                                {addCaregiverMutation.isPending ? 'Saving...' : 'Save'}
                              </button>
                              <button
                                type="button"
                                onClick={() => setAssigningEmail(null)}
                                className="rounded-md px-3 py-1.5 text-sm font-medium text-gray-500 transition-colors hover:text-gray-700"
                              >
                                Cancel
                              </button>
                            </div>
                          </div>
                          {addCaregiverMutation.isError && (
                            <p className="mt-2 text-xs text-companion-rose">
                              Failed to assign caregiver. Please try again.
                            </p>
                          )}
                        </div>
                      )}
                    </div>
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
