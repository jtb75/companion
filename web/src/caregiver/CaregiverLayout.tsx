import { useState } from 'react'
import { Routes, Route } from 'react-router-dom'
import { Layout } from '../shared/components/Layout'
import { UserPicker } from './components/UserPicker'
import { AlertsPage } from './pages/AlertsPage'
import { DashboardPage } from './pages/DashboardPage'
import { ActivityPage } from './pages/ActivityPage'

export function CaregiverLayout() {
  const [selectedUserId, setSelectedUserId] = useState<string | null>(null)

  return (
    <Layout>
      <UserPicker
        selectedUserId={selectedUserId}
        onSelect={setSelectedUserId}
      />
      {selectedUserId ? (
        <Routes>
          <Route path="alerts" element={<AlertsPage userId={selectedUserId} />} />
          <Route path="dashboard" element={<DashboardPage userId={selectedUserId} />} />
          <Route path="activity" element={<ActivityPage userId={selectedUserId} />} />
          <Route index element={<DashboardPage userId={selectedUserId} />} />
        </Routes>
      ) : (
        <div className="text-gray-400 text-sm mt-4">
          Select a user above to view their data.
        </div>
      )}
    </Layout>
  )
}
