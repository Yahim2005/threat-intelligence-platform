// src/pages/Health.jsx
import { useEffect, useState } from 'react'
import { api } from '../api/client'
import { Activity, CheckCircle, AlertCircle, Clock, Zap, TrendingUp } from 'lucide-react'
import StatCard from '../components/StatCard'

export default function Health() {
  const [health,   setHealth]   = useState(null)
  const [metrics,  setMetrics]  = useState(null)
  const [loading,  setLoading]  = useState(true)
  const [lastRefresh, setLastRefresh] = useState(null)

  function load() {
    setLoading(true)
    Promise.all([api.health(), api.metrics()])
      .then(([h, m]) => { setHealth(h); setMetrics(m); setLastRefresh(new Date()) })
      .catch(console.error)
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  if (loading && !health) return (
    <div className="flex items-center justify-center h-64 text-gray-400">Chargement…</div>
  )

  const isOk = health?.status === 'ok' && health?.db === 'ok'

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-800">Health & Metrics</h1>
        <div className="flex items-center gap-3">
          {lastRefresh && (
            <span className="text-xs text-gray-400">
              Mis à jour {lastRefresh.toLocaleTimeString('fr-FR')}
            </span>
          )}
          <button onClick={load}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-indigo-600 border border-indigo-200 rounded-lg hover:bg-indigo-50 transition-colors">
            <Activity size={14} /> Rafraîchir
          </button>
        </div>
      </div>

      {/* Statut global */}
      <div className={`rounded-xl border p-5 flex items-center gap-4 ${isOk ? 'bg-emerald-50 border-emerald-200' : 'bg-red-50 border-red-200'}`}>
        {isOk
          ? <CheckCircle size={24} className="text-emerald-500" />
          : <AlertCircle size={24} className="text-red-500" />}
        <div>
          <p className={`font-semibold ${isOk ? 'text-emerald-700' : 'text-red-700'}`}>
            {isOk ? 'Tous les systèmes sont opérationnels' : 'Dégradé — vérifier les logs'}
          </p>
          <p className="text-xs text-gray-500 mt-0.5">
            API : {health?.status} · DB : {health?.db} · Version : {health?.version}
          </p>
        </div>
      </div>

      {/* Métriques */}
      {metrics && (
        <>
          <div className="grid grid-cols-2 xl:grid-cols-4 gap-4">
            <StatCard label="Requêtes totales" value={metrics.requests_total}  icon={TrendingUp} color="indigo" />
            <StatCard label="Erreurs 4xx"      value={metrics.requests_4xx}    icon={AlertCircle} color="amber" />
            <StatCard label="Erreurs 5xx"      value={metrics.requests_5xx}    icon={AlertCircle} color="red" />
            <StatCard label="Latence moyenne"  value={`${metrics.avg_latency_ms} ms`} icon={Zap} color="emerald" />
          </div>

          {/* Répartition par endpoint */}
          <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5">
            <h2 className="text-sm font-semibold text-gray-700 mb-4">Requêtes par endpoint</h2>
            <div className="space-y-3">
              {Object.entries(metrics.requests_by_path)
                .sort((a, b) => b[1] - a[1])
                .map(([path, count]) => {
                  const max = Math.max(...Object.values(metrics.requests_by_path))
                  const pct = max > 0 ? (count / max) * 100 : 0
                  return (
                    <div key={path} className="flex items-center gap-3">
                      <span className="text-xs font-mono text-gray-600 w-40 truncate">{path}</span>
                      <div className="flex-1 bg-gray-100 rounded-full h-2">
                        <div className="bg-indigo-500 h-2 rounded-full transition-all" style={{ width: `${pct}%` }} />
                      </div>
                      <span className="text-xs text-gray-500 w-10 text-right">{count}</span>
                    </div>
                  )
                })}
            </div>
          </div>
        </>
      )}
    </div>
  )
}
