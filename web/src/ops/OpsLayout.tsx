import { Routes, Route, Navigate } from 'react-router-dom'
import { Layout } from '../shared/components/Layout'
import { PipelinePage } from './pages/PipelinePage'
import { EscalationsPage } from './pages/EscalationsPage'
import { MetricsPage } from './pages/MetricsPage'

export function OpsLayout() {
  return (
    <Layout>
      <Routes>
        <Route path="pipeline" element={<PipelinePage />} />
        <Route path="escalations" element={<EscalationsPage />} />
        <Route path="metrics" element={<MetricsPage />} />
        <Route path="" element={<Navigate to="pipeline" replace />} />
      </Routes>
    </Layout>
  )
}
