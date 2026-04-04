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
  status?: string
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
  caregivers: { contact_id: string; caregiver_name: string; caregiver_email: string; relationship: string; tier: string; is_active: boolean; status?: string }[]
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
// Assignment row (reusable)
// ---------------------------------------------------------------------------

function AssignmentRow({
  label, relationship, tier, status, isActive, contactId,
  onApprove, onRemove, approving, removing,
}: {
  label: string; relationship: string; tier: string; status?: string; isActive: boolean
  contactId: string; onApprove: (id: string) => void; onRemove: (id: string) => void
  approving: boolean; removing: boolean
}) {
  return (
    <div className="flex items-center justify-between rounded-md bg-gray-50 px-3 py-2 ring-1 ring-gray-100">
      <div className="flex items-center gap-2 flex-wrap min-w-0">
        <span className="text-sm font-medium text-gray-800">{label}</span>
        <span className="inline-flex items-center rounded-full bg-sky-100 px-2 py-0.5 text-xs font-medium text-sky-800">{relationshipLabel(relationship)}</span>
        <span className="inline-flex items-center rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-700">{tierLabel(tier)}</span>
        {status === 'pending_approval' && <span className="inline-flex items-center rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800">Pending</span>}
        {!isActive && status !== 'pending_approval' && <span className="inline-flex items-center rounded-full bg-yellow-100 px-2 py-0.5 text-xs font-medium text-yellow-800">Inactive</span>}
      </div>
      <div className="flex items-center gap-1.5 ml-2">
        {status === 'pending_approval' && (
          <button onClick={() => onApprove(contactId)} disabled={approving} className="rounded border border-emerald-300 p-1 text-emerald-600 hover:bg-emerald-50 hover:text-emerald-800" title="Approve">
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" /></svg>
          </button>
        )}
        <button onClick={() => onRemove(contactId)} disabled={removing} className="rounded border border-red-200 p-1 text-gray-400 hover:bg-red-50 hover:text-red-600" title="Remove">
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>
        </button>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Edit Profile Modal
// ---------------------------------------------------------------------------

function EditProfileModal({ person, onClose }: { person: Person; onClose: () => void }) {
  const queryClient = useQueryClient()
  const [editForm, setEditForm] = useState({
    first_name: person.first_name || '', last_name: person.last_name || '',
    preferred_name: person.preferred_name || '', phone: person.phone || '',
    is_admin: person.is_admin, admin_role: person.admin_role || 'viewer',
    care_model: person.care_model || 'self_directed',
  })
  const [deleteStep, setDeleteStep] = useState<'none' | 'confirm-deactivate' | 'confirm-delete'>('none')
  const [graceDays, setGraceDays] = useState(30)

  const { } = useQuery({
    queryKey: ['config-deletion-settings'],
    queryFn: async () => {
      const data = await api<{ entries: { category: string; key: string; value: { days: number } }[] }>('/admin/config')
      const match = data.entries.find((e) => e.category.toLowerCase() === 'deletion_settings' && e.key === 'grace_period_days')
      if (match) setGraceDays(match.value.days ?? 30)
      return match
    },
  })

  const updateMutation = useMutation({
    mutationFn: (data: Record<string, unknown>) => api(`/admin/people/${person.id}`, { method: 'PATCH', body: JSON.stringify(data) }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['admin-people'] }),
  })
  const deactivateMutation = useMutation({
    mutationFn: () => api(`/admin/companion-users/${person.id}/deactivate`, { method: 'POST' }),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['admin-people'] }); setDeleteStep('none') },
  })
  const reactivateMutation = useMutation({
    mutationFn: () => api(`/admin/companion-users/${person.id}/reactivate`, { method: 'POST' }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['admin-people'] }),
  })
  const requestDeletionMutation = useMutation({
    mutationFn: () => api(`/admin/companion-users/${person.id}/request-deletion`, { method: 'POST' }),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['admin-people'] }); setDeleteStep('none') },
  })
  const cancelDeletionMutation = useMutation({
    mutationFn: () => api(`/admin/companion-users/${person.id}/cancel-deletion`, { method: 'POST' }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['admin-people'] }),
  })
  const deleteMutation = useMutation({
    mutationFn: () => api(`/admin/companion-users/${person.id}`, { method: 'DELETE' }),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['admin-people'] }); onClose() },
  })

  const isDeactivated = person.account_status === 'deactivated'
  const isPendingDeletion = person.account_status === 'pending_deletion'

  const inputClass = "block w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:border-companion-blue-light focus:outline-none focus:ring-1 focus:ring-companion-blue-light"

  return (
    <>
      <div className="fixed inset-0 z-40 bg-black/30" onClick={onClose} />
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div className="w-full max-w-lg rounded-xl bg-white shadow-xl max-h-[90vh] overflow-y-auto">
          {/* Header */}
          <div className="flex items-center justify-between border-b border-gray-200 px-6 py-4">
            <div>
              <h2 className="text-lg font-semibold text-gray-900">{person.display_name || person.email}</h2>
              <p className="text-sm text-gray-500">{person.email}</p>
            </div>
            <button onClick={onClose} className="rounded-md p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600">
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" /></svg>
            </button>
          </div>

          <div className="px-6 py-5 space-y-5">
            {/* Profile fields */}
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="mb-1 block text-xs font-medium text-gray-500">First Name</label>
                <input type="text" value={editForm.first_name} onChange={(e) => setEditForm({ ...editForm, first_name: e.target.value })} className={inputClass} />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-gray-500">Last Name</label>
                <input type="text" value={editForm.last_name} onChange={(e) => setEditForm({ ...editForm, last_name: e.target.value })} className={inputClass} />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-gray-500">Preferred Name</label>
                <input type="text" value={editForm.preferred_name} onChange={(e) => setEditForm({ ...editForm, preferred_name: e.target.value })} placeholder="What D.D. calls them" className={inputClass} />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-gray-500">Phone</label>
                <input type="tel" value={editForm.phone} onChange={(e) => setEditForm({ ...editForm, phone: e.target.value })} className={inputClass} />
              </div>
            </div>

            {/* Roles */}
            <div className="flex items-center gap-4 flex-wrap">
              <label className="flex items-center gap-2 text-sm text-gray-700">
                <input type="checkbox" checked={editForm.is_admin} onChange={(e) => setEditForm({ ...editForm, is_admin: e.target.checked })} className="rounded border-gray-300 text-companion-blue" />
                Admin
              </label>
              {editForm.is_admin && (
                <select value={editForm.admin_role} onChange={(e) => setEditForm({ ...editForm, admin_role: e.target.value })} className="rounded-md border border-gray-300 px-3 py-1.5 text-sm">
                  {ADMIN_ROLES.map((r) => <option key={r.value} value={r.value}>{r.label}</option>)}
                </select>
              )}
              {person.is_user && (
                <>
                  <span className="text-gray-300">|</span>
                  <label className="text-xs font-medium text-gray-500">Care Model</label>
                  <select value={editForm.care_model} onChange={(e) => setEditForm({ ...editForm, care_model: e.target.value })} className="rounded-md border border-gray-300 px-3 py-1.5 text-sm">
                    <option value="self_directed">Self-Directed</option>
                    <option value="managed">Managed</option>
                  </select>
                </>
              )}
            </div>

            {/* Save */}
            <div className="flex items-center gap-3">
              <button onClick={() => updateMutation.mutate(editForm)} disabled={updateMutation.isPending} className="rounded-md bg-companion-blue px-4 py-2 text-sm font-medium text-white hover:bg-companion-blue-mid disabled:opacity-50">
                {updateMutation.isPending ? 'Saving...' : 'Save Changes'}
              </button>
              {updateMutation.isSuccess && <span className="text-xs text-emerald-600">Saved</span>}
              {updateMutation.isError && <span className="text-xs text-companion-rose">Save failed</span>}
            </div>

            {/* Account Actions */}
            {person.is_user && person.id && (
              <div className="border-t border-gray-200 pt-4 space-y-3">
                <h3 className="text-xs font-bold uppercase tracking-wide text-gray-500">Account Actions</h3>

                {(isDeactivated || isPendingDeletion) && (
                  <div className="flex gap-2">
                    {isPendingDeletion && <button onClick={() => cancelDeletionMutation.mutate()} disabled={cancelDeletionMutation.isPending} className="rounded-md bg-amber-500 px-4 py-2 text-sm font-medium text-white hover:bg-amber-600 disabled:opacity-50">{cancelDeletionMutation.isPending ? 'Cancelling...' : 'Cancel Deletion'}</button>}
                    {isDeactivated && <button onClick={() => reactivateMutation.mutate()} disabled={reactivateMutation.isPending} className="rounded-md bg-emerald-500 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-600 disabled:opacity-50">{reactivateMutation.isPending ? 'Reactivating...' : 'Reactivate'}</button>}
                  </div>
                )}

                {deleteStep === 'none' && !isPendingDeletion && (
                  <div className="flex gap-2">
                    {!isDeactivated && <button onClick={() => setDeleteStep('confirm-deactivate')} className="rounded-md border border-amber-300 px-4 py-2 text-sm font-medium text-amber-700 hover:bg-amber-50">Deactivate</button>}
                    <button onClick={() => setDeleteStep('confirm-delete')} className="rounded-md border border-red-300 px-4 py-2 text-sm font-medium text-red-700 hover:bg-red-50">{isDeactivated ? 'Delete Account' : 'Request Deletion'}</button>
                  </div>
                )}

                {deleteStep === 'confirm-deactivate' && (
                  <div className="rounded-md border border-amber-200 bg-amber-50 p-3">
                    <p className="text-sm text-amber-800 mb-2">This will block access and notify caregivers. Reversible.</p>
                    <div className="flex gap-2">
                      <button onClick={() => deactivateMutation.mutate()} disabled={deactivateMutation.isPending} className="rounded-md bg-amber-500 px-3 py-1.5 text-sm font-medium text-white hover:bg-amber-600 disabled:opacity-50">{deactivateMutation.isPending ? 'Deactivating...' : 'Confirm'}</button>
                      <button onClick={() => setDeleteStep('none')} className="px-3 py-1.5 text-sm text-gray-500">Cancel</button>
                    </div>
                  </div>
                )}

                {deleteStep === 'confirm-delete' && (
                  <div className="rounded-md border border-red-200 bg-red-50 p-3">
                    <p className="text-sm text-red-800 mb-2">{isDeactivated ? 'Permanently delete all data. Cannot be undone.' : graceDays === 0 ? 'This will permanently delete all data immediately. Cannot be undone.' : `Schedule deletion in ${graceDays} days. Can be cancelled.`}</p>
                    <div className="flex gap-2">
                      <button onClick={() => isDeactivated ? deleteMutation.mutate() : requestDeletionMutation.mutate()} disabled={deleteMutation.isPending || requestDeletionMutation.isPending} className="rounded-md bg-red-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-50">{(deleteMutation.isPending || requestDeletionMutation.isPending) ? 'Processing...' : 'Confirm'}</button>
                      <button onClick={() => setDeleteStep('none')} className="px-3 py-1.5 text-sm text-gray-500">Cancel</button>
                    </div>
                  </div>
                )}
              </div>
            )}

            {person.created_at && <p className="text-xs text-gray-400 pt-2">Created {new Date(person.created_at).toLocaleDateString()}</p>}
          </div>
        </div>
      </div>
    </>
  )
}

