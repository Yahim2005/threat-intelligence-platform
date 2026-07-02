// src/pages/Health.jsx
import { useEffect, useState } from 'react'
import { api } from '../api/client'
import {
  Activity, CheckCircle, AlertCircle, Zap,
  TrendingUp, Database, RefreshCw, Clock
} from 'lucide-react'

// ── Status badge collection run ───────────────────────────────────
function RunBadge({ status }) {
  const styles = {
    success: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    partial: 'bg-amber-50 text-amber-700 border-amber-200',
    failed:  'bg-red-50 text-red-700 border-red-200',
    running: 'bg-blue-50 text-blue-700 border-blue-200',
  }
  return (
    <span className={`px-2.5 py-0.5 rounded-full text-xs font-medium border ${styles[status] ?? 'bg-gray-50 text-gray-600 border-gray-200'}`}>
      {status}
    </span>
  )
}

// ── Stat card métriques ───────────────────────────────────────────
function MetricCard({ label, value, icon: Icon, accent }) {
  return (
    <div className={`rounded-2xl p-5 border transition-all hover:-translate-y-0.5 hover:shadow-md ${
      accent ? 'bg-[#2c1810] border-[#2c1810]' : 'bg-white border-[#ede8e3] hover:border-[#c4a882]'
    }`}>
      <div className="flex items-center justify-between mb-3">
        <p className={`text-xs font-medium uppercase tracking-wider ${accent ? 'text-[#e8d5b7]' : 'text-[#8b7355]'}`}>
          {label}
        </p>
        <div className={`p-1.5 rounded-lg ${accent ? 'bg-white/10' : 'bg-[#faf8f5]'}`}>
          <Icon size={13} className={accent ? 'text-[#e8d5b7]' : 'text-[#8b7355]'} />
        </div>
      </div>
      <p className={`text-2xl font-bold tabular-nums ${accent ? 'text-white' : 'text-gray-900'}`}
         style={{ fontFamily: 'Space Grotesk, sans-serif' }}>
        {value}
      </p>
    </div>
  )
}

function fmt(dt) {
  if (!dt) return '—'
  return new Date(dt).toLocaleString('fr-FR', { dateStyle: 'short', timeStyle: 'short' })
}

