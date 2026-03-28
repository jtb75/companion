import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AuthProvider } from './shared/auth/AuthProvider'
import LoginPage from './shared/auth/LoginPage'
import ProtectedRoute from './shared/auth/ProtectedRoute'
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
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/caregiver/*" element={<ProtectedRoute><CaregiverLayout /></ProtectedRoute>} />
            <Route path="/ops/*" element={<ProtectedRoute><OpsLayout /></ProtectedRoute>} />
            <Route path="/admin/*" element={<ProtectedRoute><AdminLayout /></ProtectedRoute>} />
            <Route path="/" element={<Navigate to="/ops" replace />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  </React.StrictMode>,
)
