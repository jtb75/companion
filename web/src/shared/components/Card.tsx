interface CardProps {
  title: string
  subtitle?: string
  children: React.ReactNode
  className?: string
}

export function Card({ title, subtitle, children, className = '' }: CardProps) {
  return (
    <div className={`bg-white rounded-lg shadow-sm border border-gray-200 p-5 ${className}`}>
      <div className="mb-3">
        <h3 className="text-base font-semibold text-gray-900">{title}</h3>
        {subtitle && <p className="text-sm text-gray-500 mt-0.5">{subtitle}</p>}
      </div>
      {children}
    </div>
  )
}
