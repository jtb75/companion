import { Routes, Route, Navigate } from 'react-router-dom'
import { Layout } from '../shared/components/Layout'
import { PromptsPage } from './pages/PromptsPage'
import { ThresholdsPage } from './pages/ThresholdsPage'
import { VoicesPage } from './pages/VoicesPage'
import { NotificationsPage } from './pages/NotificationsPage'
import { AuditPage } from './pages/AuditPage'
import { AdminUsersPage } from './pages/AdminUsersPage'
import { ContactsPage } from './pages/ContactsPage'

export function AdminLayout() {
  return (
    <Layout>
      <Routes>
        <Route path="prompts" element={<PromptsPage />} />
        <Route path="thresholds" element={<ThresholdsPage />} />
        <Route path="voices" element={<VoicesPage />} />
        <Route path="notifications" element={<NotificationsPage />} />
        <Route path="audit" element={<AuditPage />} />
        <Route path="admin-users" element={<AdminUsersPage />} />
        <Route path="contacts" element={<ContactsPage />} />
        <Route path="" element={<Navigate to="prompts" replace />} />
      </Routes>
    </Layout>
  )
}
