import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../../shared/api/client'
import { Card } from '../../shared/components/Card'

interface AdminUserEntry {
  id: string
  email: string
  name: string
  role: string
  is_active: boolean
  last_login_at: string | null
}

interface AdminUsersResponse {
  users: AdminUserEntry[]
  total: number
}

const ROLES = ['viewer', 'editor', 'admin']

export function AdminUsersPage() {
  const queryClient = useQueryClient()
  const [email, setEmail] = useState('')
  const [name, setName] = useState('')
  const [role, setRole] = useState('viewer')
  const [status, setStatus] = useState<string | null>(null)

  const { data, isLoading } = useQuery({
    queryKey: ['admin-users'],
    queryFn: () => api<AdminUsersResponse>('/admin/admin-users'),
  })

  const addMutation = useMutation({
    mutationFn: async () => {
      await api('/admin/admin-users', {
        method: 'POST',
        body: JSON.stringify({ email, name, role }),
      })
    },
    onSuccess: () => {
      setStatus('Admin user added')
      setEmail('')
      setName('')
      setRole('viewer')
      queryClient.invalidateQueries({ queryKey: ['admin-users'] })
      setTimeout(() => setStatus(null), 3000)
    },
    onError: () => {
      setStatus('Failed to add admin user')
      setTimeout(() => setStatus(null), 3000)
    },
  })

  const deleteMutation = useMutation({
    mutationFn: async (id: string) => {
      await api(`/admin/admin-users/${id}`, { method: 'DELETE' })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-users'] })
    },
  })

  const users = Array.isArray(data?.users) ? data.users : []

  if (isLoading) {
    return <p className="text-gray-500">Loading admin users...</p>
  }

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold text-gray-900">Admin User Management</h1>

      <Card title="Add Admin User">
        <div className="grid grid-cols-1 sm:grid-cols-4 gap-3">
          <input
            type="email"
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-companion-blue-light focus:border-companion-blue-light"
          />
          <input
            type="text"
            placeholder="Name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-companion-blue-light focus:border-companion-blue-light"
          />
          <select
            value={role}
            onChange={(e) => setRole(e.target.value)}
            className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-companion-blue-light focus:border-companion-blue-light"
          >
            {ROLES.map((r) => (
              <option key={r} value={r}>
                {r}
              </option>
            ))}
          </select>
          <button
            onClick={() => addMutation.mutate()}
            disabled={addMutation.isPending || !email || !name}
            className="px-4 py-2 bg-companion-blue text-white rounded-lg text-sm font-medium hover:bg-companion-blue-mid disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {addMutation.isPending ? 'Adding...' : 'Add Admin'}
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

      <Card title="Current Admin Users" subtitle={`${users.length} admin user(s)`}>
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left">
            <thead>
              <tr className="border-b border-gray-200 text-gray-500">
                <th className="py-2 pr-4 font-medium">Email</th>
                <th className="py-2 pr-4 font-medium">Name</th>
                <th className="py-2 pr-4 font-medium">Role</th>
                <th className="py-2 pr-4 font-medium">Active</th>
                <th className="py-2 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id} className="border-b border-gray-100">
                  <td className="py-2 pr-4 text-gray-900">{u.email}</td>
                  <td className="py-2 pr-4 text-gray-700">{u.name}</td>
                  <td className="py-2 pr-4">
                    <span className="inline-block px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-700">
                      {u.role}
                    </span>
                  </td>
                  <td className="py-2 pr-4">
                    <span
                      className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${
                        u.is_active
                          ? 'bg-green-100 text-green-700'
                          : 'bg-red-100 text-red-700'
                      }`}
                    >
                      {u.is_active ? 'Yes' : 'No'}
                    </span>
                  </td>
                  <td className="py-2">
                    <button
                      onClick={() => deleteMutation.mutate(u.id)}
                      disabled={deleteMutation.isPending}
                      className="text-xs text-red-600 hover:text-red-800 font-medium"
                    >
                      Deactivate
                    </button>
                  </td>
                </tr>
              ))}
              {users.length === 0 && (
                <tr>
                  <td colSpan={5} className="py-4 text-center text-gray-400">
                    No admin users found
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
