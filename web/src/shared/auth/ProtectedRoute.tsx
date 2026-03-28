import { Navigate } from 'react-router-dom'
import { useAuth } from './AuthProvider'
import AccessDenied from './AccessDenied'

interface Props {
  children: React.ReactNode
  requiredRole?: 'admin' | 'caregiver'
}

export default function ProtectedRoute({ children, requiredRole }: Props) {
  const { user, loading, authorized, role } = useAuth()

  if (loading || authorized === null) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-companion-cream">
        <div className="animate-pulse text-companion-blue">Loading...</div>
      </div>
    )
  }

  if (!user) {
    return <Navigate to="/login" replace />
  }

  if (!authorized) {
    return <AccessDenied />
  }

  // Role check: admins can access everything, caregivers only caregiver routes
  if (requiredRole === 'admin' && role !== 'admin') {
    return <AccessDenied />
  }

  return <>{children}</>
}