// ---------------------------------------------------------------------------
// Expanded accordion panel (lean summary + relationships)
// ---------------------------------------------------------------------------

function PersonDetail({
  person,
  userOptions,
}: {
  person: Person
  userOptions: UserOption[]
}) {
  const queryClient = useQueryClient()
  const assignments = Array.isArray(person.caregiver_for) ? person.caregiver_for : []
  const [showModal, setShowModal] = useState(false)
  const [showMenu, setShowMenu] = useState(false)
  const [showAssignForm, setShowAssignForm] = useState(false)
  const [showAlertForm, setShowAlertForm] = useState(false)
  const [alertTitle, setAlertTitle] = useState('D.D. Companion')
  const [alertMessage, setAlertMessage] = useState('')
  const [alertResult, setAlertResult] = useState<string | null>(null)
  const [newAssignment, setNewAssignment] = useState({ user_id: '', contact_name: person.display_name || person.first_name || person.email, relationship: 'family', tier: 'tier_1' })

  const addCaregiverMutation = useMutation({
    mutationFn: (data: Record<string, string>) => api(`/admin/people/${person.id}/caregiver`, { method: 'POST', body: JSON.stringify(data) }),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['admin-people'] }); setShowAssignForm(false); setNewAssignment({ user_id: '', contact_name: '', relationship: 'family', tier: 'tier_1' }) },
  })
  const removeCaregiverMutation = useMutation({
    mutationFn: (id: string) => api(`/admin/people/caregiver/${id}`, { method: 'DELETE' }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['admin-people'] }),
  })
  const approveMutation = useMutation({
    mutationFn: (id: string) => api(`/admin/people/caregiver/${id}/approve`, { method: 'POST' }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['admin-people'] }),
  })
  const removeAdminMutation = useMutation({
    mutationFn: (adminId: string) => api(`/admin/admin-users/${adminId}`, { method: 'DELETE' }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['admin-people'] }),
  })
  const sendAlertMutation = useMutation({
    mutationFn: (data: { title: string; message: string }) =>
      api<{ sent: number; error?: string; device_count?: number; user_name: string }>(`/admin/people/${person.id}/send-alert`, {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    onSuccess: (res) => {
      const msg = res.sent > 0
        ? `Sent to ${res.sent} device(s)`
        : res.error === 'no_devices'
          ? 'No devices registered'
          : `Send failed (${res.device_count} device(s) found but FCM error)`
      setAlertResult(msg)
      setTimeout(() => { setAlertResult(null); if (res.sent > 0) { setShowAlertForm(false); setAlertMessage('') } }, 4000)
    },
    onError: () => {
      setAlertResult('Failed to send')
      setTimeout(() => setAlertResult(null), 3000)
    },
  })

  const name = person.first_name || person.display_name || 'This person'

  return (
    <div className="border-t border-gray-200 bg-gray-200 px-5 py-4 space-y-3">
      {/* Summary bar */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 flex-wrap">
          {person.is_admin ? (
            <span className="inline-flex items-center rounded-full bg-red-100 px-2.5 py-0.5 text-xs font-medium text-red-800">Admin{person.admin_role ? ` (${person.admin_role})` : ''}</span>
          ) : assignments.length > 0 ? (
            <span className="inline-flex items-center rounded-full bg-sky-100 px-2.5 py-0.5 text-xs font-medium text-sky-800">Caregiver</span>
          ) : person.is_user ? (
            <span className="inline-flex items-center rounded-full bg-emerald-100 px-2.5 py-0.5 text-xs font-medium text-emerald-800">Member</span>
          ) : null}
          {statusBadge(person.account_status)}
          {person.care_model === 'managed' && <span className="inline-flex items-center rounded-full bg-purple-100 px-2.5 py-0.5 text-xs font-medium text-purple-800">Managed</span>}
          {person.created_at && <span className="text-xs text-gray-400">Since {new Date(person.created_at).toLocaleDateString()}</span>}
        </div>
        <div className="relative">
          <button onClick={() => setShowMenu(!showMenu)} className="rounded-md p-1.5 text-gray-500 hover:bg-white hover:text-gray-700">
            <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 24 24"><circle cx="12" cy="5" r="1.5" /><circle cx="12" cy="12" r="1.5" /><circle cx="12" cy="19" r="1.5" /></svg>
          </button>
          {showMenu && (
            <>
              <div className="fixed inset-0 z-10" onClick={() => setShowMenu(false)} />
              <div className="absolute right-0 bottom-full z-20 mb-1 w-48 rounded-lg border border-gray-200 bg-white py-1 shadow-lg">
                <button onClick={() => { setShowModal(true); setShowMenu(false) }} className="flex w-full items-center gap-2 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50">
                  <svg className="h-4 w-4 text-gray-400" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L10.582 16.07a4.5 4.5 0 01-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 011.13-1.897l8.932-8.931z" /></svg>
                  Edit Profile
                </button>
                {person.is_user && person.id && (
                  <button onClick={() => { setShowAlertForm(true); setShowMenu(false) }} className="flex w-full items-center gap-2 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50">
                    <svg className="h-4 w-4 text-gray-400" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M14.857 17.082a23.848 23.848 0 005.454-1.31A8.967 8.967 0 0118 9.75v-.7V9A6 6 0 006 9v.75a8.967 8.967 0 01-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 01-5.714 0m5.714 0a3 3 0 11-5.714 0" /></svg>
                    Send Alert
                  </button>
                )}
                {person.is_user && person.id && !person.is_admin && (
                  <button onClick={() => { setShowModal(true); setShowMenu(false) }} className="flex w-full items-center gap-2 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50">
                    <svg className="h-4 w-4 text-gray-400" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z" /></svg>
                    Set as Admin
                  </button>
                )}
                {person.is_user && person.id && person.account_status !== 'deactivated' && person.account_status !== 'pending_deletion' && (
                  <button onClick={() => { setShowModal(true); setShowMenu(false) }} className="flex w-full items-center gap-2 px-4 py-2 text-sm text-amber-700 hover:bg-amber-50">
                    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M15.75 5.25v13.5m-7.5-13.5v13.5" /></svg>
                    Deactivate Account
                  </button>
                )}
                {person.is_user && person.id && (
                  <button onClick={() => { setShowModal(true); setShowMenu(false) }} className="flex w-full items-center gap-2 px-4 py-2 text-sm text-red-600 hover:bg-red-50">
                    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" /></svg>
                    Delete Account
                  </button>
                )}
                {person.is_admin && person.admin_id && (
                  <button onClick={() => { removeAdminMutation.mutate(person.admin_id!); setShowMenu(false) }} className="flex w-full items-center gap-2 px-4 py-2 text-sm text-red-600 hover:bg-red-50">
                    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" /></svg>
                    Remove Admin
                  </button>
                )}
              </div>
            </>
          )}
        </div>
      </div>

      {/* Caregivers for this member */}
      {person.is_user && (person.caregivers?.length ?? 0) > 0 && (
        <div className="rounded-lg border border-gray-200 bg-white p-3 shadow-sm">
          <h3 className="text-xs font-bold uppercase tracking-wide text-gray-500 mb-2">Caregivers for {name}</h3>
          <div className="space-y-1.5">
            {person.caregivers.map((c) => (
              <AssignmentRow key={c.contact_id} label={`${c.caregiver_name}`} relationship={c.relationship} tier={c.tier} status={c.status} isActive={c.is_active} contactId={c.contact_id} onApprove={(id) => approveMutation.mutate(id)} onRemove={(id) => removeCaregiverMutation.mutate(id)} approving={approveMutation.isPending} removing={removeCaregiverMutation.isPending} />
            ))}
          </div>
        </div>
      )}

      {/* This person is a caregiver for */}
      {assignments.length > 0 && (
        <div className="rounded-lg border border-gray-200 bg-white p-3 shadow-sm">
          <h3 className="text-xs font-bold uppercase tracking-wide text-gray-500 mb-2">{name} is a caregiver for</h3>
          <div className="space-y-1.5">
            {assignments.map((a) => (
              <AssignmentRow key={a.contact_id} label={a.user_name} relationship={a.relationship} tier={a.tier} status={a.status} isActive={a.is_active} contactId={a.contact_id} onApprove={(id) => approveMutation.mutate(id)} onRemove={(id) => removeCaregiverMutation.mutate(id)} approving={approveMutation.isPending} removing={removeCaregiverMutation.isPending} />
            ))}
          </div>
        </div>
      )}

      {/* Assign as caregiver */}
      {!showAssignForm ? (
        <button onClick={() => setShowAssignForm(true)} className="inline-flex items-center gap-1.5 rounded-md bg-companion-blue px-3 py-1.5 text-xs font-medium text-white hover:bg-companion-blue-mid">
          + Assign as Caregiver
        </button>
      ) : (
        <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm space-y-3">
          <div>
            <label className="mb-1 block text-xs font-medium text-gray-600">Caregiver for which member?</label>
            <select value={newAssignment.user_id} onChange={(e) => setNewAssignment({ ...newAssignment, user_id: e.target.value })} className="block w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm">
              <option value="">Select a member...</option>
              {userOptions.map((u) => <option key={u.id} value={u.id}>{u.name} ({u.email})</option>)}
            </select>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-600">Relationship</label>
              <select value={newAssignment.relationship} onChange={(e) => setNewAssignment({ ...newAssignment, relationship: e.target.value })} className="block w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm">
                {RELATIONSHIPS.map((r) => <option key={r.value} value={r.value}>{r.label}</option>)}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-600">Access Tier</label>
              <select value={newAssignment.tier} onChange={(e) => setNewAssignment({ ...newAssignment, tier: e.target.value })} className="block w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm">
                {TIERS.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
              </select>
            </div>
          </div>
          <div className="flex gap-2">
            <button onClick={() => addCaregiverMutation.mutate({ member_id: newAssignment.user_id, contact_name: newAssignment.contact_name || person.email, relationship: newAssignment.relationship, tier: newAssignment.tier })} disabled={addCaregiverMutation.isPending || !newAssignment.user_id} className="rounded-md bg-companion-blue px-4 py-1.5 text-sm font-medium text-white hover:bg-companion-blue-mid disabled:opacity-50">
              {addCaregiverMutation.isPending ? 'Saving...' : 'Save'}
            </button>
            <button onClick={() => setShowAssignForm(false)} className="px-3 py-1.5 text-sm text-gray-500 hover:text-gray-700">Cancel</button>
          </div>
          {addCaregiverMutation.isError && <p className="text-xs text-companion-rose">Failed to assign caregiver.</p>}
        </div>
      )}

      {/* Alert Form */}
      {showAlertForm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30" onClick={() => setShowAlertForm(false)}>
          <div className="w-full max-w-sm rounded-xl bg-white p-5 shadow-xl space-y-3" onClick={(e) => e.stopPropagation()}>
            <h3 className="text-sm font-semibold text-gray-900">Send Alert to {name}</h3>
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-600">Title</label>
              <input
                value={alertTitle}
                onChange={(e) => setAlertTitle(e.target.value)}
                className="block w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-600">Message</label>
              <textarea
                value={alertMessage}
                onChange={(e) => setAlertMessage(e.target.value)}
                rows={3}
                className="block w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm"
                placeholder="Enter notification message..."
              />
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => sendAlertMutation.mutate({ title: alertTitle, message: alertMessage })}
                disabled={sendAlertMutation.isPending || !alertMessage.trim()}
                className="rounded-md bg-companion-blue px-4 py-1.5 text-sm font-medium text-white hover:bg-companion-blue-mid disabled:opacity-50"
              >
                {sendAlertMutation.isPending ? 'Sending...' : 'Send'}
              </button>
              <button onClick={() => { setShowAlertForm(false); setAlertMessage('') }} className="px-3 py-1.5 text-sm text-gray-500">Cancel</button>
              {alertResult && (
                <span className={`text-xs ${alertResult.includes('Failed') || alertResult.includes('No devices') ? 'text-amber-600' : 'text-emerald-600'}`}>
                  {alertResult}
                </span>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Modal */}
      {showModal && <EditProfileModal person={person} onClose={() => setShowModal(false)} />}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export function PeoplePage() {
  const queryClient = useQueryClient()
  const [search, setSearch] = useState('')
  const [expandedEmail, setExpandedEmail] = useState<string | null>(null)
  const [showAddForm, setShowAddForm] = useState(false)
  const [roleFilters, setRoleFilters] = useState<Set<string>>(new Set())

  const toggleFilter = (role: string) => {
    setRoleFilters((prev) => {
      const next = new Set(prev)
      if (next.has(role)) next.delete(role)
      else next.add(role)
      return next
    })
  }

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

  const getPersonRole = (p: Person): string => {
    if (p.is_admin) return 'admin'
    if (Array.isArray(p.caregiver_for) && p.caregiver_for.length > 0) return 'caregiver'
    if (p.is_user) return 'member'
    return 'member'
  }

  const searchLower = search.toLowerCase()
  const filteredPeople = people.filter((p) => {
    // Role filter
    if (roleFilters.size > 0 && !roleFilters.has(getPersonRole(p))) return false
    // Text search
    if (!search) return true
    const name = (p.display_name || p.first_name || '').toLowerCase()
    const email = (p.email || '').toLowerCase()
    return name.includes(searchLower) || email.includes(searchLower)
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

      {/* Role filters */}
      <div className="flex items-center gap-2">
        {([
          { key: 'admin', label: 'Admin', activeClass: 'bg-red-100 text-red-800 ring-red-300', count: people.filter((p) => getPersonRole(p) === 'admin').length },
          { key: 'caregiver', label: 'Caregiver', activeClass: 'bg-sky-100 text-sky-800 ring-sky-300', count: people.filter((p) => getPersonRole(p) === 'caregiver').length },
          { key: 'member', label: 'Member', activeClass: 'bg-emerald-100 text-emerald-800 ring-emerald-300', count: people.filter((p) => getPersonRole(p) === 'member').length },
        ] as const).map(({ key, label, activeClass, count }) => (
          <button
            key={key}
            onClick={() => toggleFilter(key)}
            className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium ring-1 transition-colors ${
              roleFilters.has(key)
                ? activeClass
                : 'bg-white text-gray-500 ring-gray-200 hover:bg-gray-50'
            }`}
          >
            {label}
            <span className={`${roleFilters.has(key) ? 'opacity-70' : 'text-gray-400'}`}>{count}</span>
          </button>
        ))}
        {roleFilters.size > 0 && (
          <button
            onClick={() => setRoleFilters(new Set())}
            className="text-xs text-gray-400 hover:text-gray-600"
          >
            Clear
          </button>
        )}
      </div>

      <p className="text-xs text-gray-400">{filteredPeople.length} of {people.length} people</p>

      {/* People list */}
      <div className="rounded-lg border border-gray-200 bg-white shadow-sm">
        {filteredPeople.length === 0 ? (
          <div className="px-6 py-12 text-center text-sm text-gray-400">No people found</div>
        ) : (
          filteredPeople.map((person) => {
            const isExpanded = expandedEmail === person.email
            return (
              <div key={person.email} className="border-b border-gray-100 last:border-b-0">
                <button
                  type="button"
                  onClick={() => setExpandedEmail(isExpanded ? null : person.email)}
                  className="flex w-full items-center justify-between px-5 py-3.5 text-left transition-colors hover:bg-gray-50"
                >
                  <div className="min-w-0 flex-1">
                    <span className="text-sm font-medium text-gray-900">
                      {person.display_name || person.first_name || person.email}
                    </span>
                    <span className="ml-3 text-sm text-gray-500">{person.email}</span>
                  </div>
                  <div className="ml-4">
                    <svg className={`h-4 w-4 text-gray-400 transition-transform ${isExpanded ? 'rotate-90' : ''}`} fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
                    </svg>
                  </div>
                </button>
                {isExpanded && (
                  <PersonDetail
                    person={people.find((p) => p.email === person.email) || person}
                    userOptions={userOptions}
                  />
                )}
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}
