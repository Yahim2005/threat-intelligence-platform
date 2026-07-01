// src/pages/Analytics.jsx
import { useEffect, useState } from 'react'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  Cell, LineChart, Line, CartesianGrid
} from 'recharts'
import { Database, Tag, BarChart2, TrendingUp } from 'lucide-react'
import { api } from '../api/client'

const COLORS = ['#6366f1','#10b981','#f59e0b','#ef4444','#3b82f6','#8b5cf6','#ec4899','#14b8a6','#f97316','#84cc16']

function Section({ icon: Icon, title, subtitle, children }) {
  return (
    <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5">
      <div className="mb-4">
        <h2 className="flex items-center gap-2 text-sm font-semibold text-gray-700">
          <Icon size={15} className="text-indigo-500" />
          {title}
        </h2>
        {subtitle && <p className="text-xs text-gray-400 mt-0.5">{subtitle}</p>}
      </div>
      {children}
    </div>
  )
}

function useData(fetcher) {
  const [data,    setData]    = useState([])
  const [loading, setLoading] = useState(true)
  useEffect(() => {
    fetcher().then(setData).catch(console.error).finally(() => setLoading(false))
  }, [])
  return { data, loading }
}

export default function Analytics() {
  const sources  = useData(() => api.topSources(10))
  const tags     = useData(() => api.topTags(10))
  const distrib  = useData(() => api.confidenceDistribution())
  const trends   = useData(() => api.trends(30))

  const trendsFormatted = trends.data.map(d => ({
    ...d,
    label: d.date.slice(5).replace('-', '/'),
  }))

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-bold text-gray-800">Analytics</h1>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">

        {/* Top sources */}
        <Section
          icon={Database}
          title="Top 10 sources"
          subtitle="Volume d'IOCs par source de collecte"
        >
          {sources.loading ? (
            <div className="h-64 flex items-center justify-center text-gray-400 text-sm">Chargement…</div>
          ) : (
            <ResponsiveContainer width="100%" height={260}>
              <BarChart
                data={sources.data}
                layout="vertical"
                margin={{ top: 0, right: 20, left: 10, bottom: 0 }}
              >
                <XAxis type="number" tick={{ fontSize: 11 }} />
                <YAxis
                  type="category"
                  dataKey="name"
                  tick={{ fontSize: 10 }}
                  width={130}
                />
                <Tooltip formatter={(v) => [v.toLocaleString(), 'IOCs']} />
                <Bar dataKey="count" radius={[0, 4, 4, 0]}>
                  {sources.data.map((_, i) => (
                    <Cell key={i} fill={COLORS[i % COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </Section>

        {/* Top tags malware */}
        <Section
          icon={Tag}
          title="Top 10 familles de malware"
          subtitle="Tags malware:* les plus représentés"
        >
          {tags.loading ? (
            <div className="h-64 flex items-center justify-center text-gray-400 text-sm">Chargement…</div>
          ) : (
            <ResponsiveContainer width="100%" height={260}>
              <BarChart
                data={tags.data}
                layout="vertical"
                margin={{ top: 0, right: 20, left: 10, bottom: 0 }}
              >
                <XAxis type="number" tick={{ fontSize: 11 }} />
                <YAxis
                  type="category"
                  dataKey="name"
                  tick={{ fontSize: 10 }}
                  width={130}
                  tickFormatter={(v) => v.replace('malware:', '')}
                />
                <Tooltip
                  formatter={(v) => [v.toLocaleString(), 'IOCs']}
                  labelFormatter={(l) => l.replace('malware:', '')}
                />
                <Bar dataKey="count" radius={[0, 4, 4, 0]}>
                  {tags.data.map((_, i) => (
                    <Cell key={i} fill={COLORS[i % COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </Section>

        {/* Distribution confidence */}
        <Section
          icon={BarChart2}
          title="Distribution des scores de confiance"
          subtitle="IOCs actifs répartis par tranche de score"
        >
          {distrib.loading ? (
            <div className="h-48 flex items-center justify-center text-gray-400 text-sm">Chargement…</div>
          ) : (
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={distrib.data} margin={{ top: 0, right: 10, left: -20, bottom: 0 }}>
                <XAxis dataKey="range" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip formatter={(v) => [v.toLocaleString(), 'IOCs']} />
                <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                  {distrib.data.map((entry, i) => {
                    const base = parseInt(entry.range)
                    const color = base >= 75 ? '#ef4444' : base >= 50 ? '#f59e0b' : '#6366f1'
                    return <Cell key={i} fill={color} />
                  })}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </Section>

        {/* Tendance 30 jours */}
        <Section
          icon={TrendingUp}
          title="Ingestion sur 30 jours"
          subtitle="Nombre d'IOCs nouveaux créés par jour"
        >
          {trends.loading ? (
            <div className="h-48 flex items-center justify-center text-gray-400 text-sm">Chargement…</div>
          ) : (
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={trendsFormatted} margin={{ top: 0, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="label" tick={{ fontSize: 11 }} interval="preserveStartEnd" />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip formatter={(v) => [v.toLocaleString(), 'IOCs']} />
                <Line type="monotone" dataKey="count" stroke="#6366f1" strokeWidth={2} dot={false} activeDot={{ r: 4 }} />
              </LineChart>
            </ResponsiveContainer>
          )}
        </Section>

      </div>
    </div>
  )
}