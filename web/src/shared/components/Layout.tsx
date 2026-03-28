import { Link, useLocation } from 'react-router-dom'
import { useAuth } from '../auth/AuthProvider'

const navSections = [
  {
    label: 'Caregiver',
    links: [
      { to: '/caregiver/alerts', label: 'Alerts' },
      { to: '/caregiver/dashboard', label: 'Dashboard' },
      { to: '/caregiver/activity', label: 'Activity' },
    ],
  },
  {
    label: 'Ops',
    links: [
      { to: '/ops/pipeline', label: 'Pipeline' },
      { to: '/ops/escalations', label: 'Escalations' },
      { to: '/ops/metrics', label: 'Metrics' },
    ],
  },
  {
    label: 'Admin',
    links: [
      { to: '/admin/prompts', label: 'Prompts' },
      { to: '/admin/thresholds', label: 'Thresholds' },
      { to: '/admin/voices', label: 'Voices' },
      { to: '/admin/notifications', label: 'Notifications' },
      { to: '/admin/audit', label: 'Audit' },
    ],
  },
]

function currentSection(pathname: string): string {
  if (pathname.startsWith('/caregiver')) return 'Caregiver'
  if (pathname.startsWith('/ops')) return 'Ops'
  if (pathname.startsWith('/admin')) return 'Admin'
  return 'Companion'
}

export function Layout({ children }: { children: React.ReactNode }) {
  const location = useLocation()
  const section = currentSection(location.pathname)
  const { user, logout } = useAuth()

  return (
    <div className="flex h-screen bg-companion-cream">
      {/* Sidebar */}
      <nav className="w-56 bg-companion-blue text-white flex-shrink-0 overflow-y-auto flex flex-col">
        <div className="p-4 border-b border-companion-blue-mid">
          <h1 className="text-lg font-bold tracking-wide">Companion</h1>
        </div>
        <div className="flex-1">
        {navSections.map((sec) => (
          <div key={sec.label} className="px-3 py-3">
            <h2 className="text-xs font-semibold uppercase tracking-wider text-companion-blue-light mb-2 px-2">
              {sec.label}
            </h2>
            {sec.links.map((link) => {
              const active = location.pathname === link.to
              return (
                <Link
                  key={link.to}
                  to={link.to}
                  className={`block px-2 py-1.5 rounded text-sm ${
                    active
                      ? 'bg-companion-blue-mid text-white font-medium'
                      : 'text-companion-blue-light hover:text-white hover:bg-companion-blue-mid/50'
                  }`}
                >
                  {link.label}
                </Link>
              )
            })}
          </div>
        ))}
        </div>
        {user && (
          <div className="p-3 border-t border-companion-blue-mid">
            <div className="text-xs text-companion-blue-light truncate px-2 mb-2">
              {user.email}
            </div>
            <button
              onClick={logout}
              className="w-full text-left px-2 py-1.5 rounded text-sm text-companion-blue-light hover:text-white hover:bg-companion-blue-mid/50 transition"
            >
              Sign Out
            </button>
          </div>
        )}
      </nav>

      {/* Main content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        <header className="bg-white border-b border-gray-200 px-6 py-3 flex-shrink-0 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-companion-blue">{section}</h2>
          {user && (
            <span className="text-sm text-gray-500">{user.email}</span>
          )}
        </header>
        <main className="flex-1 overflow-y-auto p-6">
          {children}
        </main>
      </div>
    </div>
  )
}
