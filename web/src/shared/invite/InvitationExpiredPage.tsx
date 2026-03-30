import { Link } from 'react-router-dom'
import { BRAND_MID, BRAND_EMOJI } from '../branding'

export default function InvitationExpiredPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-companion-cream">
      <div className="bg-white rounded-2xl shadow-lg p-8 w-full max-w-md text-center">
        <div className="text-4xl mb-2">{BRAND_EMOJI}</div>
        <h1 className="text-2xl font-bold text-companion-blue mb-2">{BRAND_MID}</h1>
        <p className="text-gray-600 mb-6">
          This invitation link is invalid or has expired.
        </p>
        <p className="text-gray-500 text-sm mb-6">
          Please contact the person who invited you to request a new invitation.
        </p>
        <Link
          to="/login"
          className="text-companion-blue hover:underline text-sm"
        >
          Go to sign in
        </Link>
      </div>
    </div>
  )
}
