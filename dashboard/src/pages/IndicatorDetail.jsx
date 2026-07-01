// src/pages/IndicatorDetail.jsx
import { useEffect, useState } from 'react'
import { ArrowLeft, Shield, Clock, Tag, Link2, BarChart2, MapPin } from 'lucide-react'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer
} from 'recharts'
import { api } from '../api/client'
import TLPBadge from '../components/TLPBadge'
import StatusBadge from '../components/StatusBadge'

// ─── Badge de risque ─────────────────────────────────────────────────────────
function RiskBadge({ confidence }) {
  if (confidence == null) return <span className="text-gray-400 text-sm">—</span>
  if (confidence >= 75)
    return <span className="px-3 py-1 bg-red-100 text-red-700 rounded-full text-sm font-semibold">🔴 Menace confirmée ({confidence})</span>
  if (confidence >= 40)
    return <span className="px-3 py-1 bg-amber-100 text-amber-700 rounded-full text-sm font-semibold">🟡 Suspect ({confidence})</span>
  return <span className="px-3 py-1 bg-green-100 text-green-700 rounded-full text-sm font-semibold">🟢 Risque faible ({confidence})</span>
}

// ─── Section avec titre ───────────────────────────────────────────────────────
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

// ─── Ligne de métadonnée ──────────────────────────────────────────────────────
function MetaRow({ label, children }) {
  return (
    <div className="flex items-start gap-4 py-2 border-b border-gray-50 last:border-0">
      <span className="text-xs text-gray-400 w-28 shrink-0 pt-0.5">{label}</span>
      <span className="text-sm text-gray-700 font-mono break-all">{children}</span>
    </div>
  )
}

