// src/pages/Overview.jsx
import { useEffect, useState } from 'react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend } from 'recharts'
import { AlertTriangle, CheckCircle, Clock, ShieldOff } from 'lucide-react'
import { api } from '../api/client'
import StatCard from '../components/StatCard'

const TYPE_COLORS = ['#6366f1','#10b981','#f59e0b','#ef4444','#3b82f6','#8b5cf6','#ec4899']
const TLP_COLORS  = { CLEAR: '#9ca3af', GREEN: '#10b981', AMBER: '#f59e0b', AMBER_STRICT: '#f97316', RED: '#ef4444' }

export default function Overview() {
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    api.stats()
      .then(setStats)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="flex items-center justify-center h-64 text-gray-400">Chargement…</div>
  if (error)   return <div className="text-red-500 p-6">Erreur : {error}</div>
  if (!stats)  return null

  const typeData = Object.entries(stats.indicators_by_type ?? {})
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value)

  const tlpData = Object.entries(stats.indicators_by_tlp ?? {})
    .map(([name, value]) => ({ name, value }))

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-bold text-gray-800">Overview</h1>

      {/* Stat cards */}
      <div className="grid grid-cols-2 xl:grid-cols-4 gap-4">
        <StatCard label="Total IOCs"    value={stats.total_indicators}  icon={AlertTriangle} color="indigo" />
        <StatCard label="Actifs"        value={stats.active_indicators} icon={CheckCircle}   color="emerald" />
        <StatCard label="Expirés"       value={stats.expired_indicators ?? '—'} icon={Clock} color="amber" />
        <StatCard label="Whitelistés"   value={stats.whitelisted_indicators ?? '—'} icon={ShieldOff} color="blue" />
      </div>

      {/* Graphiques */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        {/* Répartition par type */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
          <h2 className="text-sm font-semibold text-gray-700 mb-4">IOCs par type</h2>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={typeData} margin={{ top: 0, right: 10, left: -20, bottom: 0 }}>
              <XAxis dataKey="name" tick={{ fontSize: 12 }} />
              <YAxis tick={{ fontSize: 12 }} />
              <Tooltip />
              <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                {typeData.map((_, i) => (
                  <Cell key={i} fill={TYPE_COLORS[i % TYPE_COLORS.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Répartition par TLP */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
          <h2 className="text-sm font-semibold text-gray-700 mb-4">IOCs par TLP</h2>
          <ResponsiveContainer width="100%" height={220}>
            <PieChart>
              <Pie data={tlpData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={80} label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}>
                {tlpData.map((entry, i) => (
                  <Cell key={i} fill={TLP_COLORS[entry.name] ?? '#9ca3af'} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  )
}
