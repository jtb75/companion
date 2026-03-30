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
  invitation_status?: string
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
  care_model: string | null
  account_status: string | null
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
  return RELATIONSHIPS.find((r) => r.value === value.toLowerCase())?.label ?? value
}

function tierLabel(value: string): string {
  return TIERS.find((t) => t.value === value.toLowerCase())?.label ?? value
}

function statusBadge(status: string | null) {
  if (!status || status === 'active') return null
  const colors: Record<string, string> = {
    invited: 'bg-amber-100 text-amber-800',
    deactivated: 'bg-gray-200 text-gray-600',
    pending_deletion: 'bg-red-100 text-red-800',
  }
  const labels: Record<string, string> = {
    invited: 'Invited',
    deactivated: 'Deactivated',
    pending_deletion: 'Pending Deletion',
  }
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${colors[status] || 'bg-gray-100 text-gray-600'}`}>
      {labels[status] || status}
    </span>
  )
}

// ---------------------------------------------------------------------------
// Drawer component
// ---------------------------------------------------------------------------

function PersonDrawer({
  person,
  userOptions,
  onClose,
}: {
  person: Person
  userOptions: UserOption[]
  onClose: () => void
}) {
  const queryClient = useQueryClient()
  const assignments = Array.isArray(person.caregiver_for) ? person.caregiver_for : []

  const [editForm, setEditForm] = useState({
    first_name: person.first_name || '',
    last_name: person.last_name || '',
    preferred_name: person.preferred_name || '',
    phone: person.phone || '',
    is_admin: person.is_admin,
    admin_role: person.admin_role || 'viewer',
    care_model: person.care_model || 'self_directed',
  })

  const [showAssignForm, setShowAssignForm] = useState(false)
  const [newAssignment, setNewAssignment] = useState({
    user_id: '',
    contact_name: person.display_name || person.first_name || person.email,
    relationship: 'family',
    tier: 'tier_1',
  })

  const [deleteStep, setDeleteStep] = useState<'none' | 'confirm-deactivate' | 'confirm-delete'>('none')

  const updateMutation = useMutation({
    mutationFn: (data: Record<string, unknown>) =>
      api(`/admin/people/${encodeURIComponent(person.email)}`, {
        method: 'PATCH',
        body: JSON.stringify(data),
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['admin-people'] }),
  })

  const addCaregiverMutation = useMutation({
    mutationFn: (data: Record<string, string>) =>
      api(`/admin/people/${encodeURIComponent(person.email)}/caregiver`, {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-people'] })
      setShowAssignForm(false)
      setNewAssignment({ user_id: '', contact_name: person.display_name || '', relationship: 'family', tier: 'tier_1' })
    },
  })

  const removeCaregiverMutation = useMutation({
    mutationFn: (contactId: string) =>
      api(`/admin/people/caregiver/${contactId}`, { method: 'DELETE' }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['admin-people'] }),
  })

  const deactivateMutation = useMutation({
    mutationFn: () =>
      api(`/admin/companion-users/${person.id}/deactivate`, { method: 'POST' }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-people'] })
      setDeleteStep('none')
    },
  })

  const reactivateMutation = useMutation({
    mutationFn: () =>
      api(`/admin/companion-users/${person.id}/reactivate`, { method: 'POST' }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['admin-people'] }),
  })

  const requestDeletionMutation = useMutation({
    mutationFn: () =>
      api(`/admin/companion-users/${person.id}/request-deletion`, { method: 'POST' }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-people'] })
      setDeleteStep('none')
    },
  })

  const cancelDeletionMutation = useMutation({
    mutationFn: () =>
      api(`/admin/companion-users/${person.id}/cancel-deletion`, { method: 'POST' }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['admin-people'] }),
  })

  const deleteMutation = useMutation({
    mutationFn: () =>
      api(`/admin/companion-users/${person.id}`, { method: 'DELETE' }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-people'] })
      onClose()
    },
  })

  const handleSave = () => {
    updateMutation.mutate({
      first_name: editForm.first_name,
      last_name: editForm.last_name,
      preferred_name: editForm.preferred_name,
      phone: editForm.phone,
      is_admin: editForm.is_admin,
      admin_role: editForm.admin_role,
      care_model: editForm.care_model,
    })
  }

  const isDeactivated = person.account_status === 'deactivated'
  const isPendingDeletion = person.account_status === 'pending_deletion'

  return (
    <>
      {/* Backdrop */}
      <div className="fixed inset-0 z-40 bg-black/30" onClick={onClose} />

      {/* Drawer */}
      <div className="fixed inset-y-0 right-0 z-50 flex w-full max-w-lg flex-col bg-white shadow-xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-gray-200 px-6 py-4">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">
              {person.display_name || person.first_name || person.email}
            </h2>
            <p className="text-sm text-gray-500">{person.email}</p>
          </div>
          <button
            onClick={onClose}
            className="rounded-md p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
          >
            <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Scrollable content */}
        <div className="flex-1 overflow-y-auto px-6 py-5 space-y-6">
          {/* Status badges */}
          <div className="flex items-center gap-2 flex-wrap">
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
            {statusBadge(person.account_status)}
            {person.care_model === 'managed' && (
              <span className="inline-flex items-center rounded-full bg-purple-100 px-2.5 py-0.5 text-xs font-medium text-purple-800">
                Managed
              </span>
            )}
          </div>

          {/* Profile */}
          <section>
            <h3 className="mb-3 text-xs font-bold uppercase tracking-wide text-gray-500">Profile</h3>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="mb-1 block text-xs font-medium text-gray-500">First Name</label>
                <input
                  type="text"
                  value={editForm.first_name}
                  onChange={(e) => setEditForm({ ...editForm, first_name: e.target.value })}
                  className="block w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:border-companion-blue-light focus:outline-none focus:ring-1 focus:ring-companion-blue-light"
                />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-gray-500">Last Name</label>
                <input
                  type="text"
                  value={editForm.last_name}
                  onChange={(e) => setEditForm({ ...editForm, last_name: e.target.value })}
                  className="block w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:border-companion-blue-light focus:outline-none focus:ring-1 focus:ring-companion-blue-light"
                />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-gray-500">Preferred Name</label>
                <input
                  type="text"
                  value={editForm.preferred_name}
                  onChange={(e) => setEditForm({ ...editForm, preferred_name: e.target.value })}
                  placeholder="What D.D. calls them"
                  className="block w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:border-companion-blue-light focus:outline-none focus:ring-1 focus:ring-companion-blue-light"
                />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-gray-500">Phone</label>
                <input
                  type="tel"
                  value={editForm.phone}
                  onChange={(e) => setEditForm({ ...editForm, phone: e.target.value })}
                  className="block w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:border-companion-blue-light focus:outline-none focus:ring-1 focus:ring-companion-blue-light"
                />
              </div>
            </div>
          </section>

          {/* Roles */}
          <section>
            <h3 className="mb-3 text-xs font-bold uppercase tracking-wide text-gray-500">Roles</h3>
            <div className="flex items-center gap-4 flex-wrap">
              <label className="flex items-center gap-2 text-sm text-gray-700">
                <input
                  type="checkbox"
                  checked={editForm.is_admin}
                  onChange={(e) => setEditForm({ ...editForm, is_admin: e.target.checked })}
                  className="rounded border-gray-300 text-companion-blue focus:ring-companion-blue-light"
                />
                Admin
              </label>
              {editForm.is_admin && (
                <select
                  value={editForm.admin_role}
                  onChange={(e) => setEditForm({ ...editForm, admin_role: e.target.value })}
                  className="rounded-md border border-gray-300 px-3 py-1.5 text-sm"
                >
                  {ADMIN_ROLES.map((r) => <option key={r.value} value={r.value}>{r.label}</option>)}
                </select>
              )}
            </div>
            {person.is_user && (
              <div className="mt-3 flex items-center gap-4">
                <label className="text-xs font-medium text-gray-500">Care Model</label>
                <select
                  value={editForm.care_model}
                  onChange={(e) => setEditForm({ ...editForm, care_model: e.target.value })}
                  className="rounded-md border border-gray-300 px-3 py-1.5 text-sm"
                >
                  <option value="self_directed">Self-Directed</option>
                  <option value="managed">Managed</option>
                </select>
              </div>
            )}
          </section>

          {/* Save */}
          <div className="flex items-center gap-3">
            <button
              onClick={handleSave}
              disabled={updateMutation.isPending}
              className="rounded-md bg-companion-blue px-4 py-2 text-sm font-medium text-white hover:bg-companion-blue-mid disabled:opacity-50"
            >
              {updateMutation.isPending ? 'Saving...' : 'Save Changes'}
            </button>
            {updateMutation.isSuccess && <span className="text-xs text-emerald-600">Saved</span>}
            {updateMutation.isError && <span className="text-xs text-companion-rose">Save failed</span>}
          </div>

          {/* Caregiver Assignments */}
          <section>
            <h3 className="mb-3 text-xs font-bold uppercase tracking-wide text-gray-500">Caregiver Assignments</h3>
            {assignments.length > 0 ? (
              <div className="space-y-2">
                {assignments.map((a) => (
                  <div key={a.contact_id} className="flex items-center justify-between rounded-md bg-gray-50 px-3 py-2 ring-1 ring-gray-100">
                    <div className="flex items-center gap-2 flex-wrap min-w-0">
                      <span className="text-sm font-medium text-gray-800">for {a.user_name}</span>
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
                      onClick={() => removeCaregiverMutation.mutate(a.contact_id)}
                      disabled={removeCaregiverMutation.isPending}
                      className="ml-2 text-gray-400 hover:text-companion-rose"
                      title="Remove"
                    >
                      &#10005;
                    </button>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-gray-400">No caregiver assignments.</p>
            )}

            {!showAssignForm ? (
              <button
                onClick={() => setShowAssignForm(true)}
                className="mt-3 inline-flex items-center gap-1.5 rounded-md bg-companion-blue px-3 py-1.5 text-xs font-medium text-white hover:bg-companion-blue-mid"
              >
                + Assign as Caregiver
              </button>
            ) : (
              <div className="mt-3 rounded-md border border-gray-200 bg-gray-50 p-4 space-y-3">
                <div>
                  <label className="mb-1 block text-xs font-medium text-gray-600">Member</label>
                  <select
                    value={newAssignment.user_id}
                    onChange={(e) => setNewAssignment({ ...newAssignment, user_id: e.target.value })}
                    className="block w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm"
                  >
                    <option value="">Select a member...</option>
                    {userOptions.map((u) => <option key={u.id} value={u.id}>{u.name} ({u.email})</option>)}
                  </select>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="mb-1 block text-xs font-medium text-gray-600">Relationship</label>
                    <select
                      value={newAssignment.relationship}
                      onChange={(e) => setNewAssignment({ ...newAssignment, relationship: e.target.value })}
                      className="block w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm"
                    >
                      {RELATIONSHIPS.map((r) => <option key={r.value} value={r.value}>{r.label}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="mb-1 block text-xs font-medium text-gray-600">Access Tier</label>
                    <select
                      value={newAssignment.tier}
                      onChange={(e) => setNewAssignment({ ...newAssignment, tier: e.target.value })}
                      className="block w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm"
                    >
                      {TIERS.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
                    </select>
                  </div>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => addCaregiverMutation.mutate({
                      user_id: newAssignment.user_id,
                      contact_name: newAssignment.contact_name || person.email,
                      relationship: newAssignment.relationship,
                      tier: newAssignment.tier,
                    })}
                    disabled={addCaregiverMutation.isPending || !newAssignment.user_id}
                    className="rounded-md bg-companion-blue px-4 py-1.5 text-sm font-medium text-white hover:bg-companion-blue-mid disabled:opacity-50"
                  >
                    {addCaregiverMutation.isPending ? 'Saving...' : 'Save'}
                  </button>
                  <button onClick={() => setShowAssignForm(false)} className="px-3 py-1.5 text-sm text-gray-500 hover:text-gray-700">
                    Cancel
                  </button>
                </div>
                {addCaregiverMutation.isError && (
                  <p className="text-xs text-companion-rose">Failed to assign caregiver.</p>
                )}
              </div>
            )}
          </section>

          {/* Account Actions */}
          {person.is_user && person.id && (
            <section className="border-t border-gray-200 pt-5">
              <h3 className="mb-3 text-xs font-bold uppercase tracking-wide text-gray-500">Account Actions</h3>

              {/* Reactivate */}
              {(isDeactivated || isPendingDeletion) && (
                <div className="mb-3">
                  {isPendingDeletion && (
                    <button
                      onClick={() => cancelDeletionMutation.mutate()}
                      disabled={cancelDeletionMutation.isPending}
                      className="mr-2 rounded-md bg-amber-500 px-4 py-2 text-sm font-medium text-white hover:bg-amber-600 disabled:opacity-50"
                    >
                      {cancelDeletionMutation.isPending ? 'Cancelling...' : 'Cancel Deletion'}
                    </button>
                  )}
                  {isDeactivated && (
                    <button
                      onClick={() => reactivateMutation.mutate()}
                      disabled={reactivateMutation.isPending}
                      className="rounded-md bg-emerald-500 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-600 disabled:opacity-50"
                    >
                      {reactivateMutation.isPending ? 'Reactivating...' : 'Reactivate Account'}
                    </button>
                  )}
                </div>
              )}

              {/* Deactivate / Delete */}
              {deleteStep === 'none' && !isPendingDeletion && (
                <div className="flex gap-2">
                  {!isDeactivated && (
                    <button
                      onClick={() => setDeleteStep('confirm-deactivate')}
                      className="rounded-md border border-amber-300 px-4 py-2 text-sm font-medium text-amber-700 hover:bg-amber-50"
                    >
                      Deactivate
                    </button>
                  )}
                  <button
                    onClick={() => setDeleteStep('confirm-delete')}
                    className="rounded-md border border-red-300 px-4 py-2 text-sm font-medium text-red-700 hover:bg-red-50"
                  >
                    {isDeactivated ? 'Delete Account' : 'Request Deletion'}
                  </button>
                </div>
              )}

              {/* Deactivate confirmation */}
              {deleteStep === 'confirm-deactivate' && (
                <div className="rounded-md border border-amber-200 bg-amber-50 p-4">
                  <p className="text-sm text-amber-800 mb-3">
                    Deactivating will block all access and notify caregivers. The account can be reactivated later.
                  </p>
                  <div className="flex gap-2">
                    <button
                      onClick={() => deactivateMutation.mutate()}
                      disabled={deactivateMutation.isPending}
                      className="rounded-md bg-amber-500 px-4 py-2 text-sm font-medium text-white hover:bg-amber-600 disabled:opacity-50"
                    >
                      {deactivateMutation.isPending ? 'Deactivating...' : 'Confirm Deactivate'}
                    </button>
                    <button onClick={() => setDeleteStep('none')} className="px-4 py-2 text-sm text-gray-500 hover:text-gray-700">
                      Cancel
                    </button>
                  </div>
                </div>
              )}

              {/* Delete confirmation */}
              {deleteStep === 'confirm-delete' && (
                <div className="rounded-md border border-red-200 bg-red-50 p-4">
                  {isDeactivated ? (
                    <>
                      <p className="text-sm text-red-800 mb-3">
                        This will permanently delete the account and all associated data. This action cannot be undone.
                      </p>
                      <div className="flex gap-2">
                        <button
                          onClick={() => deleteMutation.mutate()}
                          disabled={deleteMutation.isPending}
                          className="rounded-md bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-50"
                        >
                          {deleteMutation.isPending ? 'Deleting...' : 'Permanently Delete'}
                        </button>
                        <button onClick={() => setDeleteStep('none')} className="px-4 py-2 text-sm text-gray-500 hover:text-gray-700">
                          Cancel
                        </button>
                      </div>
                    </>
                  ) : (
                    <>
                      <p className="text-sm text-red-800 mb-3">
                        This will schedule the account for deletion in 30 days. The account will be deactivated immediately. During the grace period, the deletion can be cancelled.
                      </p>
                      <div className="flex gap-2">
                        <button
                          onClick={() => requestDeletionMutation.mutate()}
                          disabled={requestDeletionMutation.isPending}
                          className="rounded-md bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-50"
                        >
                          {requestDeletionMutation.isPending ? 'Requesting...' : 'Request Deletion'}
                        </button>
                        <button onClick={() => setDeleteStep('none')} className="px-4 py-2 text-sm text-gray-500 hover:text-gray-700">
                          Cancel
                        </button>
                      </div>
                    </>
                  )}
                  {(deleteMutation.isError || requestDeletionMutation.isError) && (
                    <p className="mt-2 text-xs text-red-600">Operation failed. Please try again.</p>
                  )}
                </div>
              )}

              {(deactivateMutation.isError || reactivateMutation.isError || cancelDeletionMutation.isError) && (
                <p className="mt-2 text-xs text-companion-rose">Action failed. Please try again.</p>
              )}
            </section>
          )}

          {/* Metadata */}
          {person.created_at && (
            <section className="border-t border-gray-200 pt-4">
              <p className="text-xs text-gray-400">
                Created {new Date(person.created_at).toLocaleDateString()}
              </p>
            </section>
          )}
        </div>
      </div>
    </>
  )
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export function PeoplePage() {
  const queryClient = useQueryClient()
  const [search, setSearch] = useState('')
  const [selectedPerson, setSelectedPerson] = useState<Person | null>(null)
  const [showAddForm, setShowAddForm] = useState(false)

  const [newPerson, setNewPerson] = useState({
    email: '',
    first_name: '',
    last_name: '',
    phone: '',
    is_user: true,
    is_admin: false,
    admin_role: 'viewer',
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
    return name.includes(searchLower) || email.includes(searchLower) || roles.join(' ').includes(searchLower)
  })

  const createMutation = useMutation({
    mutationFn: (data: typeof newPerson) =>
      api('/admin/people', { method: 'POST', body: JSON.stringify(data) }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-people'] })
      queryClient.invalidateQueries({ queryKey: ['admin-users-list'] })
      setShowAddForm(false)
      setNewPerson({ email: '', first_name: '', last_name: '', phone: '', is_user: true, is_admin: false, admin_role: 'viewer' })
    },
  })

  // Keep drawer in sync with refreshed data
  const drawerPerson = selectedPerson
    ? people.find((p) => p.email === selectedPerson.email) || selectedPerson
    : null

  if (isLoading) {
    return <p className="text-gray-500 p-6">Loading people...</p>
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-900">People</h1>
        <button
          onClick={() => setShowAddForm(!showAddForm)}
          className="inline-flex items-center gap-1.5 rounded-md bg-companion-blue px-4 py-2 text-sm font-medium text-white hover:bg-companion-blue-mid"
        >
          + Add Person
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
              <input type="text" value={newPerson.first_name} onChange={(e) => setNewPerson({ ...newPerson, first_name: e.target.value })} className="block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-companion-blue-light focus:outline-none focus:ring-1 focus:ring-companion-blue-light" />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-600">Last Name</label>
              <input type="text" value={newPerson.last_name} onChange={(e) => setNewPerson({ ...newPerson, last_name: e.target.value })} className="block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-companion-blue-light focus:outline-none focus:ring-1 focus:ring-companion-blue-light" />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-600">Phone</label>
              <input type="tel" value={newPerson.phone} onChange={(e) => setNewPerson({ ...newPerson, phone: e.target.value })} className="block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-companion-blue-light focus:outline-none focus:ring-1 focus:ring-companion-blue-light" />
            </div>
          </div>
          <div className="mt-4 flex items-center gap-6">
            <label className="flex items-center gap-2 text-sm text-gray-700">
              <input type="checkbox" checked={newPerson.is_user} onChange={(e) => setNewPerson({ ...newPerson, is_user: e.target.checked })} className="rounded border-gray-300 text-companion-blue" />
              Create as User
            </label>
            <label className="flex items-center gap-2 text-sm text-gray-700">
              <input type="checkbox" checked={newPerson.is_admin} onChange={(e) => setNewPerson({ ...newPerson, is_admin: e.target.checked })} className="rounded border-gray-300 text-companion-blue" />
              Create as Admin
            </label>
            {newPerson.is_admin && (
              <select value={newPerson.admin_role} onChange={(e) => setNewPerson({ ...newPerson, admin_role: e.target.value })} className="rounded-md border border-gray-300 px-3 py-1.5 text-sm">
                {ADMIN_ROLES.map((r) => <option key={r.value} value={r.value}>{r.label}</option>)}
              </select>
            )}
          </div>
          <div className="mt-4 flex items-center gap-2">
            <button
              onClick={() => createMutation.mutate(newPerson)}
              disabled={createMutation.isPending || !newPerson.email.trim()}
              className="rounded-md bg-companion-blue px-4 py-2 text-sm font-medium text-white hover:bg-companion-blue-mid disabled:opacity-50"
            >
              {createMutation.isPending ? 'Creating...' : 'Create'}
            </button>
            <button onClick={() => setShowAddForm(false)} className="px-4 py-2 text-sm text-gray-500 hover:text-gray-700">Cancel</button>
          </div>
          {createMutation.isError && (
            <p className="mt-2 text-xs text-companion-rose">Failed to create person. Please check the email is unique and try again.</p>
          )}
        </div>
      )}

      {/* Search */}
      <div className="relative">
        <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3">
          <svg className="h-5 w-5 text-gray-400" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M9 3.5a5.5 5.5 0 100 11 5.5 5.5 0 000-11zM2 9a7 7 0 1112.452 4.391l3.328 3.329a.75.75 0 11-1.06 1.06l-3.329-3.328A7 7 0 012 9z" clipRule="evenodd" />
          </svg>
        </div>
        <input
          type="text"
          placeholder="Search by name, email, or role..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="block w-full rounded-lg border border-gray-300 bg-white py-2.5 pl-10 pr-4 text-sm placeholder-gray-400 focus:border-companion-blue-light focus:outline-none focus:ring-2 focus:ring-companion-blue-light"
        />
      </div>

      <p className="text-xs text-gray-400">{filteredPeople.length} of {people.length} people</p>

      {/* People list */}
      <div className="overflow-hidden rounded-lg border border-gray-200 bg-white shadow-sm">
        {filteredPeople.length === 0 ? (
          <div className="px-6 py-12 text-center text-sm text-gray-400">No people found</div>
        ) : (
          filteredPeople.map((person) => {
            const assignments = Array.isArray(person.caregiver_for) ? person.caregiver_for : []
            return (
              <button
                key={person.email}
                type="button"
                onClick={() => setSelectedPerson(person)}
                className="flex w-full items-center justify-between border-b border-gray-100 px-5 py-3.5 text-left transition-colors hover:bg-gray-50 last:border-b-0"
              >
                <div className="min-w-0 flex-1">
                  <span className="text-sm font-medium text-gray-900">
                    {person.display_name || person.first_name || person.email}
                  </span>
                  <span className="ml-3 text-sm text-gray-500">{person.email}</span>
                </div>
                <div className="ml-4 flex items-center gap-2">
                  {person.is_user && (
                    <span className="inline-flex items-center rounded-full bg-emerald-100 px-2.5 py-0.5 text-xs font-medium text-emerald-800">User</span>
                  )}
                  {person.is_admin && (
                    <span className="inline-flex items-center rounded-full bg-red-100 px-2.5 py-0.5 text-xs font-medium text-red-800">
                      Admin{person.admin_role ? ` (${person.admin_role})` : ''}
                    </span>
                  )}
                  {statusBadge(person.account_status)}
                  {assignments.length > 0 && (
                    <span className="inline-flex items-center rounded-full bg-sky-100 px-2.5 py-0.5 text-xs font-medium text-sky-800">
                      Caregiver ({assignments.length})
                    </span>
                  )}
                </div>
              </button>
            )
          })
        )}
      </div>

      {/* Drawer */}
      {drawerPerson && (
        <PersonDrawer
          person={drawerPerson}
          userOptions={userOptions}
          onClose={() => setSelectedPerson(null)}
        />
      )}
    </div>
  )
}