// ─── Composant principal ──────────────────────────────────────────────────────
export default function IndicatorDetail({ value, onBack }) {
  const [ind,      setInd]      = useState(null)
  const [related,  setRelated]  = useState([])
  const [timeline, setTimeline] = useState([])
  const [loading,  setLoading]  = useState(true)
  const [error,    setError]    = useState(null)

  useEffect(() => {
    setLoading(true)
    Promise.all([
      api.lookupByValue(value),
      api.related(value),
      api.timeline(value, 30),
    ])
      .then(([i, r, t]) => {
        setInd(i)
        setRelated(r)
        setTimeline(t.map(p => ({ ...p, label: p.date.slice(5).replace('-', '/') })))
      })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [value])

  if (loading) return <div className="flex items-center justify-center h-64 text-gray-400">Chargement…</div>
  if (error)   return <div className="text-red-500 p-6">Erreur : {error}</div>
  if (!ind)    return null

  const fmt = (dt) => dt ? new Date(dt).toLocaleString('fr-FR') : '—'

  return (
    <div className="space-y-5">
      {/* En-tête */}
      <div className="flex items-center gap-3">
        <button
          onClick={onBack}
          className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-indigo-600 transition-colors"
        >
          <ArrowLeft size={16} /> Retour
        </button>
      </div>

      <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="text-xs text-gray-400 mb-1 uppercase tracking-wide">Indicateur</p>
            <p className="font-mono text-base font-semibold text-gray-800 break-all">{ind.value}</p>
          </div>
          <RiskBadge confidence={ind.confidence} />
        </div>
      </div>

      {/* Grille principale */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-5">

        {/* Métadonnées */}
        <Section icon={Shield} title="Informations">
          <MetaRow label="Type">
            <span className="px-2 py-0.5 bg-indigo-50 text-indigo-700 rounded text-xs font-medium not-italic">
              {ind.type}
            </span>
          </MetaRow>
          <MetaRow label="Statut"><StatusBadge status={ind.status} /></MetaRow>
          <MetaRow label="TLP"><TLPBadge tlp={ind.tlp} /></MetaRow>
          <MetaRow label="Source">{ind.source ?? '—'}</MetaRow>
          <MetaRow label="Premier vu">{fmt(ind.first_seen)}</MetaRow>
          <MetaRow label="Dernier vu">{fmt(ind.last_seen)}</MetaRow>
          <MetaRow label="Confidence">{ind.confidence ?? '—'} / 100</MetaRow>
        </Section>

        {/* Tags + MITRE */}
        
        <div className="space-y-5">
          <Section icon={Tag} title="Tags">
            {ind.tags?.length > 0 ? (
              <div className="flex flex-wrap gap-2">
                {ind.tags.map(tag => (
                  <span key={tag} className="px-2 py-1 bg-gray-100 text-gray-600 rounded-lg text-xs font-mono">
                    {tag}
                  </span>
                ))}
              </div>
            ) : (
              <p className="text-xs text-gray-400">Aucun tag</p>
            )}
          </Section>

          <Section icon={Shield} title="Techniques MITRE ATT&CK">
            {ind.attack_techniques?.length > 0 ? (
              <div className="flex flex-wrap gap-2">
                {ind.attack_techniques.map(t => (
                  <a
                    key={t}
                    href={`https://attack.mitre.org/techniques/${t.replace('.', '/')}`}
                    target="_blank"
                    rel="noreferrer"
                    className="px-2 py-1 bg-purple-50 text-purple-700 rounded-lg text-xs font-mono hover:bg-purple-100 transition-colors"
                  >
                    {t}
                  </a>
                ))}
              </div>
            ) : (
              <p className="text-xs text-gray-400">Aucune technique associée</p>
            )}
          </Section>
        </div>
      </div>

      {/* Timeline */}
      <Section icon={BarChart2} title="Timeline des sightings (30 jours)">
        {timeline.length === 0 ? (
          <p className="text-xs text-gray-400">Aucun sighting enregistré sur cette période.</p>
        ) : (
          <ResponsiveContainer width="100%" height={180}>
            <LineChart data={timeline} margin={{ top: 0, right: 10, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="label" tick={{ fontSize: 11 }} interval="preserveStartEnd" />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip formatter={(v) => [v, 'sightings']} />
              <Line type="monotone" dataKey="sightings" stroke="#6366f1" strokeWidth={2} dot={false} activeDot={{ r: 4 }} />
            </LineChart>
          </ResponsiveContainer>
        )}
      </Section>
      {/* GeoIP — uniquement pour les IPs */}
      {ind.geoip && ind.geoip.country_code && (
        <Section icon={MapPin} title="Géolocalisation">
          <div className="grid grid-cols-2 gap-x-6">
            <div>
              <p className="text-xs text-gray-400 mb-0.5">Pays</p>
              <p className="text-sm text-gray-700 font-medium">
                {ind.geoip.country_name ?? '—'}
                {ind.geoip.country_code && (
                  <span className="ml-2 text-xs text-gray-400">({ind.geoip.country_code})</span>
                )}
              </p>
            </div>
            <div>
              <p className="text-xs text-gray-400 mb-0.5">Ville</p>
              <p className="text-sm text-gray-700">{ind.geoip.city ?? '—'}</p>
            </div>
            <div className="mt-3">
              <p className="text-xs text-gray-400 mb-0.5">ASN</p>
              <p className="text-sm text-gray-700 font-mono">AS{ind.geoip.asn ?? '—'}</p>
            </div>
            <div className="mt-3">
              <p className="text-xs text-gray-400 mb-0.5">Organisation</p>
              <p className="text-sm text-gray-700">{ind.geoip.asn_org ?? '—'}</p>
            </div>
            {ind.geoip.latitude != null && ind.geoip.longitude != null && (
              <div className="mt-3 col-span-2">
                <p className="text-xs text-gray-400 mb-0.5">Coordonnées</p>
                <a
                  href={`https://www.openstreetmap.org/?mlat=${ind.geoip.latitude}&mlon=${ind.geoip.longitude}&zoom=10`}
                  target="_blank"
                  rel="noreferrer"
                  className="text-sm text-indigo-600 hover:underline font-mono"
                >
                  {ind.geoip.latitude}, {ind.geoip.longitude} ↗
                </a>
              </div>
            )}
          </div>
        </Section>
      )}

      {/* IOCs liés */}
      <Section icon={Link2} title={`IOCs liés (${related.length})`}>
        {related.length === 0 ? (
          <p className="text-xs text-gray-400">Aucun IOC corrélé trouvé.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm min-w-[500px]">
              <thead className="bg-gray-50">
                <tr>
                  {['Valeur', 'Type', 'Confidence', 'Relation', 'Règle'].map(h => (
                    <th key={h} className="text-left px-3 py-2 text-xs font-semibold text-gray-500 uppercase tracking-wide">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {related.map((r, i) => (
                  <tr key={i} className="hover:bg-gray-50">
                    <td className="px-3 py-2 font-mono text-xs text-gray-700 max-w-[180px] truncate" title={r.value}>{r.value}</td>
                    <td className="px-3 py-2">
                      <span className="px-1.5 py-0.5 bg-indigo-50 text-indigo-700 rounded text-xs">{r.type}</span>
                    </td>
                    <td className="px-3 py-2 text-xs text-gray-500 tabular-nums">{r.confidence ?? '—'}</td>
                    <td className="px-3 py-2">
                      <span className="px-1.5 py-0.5 bg-amber-50 text-amber-700 rounded text-xs">{r.relationship_type}</span>
                    </td>
                    <td className="px-3 py-2 font-mono text-xs text-gray-400 max-w-[150px] truncate" title={r.rule}>{r.rule ?? '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Section>
    </div>
  )
}
