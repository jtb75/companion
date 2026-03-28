import { Card } from '../../shared/components/Card'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

const sectionUsage = [
  { section: 'Mail', sessions: 142 },
  { section: 'Bills', sessions: 98 },
  { section: 'Medical', sessions: 76 },
  { section: 'Calendar', sessions: 65 },
  { section: 'Contacts', sessions: 41 },
]

const cohortData = [
  { week: 'W1', retained: 100 },
  { week: 'W2', retained: 85 },
  { week: 'W3', retained: 78 },
  { week: 'W4', retained: 72 },
]

export function MetricsPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold text-gray-900">Pilot Metrics</h1>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card title="Active Users">
          <p className="text-3xl font-bold text-companion-blue">12</p>
          <p className="text-sm text-gray-500 mt-1">Last 7 days</p>
        </Card>
        <Card title="Avg Sessions / User">
          <p className="text-3xl font-bold text-companion-teal">4.2</p>
          <p className="text-sm text-gray-500 mt-1">Per week</p>
        </Card>
        <Card title="Retention (4-week)">
          <p className="text-3xl font-bold text-companion-sage">72%</p>
          <p className="text-sm text-gray-500 mt-1">Pilot cohort</p>
        </Card>
      </div>

      <Card title="Section Usage" subtitle="Sessions by section (last 30 days)">
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={sectionUsage}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="section" />
              <YAxis />
              <Tooltip />
              <Bar dataKey="sessions" fill="#2C5F8A" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </Card>

      <Card title="Retention Cohort" subtitle="Pilot cohort weekly retention">
        <div className="h-48">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={cohortData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="week" />
              <YAxis domain={[0, 100]} />
              <Tooltip />
              <Bar dataKey="retained" fill="#2A7A6F" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </Card>
    </div>
  )
}
