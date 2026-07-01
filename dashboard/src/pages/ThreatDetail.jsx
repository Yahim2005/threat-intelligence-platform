// src/pages/ThreatDetail.jsx
import { useEffect, useState } from 'react'
import { ArrowLeft, Shield, Tag, List, BarChart2 } from 'lucide-react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts'
import { api } from '../api/client'
import TLPBadge from '../components/TLPBadge'
import StatusBadge from '../components/StatusBadge'

const TYPE_COLORS = ['#6366f1','#10b981','#f59e0b','#ef4444','#3b82f6','#8b5cf6','#ec4899']

function Section({ icon: Icon, title, children }) {
  return (
    <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5">
      <h2 className="flex items-center gap-2 text-sm font-semibold text-gray-700 mb-4">
        <Icon size={15} className="text-indigo-500" />
        {title}
      </h2>
      {children}
    </div>
  )
}

function MetaRow({ label, children }) {
  return (
    <div className="flex items-start gap-4 py-2 border-b border-gray-50 last:border-0">
      <span className="text-xs text-gray-400 w-32 shrink-0 pt-0.5">{label}</span>
      <span className="text-sm text-gray-700">{children}</span>
    </div>
  )
}

export default function ThreatDetail({ threatId, onBack, onOpenDetail }) {
  const [threat,  setThreat]  = useState(null)
  const [loading, setLoading] = useState(true)
  const [error,   setError]   = useState(null)

  useEffect(() => {
    setLoading(true)
    api.threatDetail(threatId)
      .then(setThreat)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [threatId])

  if (loading) return <div className="flex items-center justify-center h-64 text-gray-400">Chargement…</div>
  if (error)   return <div className="text-red-500 p-6">Erreur : {error}</div>
  if (!threat) return null

  const typeData = Object.entries(threat.indicators_by_type)
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value)

  const fmt = (dt) => dt ? new Date(dt).toLocaleDateString('fr-FR') : '—'

  return (
    <div className="space-y-5">
      {/* Retour */}
      <button
        onClick={onBack}
        className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-indigo-600 transition-colors"
      >
        <ArrowLeft size={16} /> Retour aux Threats
      </button>

      {/* En-tête */}
      <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5">
        <div className="flex items-start gap-3">
          <div className="p-2 bg-red-50 rounded-lg mt-0.5">
            <Shield size={18} className="text-red-500" />
          </div>
          <div className="flex-1">
            <h1 className="text-base font-bold text-gray-800">{threat.name}</h1>
            {threat.description && (
              <p className="text-sm text-gray-500 mt-1">{threat.description}</p>
            )}
          </div>
          <div className="text-right shrink-0">
            <p className="text-2xl font-bold text-gray-800">{threat.indicator_count}</p>
            <p className="text-xs text-gray-400">IOCs</p>
          </div>
        </div>
      </div>

      {/* Grille métadonnées + graphe */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-5">
        <Section icon={Shield} title="Informations">
          <MetaRow label="Type">{threat.threat_type}</MetaRow>
          <MetaRow label="TLP"><TLPBadge tlp={threat.tlp} /></MetaRow>
          <MetaRow label="Créé le">{fmt(threat.created_at)}</MetaRow>
          <MetaRow label="Confidence moy.">
            <div className="flex items-center gap-2">
              <div className="w-24 bg-gray-100 rounded-full h-1.5">
                <div className="bg-indigo-500 h-1.5 rounded-full" style={{ width: `${threat.avg_confidence}%` }} />
              </div>
              <span className="text-sm font-medium">{threat.avg_confidence ?? '—'}</span>
            </div>
          </MetaRow>
        </Section>

        <Section icon={BarChart2} title="Répartition par type d'IOC">
          {typeData.length === 0 ? (
            <p className="text-xs text-gray-400">Aucune donnée</p>
          ) : (
            <ResponsiveContainer width="100%" height={160}>
              <BarChart data={typeData} margin={{ top: 0, right: 10, left: -20, bottom: 0 }}>
                <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip />
                <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                  {typeData.map((_, i) => (
                    <Cell key={i} fill={TYPE_COLORS[i % TYPE_COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </Section>
      </div>

      {/* Top tags */}
      <Section icon={Tag} title="Tags dominants">
        {threat.top_tags?.length === 0 ? (
          <p className="text-xs text-gray-400">Aucun tag sur ce cluster</p>
        ) : (
          <div className="flex flex-wrap gap-2">
            {threat.top_tags.map(tag => (
              <span key={tag} className="px-2.5 py-1 bg-indigo-50 text-indigo-700 rounded-lg text-xs font-mono">
                {tag}
              </span>
            ))}
          </div>
        )}
      </Section>

      {/* Liste des IOCs */}
      <Section icon={List} title={`IOCs du cluster (${Math.min(threat.indicator_count, 50)} affichés)`}>
        <div className="overflow-x-auto">
          <table className="w-full text-sm min-w-[600px]">
            <thead className="bg-gray-50">
              <tr>
                {['Valeur', 'Type', 'Confidence', 'Statut', 'Source', 'Dernier vu'].map(h => (
                  <th key={h} className="text-left px-3 py-2 text-xs font-semibold text-gray-500 uppercase tracking-wide">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {threat.indicators.map(ind => (
                <tr key={ind.id} className="hover:bg-gray-50 transition-colors group">
                  <td className="px-3 py-2 max-w-[200px]">
                    <button
                      onClick={() => onOpenDetail && onOpenDetail(ind.value)}
                      className="font-mono text-xs text-indigo-600 hover:underline truncate block w-full text-left"
                      title={ind.value}
                    >
                      {ind.value}
                    </button>
                  </td>
                  <td className="px-3 py-2">
                    <span className="px-1.5 py-0.5 bg-indigo-50 text-indigo-700 rounded text-xs">{ind.type}</span>
                  </td>
                  <td className="px-3 py-2">
                    <div className="flex items-center gap-2">
                      <div className="w-12 bg-gray-100 rounded-full h-1.5">
                        <div className="bg-indigo-500 h-1.5 rounded-full" style={{ width: `${ind.confidence}%` }} />
                      </div>
                      <span className="text-xs text-gray-500 tabular-nums">{ind.confidence ?? '—'}</span>
                    </div>
                  </td>
                  <td className="px-3 py-2"><StatusBadge status={ind.status} /></td>
                  <td className="px-3 py-2 text-xs text-gray-500 truncate max-w-[120px]">{ind.source ?? '—'}</td>
                  <td className="px-3 py-2 text-xs text-gray-400 tabular-nums">
                    {ind.last_seen ? new Date(ind.last_seen).toLocaleDateString('fr-FR') : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Section>
    </div>
  )
}