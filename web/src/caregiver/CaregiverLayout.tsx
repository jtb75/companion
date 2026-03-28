import { Routes, Route, Navigate } from 'react-router-dom'
import { Layout } from '../shared/components/Layout'
import { AlertsPage } from './pages/AlertsPage'
import { DashboardPage } from './pages/DashboardPage'
import { ActivityPage } from './pages/ActivityPage'

export function CaregiverLayout() {
  return (
    <Layout>
      <Routes>
        <Route path="alerts" element={<AlertsPage />} />
        <Route path="dashboard" element={<DashboardPage />} />
        <Route path="activity" element={<ActivityPage />} />
        <Route path="" element={<Navigate to="dashboard" replace />} />
      </Routes>
    </Layout>
  )
}
