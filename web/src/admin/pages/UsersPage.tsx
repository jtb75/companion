import { useEffect, useState } from 'react'
import { api } from '../../shared/api/client'

interface CompanionUser {
  id: string
  email: string
  first_name: string | null
  last_name: string | null
  phone: string | null
  preferred_name: string | null
  display_name: string | null
  created_at: string | null
}

export function UsersPage() {
  const [users, setUsers] = useState<CompanionUser[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  // Add form state
  const [firstName, setFirstName] = useState('')
  const [lastName, setLastName] = useState('')
  const [email, setEmail] = useState('')
  const [phone, setPhone] = useState('')
  const [adding, setAdding] = useState(false)

  const fetchUsers = async () => {
    try {
      const data = await api<{ users: CompanionUser[] }>('/admin/companion-users')
      setUsers(Array.isArray(data.users) ? data.users : [])
    } catch {
      setError('Failed to load users')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchUsers()
  }, [])

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!email.trim()) return
    setAdding(true)
    setError('')
    try {
      await api('/admin/companion-users', {
        method: 'POST',
        body: JSON.stringify({
          first_name: firstName.trim(),
          last_name: lastName.trim(),
          email: email.trim(),
          phone: phone.trim() || null,
        }),
      })
      setFirstName('')
      setLastName('')
      setEmail('')
      setPhone('')
      await fetchUsers()
    } catch {
      setError('Failed to add user')
    } finally {
      setAdding(false)
    }
  }

  const handleDelete = async (id: string) => {
    if (!confirm('Delete this user? This cannot be undone.')) return
    try {
      await api(`/admin/companion-users/${id}`, { method: 'DELETE' })
      await fetchUsers()
    } catch {
      setError('Failed to delete user')
    }
  }

  if (loading) {
    return <div className="text-companion-blue">Loading users...</div>
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-companion-blue">Companion Users</h1>

      {error && (
        <div className="bg-red-50 text-red-700 p-3 rounded-lg text-sm">{error}</div>
      )}

      {/* Add form */}
      <form onSubmit={handleAdd} className="bg-white rounded-xl shadow p-4 flex flex-wrap gap-3 items-end">
        <div className="flex-1 min-w-[140px]">
          <label className="block text-xs font-medium text-gray-500 mb-1">First Name</label>
          <input
            type="text"
            value={firstName}
            onChange={(e) => setFirstName(e.target.value)}
            className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:border-companion-blue focus:outline-none"
            placeholder="First name"
          />
        </div>
        <div className="flex-1 min-w-[140px]">
          <label className="block text-xs font-medium text-gray-500 mb-1">Last Name</label>
          <input
            type="text"
            value={lastName}
            onChange={(e) => setLastName(e.target.value)}
            className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:border-companion-blue focus:outline-none"
            placeholder="Last name"
          />
        </div>
        <div className="flex-1 min-w-[180px]">
          <label className="block text-xs font-medium text-gray-500 mb-1">Email *</label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:border-companion-blue focus:outline-none"
            placeholder="user@example.com"
            required
          />
        </div>
        <div className="flex-1 min-w-[140px]">
          <label className="block text-xs font-medium text-gray-500 mb-1">Phone</label>
          <input
            type="tel"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:border-companion-blue focus:outline-none"
            placeholder="Phone"
          />
        </div>
        <button
          type="submit"
          disabled={adding}
          className="bg-companion-blue text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-companion-blue-mid transition disabled:opacity-50"
        >
          {adding ? 'Adding...' : 'Add User'}
        </button>
      </form>

      {/* Table */}
      <div className="bg-white rounded-xl shadow overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-left">
            <tr>
              <th className="px-4 py-3 font-medium text-gray-500">First Name</th>
              <th className="px-4 py-3 font-medium text-gray-500">Last Name</th>
              <th className="px-4 py-3 font-medium text-gray-500">Email</th>
              <th className="px-4 py-3 font-medium text-gray-500">Phone</th>
              <th className="px-4 py-3 font-medium text-gray-500">Created</th>
              <th className="px-4 py-3 font-medium text-gray-500">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {Array.isArray(users) && users.map((u) => (
              <tr key={u.id} className="hover:bg-gray-50">
                <td className="px-4 py-3">{u.first_name || '-'}</td>
                <td className="px-4 py-3">{u.last_name || '-'}</td>
                <td className="px-4 py-3 text-gray-600">{u.email}</td>
                <td className="px-4 py-3 text-gray-600">{u.phone || '-'}</td>
                <td className="px-4 py-3 text-gray-400">
                  {u.created_at ? new Date(u.created_at).toLocaleDateString() : '-'}
                </td>
                <td className="px-4 py-3">
                  <button
                    onClick={() => handleDelete(u.id)}
                    className="text-red-500 hover:text-red-700 text-xs font-medium"
                  >
                    Delete
                  </button>
                </td>
              </tr>
            ))}
            {(!Array.isArray(users) || users.length === 0) && (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-gray-400">
                  No users yet
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
