import { Card } from '../../shared/components/Card'

export function NotificationsPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold text-gray-900">Notification Settings</h1>

      <Card title="Caregiver Notifications" subtitle="Configure when caregivers receive alerts">
        <div className="space-y-3">
          <label className="flex items-center gap-3">
            <input type="checkbox" defaultChecked className="rounded border-gray-300" />
            <span className="text-sm text-gray-700">Medication missed (2+ hours overdue)</span>
          </label>
          <label className="flex items-center gap-3">
            <input type="checkbox" defaultChecked className="rounded border-gray-300" />
            <span className="text-sm text-gray-700">Bill due within 3 days</span>
          </label>
          <label className="flex items-center gap-3">
            <input type="checkbox" defaultChecked className="rounded border-gray-300" />
            <span className="text-sm text-gray-700">Appointment reminder (24 hours before)</span>
          </label>
          <label className="flex items-center gap-3">
            <input type="checkbox" className="rounded border-gray-300" />
            <span className="text-sm text-gray-700">Daily summary digest</span>
          </label>
        </div>
      </Card>

      <Card title="Escalation Notifications" subtitle="Configure when ops team gets notified">
        <div className="space-y-3">
          <label className="flex items-center gap-3">
            <input type="checkbox" defaultChecked className="rounded border-gray-300" />
            <span className="text-sm text-gray-700">Question approaching threshold (80%)</span>
          </label>
          <label className="flex items-center gap-3">
            <input type="checkbox" defaultChecked className="rounded border-gray-300" />
            <span className="text-sm text-gray-700">Question past threshold</span>
          </label>
          <label className="flex items-center gap-3">
            <input type="checkbox" defaultChecked className="rounded border-gray-300" />
            <span className="text-sm text-gray-700">Pipeline stage failure rate above 10%</span>
          </label>
        </div>
      </Card>

      <div className="flex justify-end">
        <button className="px-4 py-2 bg-companion-blue text-white rounded-lg text-sm font-medium hover:bg-companion-blue-mid">
          Save Settings
        </button>
      </div>
    </div>
  )
}
