// src/pages/Analytics.jsx
import { useEffect, useState } from 'react'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  Cell, AreaChart, Area, CartesianGrid
} from 'recharts'
import { Database, Tag, BarChart2, TrendingUp } from 'lucide-react'
import { api } from '../api/client'

const BEIGE_PALETTE = [
  '#8b7355','#c4a882','#a0845c','#6b5740','#d4b896',
  '#bfa07a','#e8d5b7','#7a6248','#9e8266','#c9a87c'
]

// ── Tooltip custom ────────────────────────────────────────────────
function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-white border border-[#ede8e3] rounded-xl px-3 py-2 shadow-xl text-xs">
      <p className="text-[#8b7355] mb-0.5 font-medium">{label}</p>
      <p className="font-bold text-gray-800">{payload[0].value?.toLocaleString()}</p>
    </div>
  )
}

// ── Section card ──────────────────────────────────────────────────
function Section({ icon: Icon, title, subtitle, children }) {
  return (
    <div className="bg-white rounded-2xl border border-[#ede8e3] p-6 hover:border-[#c4a882] transition-colors">
      <div className="mb-4">
        <h2 className="flex items-center gap-2 text-sm font-semibold text-gray-800"
            style={{ fontFamily: 'Space Grotesk, sans-serif' }}>
          <Icon size={15} className="text-[#8b7355]" />
          {title}
        </h2>
        {subtitle && <p className="text-xs text-gray-400 mt-0.5">{subtitle}</p>}
      </div>
      {children}
    </div>
  )
}

// ── Spinner ───────────────────────────────────────────────────────
function Spinner({ height = 200 }) {
  return (
    <div className={`flex items-center justify-center`} style={{ height }}>
      <div className="w-6 h-6 border-2 border-[#c4a882] border-t-transparent rounded-full animate-spin" />
    </div>
  )
}

// ── Hook data ─────────────────────────────────────────────────────
function useData(fetcher) {
  const [data,    setData]    = useState([])
  const [loading, setLoading] = useState(true)
  useEffect(() => {
    fetcher().then(setData).catch(console.error).finally(() => setLoading(false))
  }, [])
  return { data, loading }
}

