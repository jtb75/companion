import { useAuth } from './AuthProvider'

export default function AccessDenied() {
  const { user, logout } = useAuth()

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-companion-cream">
      <div className="bg-white rounded-2xl shadow-lg p-8 w-full max-w-md text-center">
        <div className="text-5xl mb-4">🔒</div>
        <h1 className="text-xl font-bold text-gray-800 mb-2">Access Denied</h1>
        <p className="text-gray-500 mb-2">
          Signed in as <span className="font-medium">{user?.email}</span>
        </p>
        <p className="text-gray-400 text-sm mb-6">
          Your account doesn't have access to the Companion Dashboard.
          Contact your administrator to request access.
        </p>
        <button
          onClick={logout}
          className="w-full bg-companion-blue text-white font-medium py-3 rounded-xl hover:bg-companion-blue-mid transition"
        >
          Sign Out
        </button>
      </div>
    </div>
  )
}
