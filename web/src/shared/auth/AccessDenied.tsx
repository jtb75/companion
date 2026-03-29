import { useEffect, useState } from 'react'
import { useAuth } from './AuthProvider'

export default function AccessDenied() {
  const { user, logout } = useAuth()
  const [deniedEmail, setDeniedEmail] = useState<string | null>(null)

  useEffect(() => {
    if (user) {
      setDeniedEmail(user.email)
      logout()
    }
  }, [user, logout])

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-companion-cream">
      <div className="bg-white rounded-2xl shadow-lg p-8 w-full max-w-md text-center">
        <div className="text-5xl mb-4">🔒</div>
        <h1 className="text-xl font-bold text-gray-800 mb-2">Access Denied</h1>
        {deniedEmail && (
          <p className="text-gray-500 mb-2">
            <span className="font-medium">{deniedEmail}</span> does not have
            access to the Companion Dashboard.
          </p>
        )}
        <p className="text-gray-400 text-sm mb-6">
          You have been signed out. Contact your administrator to request access.
        </p>
        <a
          href="/login"
          className="block w-full bg-companion-blue text-white font-medium py-3 rounded-xl hover:bg-companion-blue-mid transition text-center"
        >
          Return to Login
        </a>
      </div>
    </div>
  )
}
