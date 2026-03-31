import { useQuery } from '@tanstack/react-query'
import { api } from '../../shared/api/client'

interface AuditEntry {
  id: string
  config_id: string
  category: string
  key: string
  changed_by: string
  reason: string | null
  old_value: Record<string, unknown> | null
  new_value: Record<string, unknown>
  changed_at: string
}

function formatValue(val: Record<string, unknown> | null | string): string {
  if (val === null) return '-'
  if (typeof val === 'string') return val
  const str = JSON.stringify(val)
  return str.length > 80 ? str.slice(0, 77) + '...' : str
}

export function AuditPage() {
  const { data, isLoading } = useQuery({
    queryKey: ['config-audit'],
    queryFn: () => api<{ entries: AuditEntry[]; total: number }>('/admin/config/audit'),
  })

  const entries = data?.entries ?? []

  if (isLoading) {
    return <p className="text-gray-500">Loading audit log...</p>
  }

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold text-gray-900">Config Audit Log</h1>

      <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Timestamp
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Category
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Key
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Changed By
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Old Value
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                New Value
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {entries.length === 0 && (
              <tr>
                <td colSpan={6} className="px-4 py-12 text-center text-sm text-gray-400">
                  No audit entries yet. Changes to config settings will appear here.
                </td>
              </tr>
            )}
            {entries.map((entry) => (
              <tr key={entry.id} className="hover:bg-gray-50">
                <td className="px-4 py-3 text-sm text-gray-600 whitespace-nowrap">
                  {new Date(entry.changed_at).toLocaleString()}
                </td>
                <td className="px-4 py-3 text-sm text-gray-800">
                  <span className="px-2 py-0.5 bg-gray-100 rounded text-xs font-mono">
                    {entry.category}
                  </span>
                </td>
                <td className="px-4 py-3 text-sm text-gray-800 font-mono">{entry.key}</td>
                <td className="px-4 py-3 text-sm text-gray-600">{entry.changed_by}</td>
                <td className="px-4 py-3 text-sm text-gray-500 max-w-[200px] truncate" title={formatValue(entry.old_value)}>
                  {formatValue(entry.old_value)}
                </td>
                <td className="px-4 py-3 text-sm text-gray-800 max-w-[200px] truncate" title={formatValue(entry.new_value)}>
                  {formatValue(entry.new_value)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