export default function Health() {
  const [health,      setHealth]      = useState(null)
  const [metrics,     setMetrics]     = useState(null)
  const [runs,        setRuns]        = useState([])
  const [loading,     setLoading]     = useState(true)
  const [refreshing,  setRefreshing]  = useState(false)
  const [lastRefresh, setLastRefresh] = useState(null)

  function load(isRefresh = false) {
    if (isRefresh) setRefreshing(true)
    else setLoading(true)

    Promise.all([api.health(), api.metrics(), api.collectionRuns(50)])
      .then(([h, m, r]) => {
        setHealth(h)
        setMetrics(m)
        setRuns(r)
        setLastRefresh(new Date())
      })
      .catch(console.error)
      .finally(() => { setLoading(false); setRefreshing(false) })
  }

  useEffect(() => { load() }, [])

  if (loading) return (
    <div className="flex flex-col items-center justify-center h-64 gap-3">
      <div className="w-6 h-6 border-2 border-[#c4a882] border-t-transparent rounded-full animate-spin" />
      <p className="text-sm text-gray-400">Chargement…</p>
    </div>
  )

  const isOk = health?.status === 'ok' && health?.db === 'ok'
  const maxPath = metrics ? Math.max(...Object.values(metrics.requests_by_path), 1) : 1

  return (
    <div className="space-y-5" style={{ fontFamily: 'Inter, sans-serif' }}>

      {/* ── En-tête ───────────────────────────────────────────── */}
      <div className="flex items-end justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold text-gray-900"
              style={{ fontFamily: 'Space Grotesk, sans-serif' }}>
            Health & Metrics
          </h1>
          <p className="text-sm text-gray-400 mt-0.5">
            Surveillance de l'API et de la pipeline de collecte
          </p>
        </div>
        <div className="flex items-center gap-3">
          {lastRefresh && (
            <span className="text-xs text-gray-400 flex items-center gap-1">
              <Clock size={11} />
              {lastRefresh.toLocaleTimeString('fr-FR')}
            </span>
          )}
          <button
            onClick={() => load(true)}
            disabled={refreshing}
            className="flex items-center gap-1.5 px-4 py-2 text-sm text-[#8b7355] border border-[#ede8e3] rounded-xl bg-white hover:border-[#c4a882] disabled:opacity-40 transition-all"
          >
            <RefreshCw size={13} className={refreshing ? 'animate-spin' : ''} />
            Rafraîchir
          </button>
        </div>
      </div>

      {/* ── Statut global ─────────────────────────────────────── */}
      <div className={`rounded-2xl border p-5 flex items-center gap-4 ${
        isOk ? 'bg-emerald-50 border-emerald-200' : 'bg-red-50 border-red-200'
      }`}>
        <div className={`p-2.5 rounded-xl ${isOk ? 'bg-emerald-100' : 'bg-red-100'}`}>
          {isOk
            ? <CheckCircle size={20} className="text-emerald-600" />
            : <AlertCircle size={20} className="text-red-600" />
          }
        </div>
        <div>
          <p className={`font-semibold text-sm ${isOk ? 'text-emerald-700' : 'text-red-700'}`}
             style={{ fontFamily: 'Space Grotesk, sans-serif' }}>
            {isOk ? 'Tous les systèmes sont opérationnels' : 'Dégradé — vérifier les logs'}
          </p>
          <p className="text-xs text-gray-500 mt-0.5">
            API : <span className="font-medium">{health?.status}</span> · 
            DB : <span className="font-medium">{health?.db}</span> · 
            Version : <span className="font-medium">{health?.version}</span>
          </p>
        </div>
      </div>

      {/* ── Métriques ─────────────────────────────────────────── */}
      {metrics && (
        <>
          <div className="grid grid-cols-2 xl:grid-cols-4 gap-4">
            <MetricCard label="Requêtes totales" value={metrics.requests_total.toLocaleString()} icon={TrendingUp} accent />
            <MetricCard label="Erreurs 4xx"      value={metrics.requests_4xx}                    icon={AlertCircle} />
            <MetricCard label="Erreurs 5xx"      value={metrics.requests_5xx}                    icon={AlertCircle} />
            <MetricCard label="Latence moy."     value={`${metrics.avg_latency_ms} ms`}          icon={Zap} />
          </div>

          {/* Endpoints */}
          <div className="bg-white rounded-2xl border border-[#ede8e3] p-6">
            <h2 className="text-sm font-semibold text-gray-800 mb-4"
                style={{ fontFamily: 'Space Grotesk, sans-serif' }}>
              Requêtes par endpoint
            </h2>
            <div className="space-y-3">
              {Object.entries(metrics.requests_by_path)
                .sort((a, b) => b[1] - a[1])
                .slice(0, 10)
                .map(([path, count]) => {
                  const pct = (count / maxPath) * 100
                  return (
                    <div key={path} className="flex items-center gap-3">
                      <span className="text-xs font-mono text-[#8b7355] w-48 truncate shrink-0">{path}</span>
                      <div className="flex-1 bg-[#f5f0eb] rounded-full h-1.5">
                        <div
                          className="bg-[#8b7355] h-1.5 rounded-full transition-all duration-500"
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                      <span className="text-xs text-gray-400 tabular-nums w-8 text-right shrink-0">{count}</span>
                    </div>
                  )
                })}
            </div>
          </div>
        </>
      )}

      {/* ── Historique des collectes ───────────────────────────── */}
      <div className="bg-white rounded-2xl border border-[#ede8e3] overflow-hidden">
        <div className="flex items-center gap-2 px-6 py-4 border-b border-[#f5f0eb]">
          <Database size={15} className="text-[#8b7355]" />
          <h2 className="text-sm font-semibold text-gray-800"
              style={{ fontFamily: 'Space Grotesk, sans-serif' }}>
            Historique des collectes
          </h2>
          <span className="text-xs text-gray-400 ml-auto">{runs.length} derniers runs</span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm min-w-[700px]">
            <thead>
              <tr className="border-b border-[#f5f0eb]">
                {['Source', 'Démarré', 'Durée', 'Statut', 'Créés', 'Mis à jour', 'Erreurs'].map(h => (
                  <th key={h} className="text-left px-5 py-3.5 text-xs font-semibold text-[#8b7355] uppercase tracking-wider bg-[#faf8f5]">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {runs.length === 0 ? (
                <tr>
                  <td colSpan={7} className="text-center py-12 text-gray-400 text-sm">
                    Aucun run enregistré
                  </td>
                </tr>
              ) : runs.map(run => (
                <tr key={run.id} className="border-b border-[#faf8f5] hover:bg-[#faf8f5] transition-colors">
                  <td className="px-5 py-3.5 text-xs font-medium text-gray-700 max-w-[160px] truncate" title={run.source}>
                    {run.source}
                  </td>
                  <td className="px-5 py-3.5 text-xs text-gray-400 tabular-nums">{fmt(run.started_at)}</td>
                  <td className="px-5 py-3.5 text-xs text-gray-400 tabular-nums">
                    {run.duration_s != null ? `${run.duration_s}s` : '—'}
                  </td>
                  <td className="px-5 py-3.5"><RunBadge status={run.status} /></td>
                  <td className="px-5 py-3.5 text-xs font-medium text-emerald-600 tabular-nums">
                    +{run.items_created.toLocaleString()}
                  </td>
                  <td className="px-5 py-3.5 text-xs text-blue-500 tabular-nums">
                    {run.items_updated.toLocaleString()}
                  </td>
                  <td className="px-5 py-3.5 text-xs tabular-nums">
                    {run.items_errors > 0
                      ? <span className="text-red-500 font-medium">{run.items_errors}</span>
                      : <span className="text-gray-200">0</span>
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