export default function Analytics() {
  const sources = useData(() => api.topSources(10))
  const tags    = useData(() => api.topTags(10))
  const distrib = useData(() => api.confidenceDistribution())
  const trends  = useData(() => api.trends(30))

  const trendsFormatted = trends.data.map(d => ({
    ...d,
    label: d.date.slice(5).replace('-', '/'),
  }))

  return (
    <div className="space-y-6" style={{ fontFamily: 'Inter, sans-serif' }}>

      {/* ── En-tête ───────────────────────────────────────────── */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900"
            style={{ fontFamily: 'Space Grotesk, sans-serif' }}>
          Analytics
        </h1>
        <p className="text-sm text-gray-400 mt-0.5">
          Analyse et visualisation des données de threat intelligence
        </p>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-5">

        {/* ── Top sources ───────────────────────────────────── */}
        <Section icon={Database} title="Top 10 sources" subtitle="Volume d'IOCs par source de collecte">
          {sources.loading ? <Spinner height={260} /> : (
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={sources.data} layout="vertical"
                        margin={{ top: 0, right: 20, left: 0, bottom: 0 }}>
                <XAxis type="number" tick={{ fontSize: 10, fill: '#9ca3af' }}
                       axisLine={false} tickLine={false}
                       tickFormatter={v => v >= 1000 ? `${(v/1000).toFixed(0)}k` : v} />
                <YAxis type="category" dataKey="name" tick={{ fontSize: 10, fill: '#6b7280' }}
                       axisLine={false} tickLine={false} width={140}
                       tickFormatter={v => v.length > 18 ? v.slice(0, 18) + '…' : v} />
                <Tooltip content={<CustomTooltip />} cursor={{ fill: '#faf8f5' }} />
                <Bar dataKey="count" radius={[0, 6, 6, 0]} barSize={16}>
                  {sources.data.map((_, i) => (
                    <Cell key={i} fill={BEIGE_PALETTE[i % BEIGE_PALETTE.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </Section>

        {/* ── Top familles malware ──────────────────────────── */}
        <Section icon={Tag} title="Top 10 familles de malware" subtitle="Tags malware:* les plus représentés">
          {tags.loading ? <Spinner height={260} /> : (
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={tags.data} layout="vertical"
                        margin={{ top: 0, right: 20, left: 0, bottom: 0 }}>
                <XAxis type="number" tick={{ fontSize: 10, fill: '#9ca3af' }}
                       axisLine={false} tickLine={false}
                       tickFormatter={v => v >= 1000 ? `${(v/1000).toFixed(0)}k` : v} />
                <YAxis type="category" dataKey="name" tick={{ fontSize: 10, fill: '#6b7280' }}
                       axisLine={false} tickLine={false} width={100}
                       tickFormatter={v => v.replace('malware:', '')} />
                <Tooltip content={<CustomTooltip />} cursor={{ fill: '#faf8f5' }}
                         labelFormatter={l => l.replace('malware:', '')} />
                <Bar dataKey="count" radius={[0, 6, 6, 0]} barSize={16}>
                  {tags.data.map((_, i) => (
                    <Cell key={i} fill={BEIGE_PALETTE[i % BEIGE_PALETTE.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </Section>

        {/* ── Distribution confidence ───────────────────────── */}
        <Section icon={BarChart2} title="Distribution des scores de confiance"
                 subtitle="IOCs actifs répartis par tranche de score (0–100)">
          {distrib.loading ? <Spinner height={200} /> : (
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={distrib.data} margin={{ top: 0, right: 10, left: -20, bottom: 0 }}
                        barCategoryGap="25%">
                <XAxis dataKey="range" tick={{ fontSize: 10, fill: '#9ca3af' }}
                       axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 10, fill: '#9ca3af' }} axisLine={false} tickLine={false}
                       tickFormatter={v => v >= 1000 ? `${(v/1000).toFixed(0)}k` : v} />
                <Tooltip content={<CustomTooltip />} cursor={{ fill: '#faf8f5' }} />
                <Bar dataKey="count" radius={[6, 6, 0, 0]}>
                  {distrib.data.map((entry, i) => {
                    const base = parseInt(entry.range)
                    const color = base >= 70 ? '#ef4444'
                                : base >= 50 ? '#f59e0b'
                                : base >= 40 ? '#c4a882'
                                : '#e8d5b7'
                    return <Cell key={i} fill={color} />
                  })}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </Section>

        {/* ── Tendance 30 jours ─────────────────────────────── */}
        <Section icon={TrendingUp} title="Ingestion sur 30 jours"
                 subtitle="Nombre d'IOCs nouveaux créés par jour">
          {trends.loading ? <Spinner height={200} /> : (
            <ResponsiveContainer width="100%" height={200}>
              <AreaChart data={trendsFormatted} margin={{ top: 0, right: 10, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%"  stopColor="#c4a882" stopOpacity={0.2} />
                    <stop offset="95%" stopColor="#c4a882" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#f5f0eb" vertical={false} />
                <XAxis dataKey="label" tick={{ fontSize: 10, fill: '#9ca3af' }}
                       axisLine={false} tickLine={false} interval="preserveStartEnd" />
                <YAxis tick={{ fontSize: 10, fill: '#9ca3af' }} axisLine={false} tickLine={false}
                       tickFormatter={v => v >= 1000 ? `${(v/1000).toFixed(0)}k` : v} />
                <Tooltip content={<CustomTooltip />} />
                <Area type="monotone" dataKey="count" stroke="#8b7355" strokeWidth={2}
                      fill="url(#areaGrad)" dot={false}
                      activeDot={{ r: 5, fill: '#8b7355', strokeWidth: 0 }} />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </Section>

      </div>
    </div>
  )
}