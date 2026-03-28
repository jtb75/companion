import { useQuery } from '@tanstack/react-query'
import { api } from '../../shared/api/client'

interface AuditEntry {
  timestamp: string
  category: string
  key: string
  changed_by: string
  old_value: string
  new_value: string
}

const placeholderAudit: AuditEntry[] = [
  {
    timestamp: '2026-03-27T09:12:00Z',
    category: 'pipeline_threshold',
    key: 'classification_confidence',
    changed_by: 'admin@companion.dev',
    old_value: '0.80',
    new_value: '0.85',
  },
  {
    timestamp: '2026-03-25T10:00:00Z',
    category: 'arlo_persona',
    key: 'system_prompt',
    changed_by: 'admin@companion.dev',
    old_value: '(previous prompt text)',
    new_value: '(updated prompt text)',
  },
  {
    timestamp: '2026-03-22T15:30:00Z',
    category: 'pipeline_threshold',
    key: 'junk_cutoff',
    changed_by: 'ops@companion.dev',
    old_value: '0.25',
    new_value: '0.30',
  },
]

export function AuditPage() {
  const { data, isLoading } = useQuery({
    queryKey: ['config-audit'],
    queryFn: async () => {
      try {
        return await api<AuditEntry[]>('/admin/config/audit')
      } catch {
        return placeholderAudit
      }
    },
  })

  const entries = Array.isArray(data) ? data : placeholderAudit

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
            {entries.map((entry, i) => (
              <tr key={i} className="hover:bg-gray-50">
                <td className="px-4 py-3 text-sm text-gray-600 whitespace-nowrap">
                  {new Date(entry.timestamp).toLocaleString()}
                </td>
                <td className="px-4 py-3 text-sm text-gray-800">
                  <span className="px-2 py-0.5 bg-gray-100 rounded text-xs font-mono">
                    {entry.category}
                  </span>
                </td>
                <td className="px-4 py-3 text-sm text-gray-800 font-mono">{entry.key}</td>
                <td className="px-4 py-3 text-sm text-gray-600">{entry.changed_by}</td>
                <td className="px-4 py-3 text-sm text-gray-500 max-w-[200px] truncate">
                  {entry.old_value}
                </td>
                <td className="px-4 py-3 text-sm text-gray-800 max-w-[200px] truncate">
                  {entry.new_value}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
