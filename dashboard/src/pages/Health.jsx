// src/pages/Health.jsx
import { useEffect, useState } from 'react'
import { api } from '../api/client'
import { Activity, CheckCircle, AlertCircle, Clock, Zap, TrendingUp, Database, XCircle } from 'lucide-react'
import StatCard from '../components/StatCard'

function StatusBadge({ status }) {
  const styles = {
    success: 'bg-emerald-100 text-emerald-700',
    partial:  'bg-amber-100 text-amber-700',
    failed:   'bg-red-100 text-red-700',
    running:  'bg-blue-100 text-blue-700',
  }
  return (
    <span className={`px-2 py-0.5 rounded text-xs font-medium ${styles[status] ?? 'bg-gray-100 text-gray-600'}`}>
      {status}
    </span>
  )
}

function fmt(dt) {
  if (!dt) return '—'
  return new Date(dt).toLocaleString('fr-FR', { dateStyle: 'short', timeStyle: 'short' })
}

export default function Health() {
  const [health,   setHealth]   = useState(null)
  const [metrics,  setMetrics]  = useState(null)
  const [runs,     setRuns]     = useState([])
  const [loading,  setLoading]  = useState(true)
  const [lastRefresh, setLastRefresh] = useState(null)

  function load() {
    setLoading(true)
    Promise.all([api.health(), api.metrics(), api.collectionRuns(50)])
      .then(([h, m, r]) => {
        setHealth(h)
        setMetrics(m)
        setRuns(r)
        setLastRefresh(new Date())
      })
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
            <StatCard label="Requêtes totales" value={metrics.requests_total}        icon={TrendingUp} color="indigo" />
            <StatCard label="Erreurs 4xx"      value={metrics.requests_4xx}          icon={AlertCircle} color="amber" />
            <StatCard label="Erreurs 5xx"      value={metrics.requests_5xx}          icon={AlertCircle} color="red" />
            <StatCard label="Latence moyenne"  value={`${metrics.avg_latency_ms} ms`} icon={Zap}        color="emerald" />
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

      {/* Historique des collection runs */}
      <div className="bg-white rounded-xl border border-gray-100 shadow-sm">
        <div className="flex items-center gap-2 px-5 py-4 border-b border-gray-100">
          <Database size={15} className="text-indigo-500" />
          <h2 className="text-sm font-semibold text-gray-700">Historique des collectes</h2>
          <span className="text-xs text-gray-400 ml-auto">{runs.length} derniers runs</span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm min-w-[700px]">
            <thead className="bg-gray-50 border-b border-gray-100">
              <tr>
                {['Source', 'Démarré', 'Durée', 'Statut', 'Créés', 'Mis à jour', 'Erreurs'].map(h => (
                  <th key={h} className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {runs.length === 0 ? (
                <tr><td colSpan={7} className="text-center py-8 text-gray-400 text-sm">Aucun run enregistré</td></tr>
              ) : runs.map(run => (
                <tr key={run.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-3 text-xs font-medium text-gray-700 max-w-[160px] truncate" title={run.source}>
                    {run.source}
                  </td>
                  <td className="px-4 py-3 text-xs text-gray-500 tabular-nums">{fmt(run.started_at)}</td>
                  <td className="px-4 py-3 text-xs text-gray-500 tabular-nums">
                    {run.duration_s != null ? `${run.duration_s}s` : '—'}
                  </td>
                  <td className="px-4 py-3"><StatusBadge status={run.status} /></td>
                  <td className="px-4 py-3 text-xs text-emerald-600 tabular-nums font-medium">
                    +{run.items_created.toLocaleString()}
                  </td>
                  <td className="px-4 py-3 text-xs text-blue-600 tabular-nums">
                    {run.items_updated.toLocaleString()}
                  </td>
                  <td className="px-4 py-3 text-xs tabular-nums">
                    {run.items_errors > 0
                      ? <span className="text-red-500 font-medium">{run.items_errors}</span>
                      : <span className="text-gray-300">0</span>
                    }
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
