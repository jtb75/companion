import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { CaregiverLayout } from './caregiver/CaregiverLayout'
import { OpsLayout } from './ops/OpsLayout'
import { AdminLayout } from './admin/AdminLayout'
import './index.css'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
})

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/caregiver/*" element={<CaregiverLayout />} />
          <Route path="/ops/*" element={<OpsLayout />} />
          <Route path="/admin/*" element={<AdminLayout />} />
          <Route path="/" element={<Navigate to="/ops" replace />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  </React.StrictMode>,
)
