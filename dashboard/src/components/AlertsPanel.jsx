// src/components/AlertsPanel.jsx
import { useEffect, useState } from 'react'
import { AlertTriangle, ChevronRight, RefreshCw } from 'lucide-react'
import { api } from '../api/client'

function confidenceColor(score) {
  if (score >= 85) return 'bg-red-100 text-red-700 border-red-200'
  if (score >= 75) return 'bg-amber-100 text-amber-700 border-amber-200'
  return 'bg-blue-50 text-blue-700 border-blue-200'
}

function TypePill({ type }) {
  return (
    <span className="px-1.5 py-0.5 bg-gray-100 text-gray-500 rounded text-xs font-mono">
      {type}
    </span>
  )
}

export default function AlertsPanel({ onOpenDetail }) {
  const [alerts,  setAlerts]  = useState([])
  const [loading, setLoading] = useState(true)
  const [refresh, setRefresh] = useState(0)

  useEffect(() => {
    setLoading(true)
    api.alerts(75, 168)
      .then(setAlerts)
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [refresh])

  return (
    <div className="bg-white rounded-xl border border-gray-100 shadow-sm">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100">
        <div className="flex items-center gap-2">
          <AlertTriangle size={15} className="text-red-500" />
          <h2 className="text-sm font-semibold text-gray-700">Alertes haute confiance</h2>
          {alerts.length > 0 && (
            <span className="px-2 py-0.5 bg-red-500 text-white text-xs font-bold rounded-full">
              {alerts.length}
            </span>
          )}
        </div>
        <button
          onClick={() => setRefresh(r => r + 1)}
          className="p-1.5 rounded-lg text-gray-400 hover:text-indigo-600 hover:bg-indigo-50 transition-colors"
          title="Rafraîchir"
        >
          <RefreshCw size={13} className={loading ? 'animate-spin' : ''} />
        </button>
      </div>

      {/* Contenu */}
      <div className="divide-y divide-gray-50">
        {loading ? (
          <div className="py-8 text-center text-sm text-gray-400">Chargement…</div>
        ) : alerts.length === 0 ? (
          <div className="py-8 text-center text-sm text-gray-400">
            Aucune alerte sur les 7 derniers jours
          </div>
        ) : (
          alerts.map(alert => (
            <div
              key={alert.id}
              className="flex items-center gap-3 px-5 py-3 hover:bg-gray-50 transition-colors group"
            >
              {/* Score badge */}
              <span className={`text-xs font-bold px-2 py-1 rounded-lg border shrink-0 ${confidenceColor(alert.confidence)}`}>
                {alert.confidence}
              </span>

              {/* Info principale */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-0.5">
                  <TypePill type={alert.type} />
                  <span className="text-xs text-gray-400 truncate">{alert.source ?? '—'}</span>
                </div>
                <p className="font-mono text-xs text-gray-700 truncate" title={alert.value}>
                  {alert.value}
                </p>
                {alert.tags?.length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-1">
                    {alert.tags.slice(0, 3).map(tag => (
                      <span key={tag} className="px-1.5 py-0.5 bg-indigo-50 text-indigo-600 rounded text-xs">
                        {tag}
                      </span>
                    ))}
                    {alert.tags.length > 3 && (
                      <span className="text-xs text-gray-400">+{alert.tags.length - 3}</span>
                    )}
                  </div>
                )}
              </div>

              {/* Bouton détail */}
              {onOpenDetail && (
                <button
                  onClick={() => onOpenDetail(alert.value)}
                  className="shrink-0 p-1 rounded-lg text-gray-300 group-hover:text-indigo-500 transition-colors"
                  title="Voir le détail"
                >
                  <ChevronRight size={15} />
                </button>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  )
}