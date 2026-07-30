// src/pages/ThreatDetail.jsx
import { useEffect, useState } from 'react'
import { ArrowLeft, Shield, Tag, List, BarChart2, Building2, Server } from 'lucide-react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts'
import { api } from '../api/client'
import TLPBadge from '../components/TLPBadge'
import StatusBadge from '../components/StatusBadge'
import TechInfoPanel from '../components/TechInfoPanel'

const BEIGE_PALETTE = ['#8b7355','#c4a882','#a0845c','#6b5740','#d4b896','#bfa07a','#e8d5b7']

const MECHANISM_LABELS = {
  typosquat: 'typosquatting',
  ct: 'certificats suspects',
  nrd_watch: 'domaines récents suspects',
}

// ── Tooltip custom ────────────────────────────────────────────────
function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-white border border-[#ede8e3] rounded-xl px-3 py-2 shadow-xl text-xs">
      <p className="text-[#8b7355] mb-0.5">{label}</p>
      <p className="font-bold text-gray-800">{payload[0].value?.toLocaleString()} IOCs</p>
    </div>
  )
}

// ── Section card ──────────────────────────────────────────────────
function Section({ icon: Icon, title, children }) {
  return (
    <div className="bg-white rounded-2xl border border-[#ede8e3] p-5">
      <h2 className="flex items-center gap-2 text-sm font-semibold text-gray-800 mb-4"
          style={{ fontFamily: 'Space Grotesk, sans-serif' }}>
        <Icon size={14} className="text-[#8b7355]" />
        {title}
      </h2>
      {children}
    </div>
  )
}

// ── Ligne métadonnée ──────────────────────────────────────────────
function MetaRow({ label, children }) {
  return (
    <div className="flex items-start gap-4 py-2.5 border-b border-[#faf8f5] last:border-0">
      <span className="text-xs text-gray-400 w-32 shrink-0 pt-0.5 uppercase tracking-wide">{label}</span>
      <span className="text-sm text-gray-700">{children}</span>
    </div>
  )
}

// ── Couleur confidence ────────────────────────────────────────────
function confidenceStyle(score) {
  if (score >= 60) return { bar: 'bg-red-400',    text: 'text-red-600' }
  if (score >= 50) return { bar: 'bg-orange-400', text: 'text-orange-600' }
  if (score >= 40) return { bar: 'bg-amber-400',  text: 'text-amber-600' }
  return                  { bar: 'bg-yellow-300', text: 'text-yellow-600' }
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

  if (loading) return (
    <div className="flex flex-col items-center justify-center h-64 gap-3">
      <div className="w-6 h-6 border-2 border-[#c4a882] border-t-transparent rounded-full animate-spin" />
      <p className="text-sm text-gray-400">Chargement du cluster…</p>
    </div>
  )
  if (error)   return <div className="text-red-500 p-6">Erreur : {error}</div>
  if (!threat) return null

  const typeData = Object.entries(threat.indicators_by_type)
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value)

  const fmt = (dt) => dt ? new Date(dt).toLocaleDateString('fr-FR') : '—'
  const score = Math.round(threat.avg_confidence ?? 0)
  const { bar, text } = confidenceStyle(score)

  return (
    <div className="space-y-5" style={{ fontFamily: 'Inter, sans-serif' }}>

      {/* ── Retour ───────────────────────────────────────────── */}
      <button
        onClick={onBack}
        className="flex items-center gap-1.5 text-sm text-[#8b7355] hover:text-[#6b5740] transition-colors"
      >
        <ArrowLeft size={15} /> Retour aux Threats
      </button>

      {/* ── En-tête ───────────────────────────────────────────── */}
      <div className="bg-white rounded-2xl border border-[#ede8e3] p-6">
        <div className="flex items-start gap-4">
          <div className="p-3 bg-[#faf8f5] rounded-xl shrink-0">
            <Shield size={20} className="text-[#8b7355]" />
          </div>
          <div className="flex-1 min-w-0">
            <h1 className="text-lg font-bold text-gray-900 leading-snug"
                style={{ fontFamily: 'Space Grotesk, sans-serif' }}>
              {threat.name}
            </h1>
            {threat.description && (
              <p className="text-sm text-gray-400 mt-1 line-clamp-2">{threat.description}</p>
            )}
            {/* Barre confidence */}
            <div className="flex items-center gap-3 mt-3">
              <div className="flex-1 max-w-[200px] bg-[#f5f0eb] rounded-full h-1.5">
                <div className={`${bar} h-1.5 rounded-full transition-all duration-700`}
                     style={{ width: `${score}%` }} />
              </div>
              <span className={`text-sm font-bold tabular-nums ${text}`}>{score}/100</span>
            </div>
          </div>
          <div className="text-right shrink-0">
            <p className="text-3xl font-bold text-gray-900 tabular-nums"
               style={{ fontFamily: 'Space Grotesk, sans-serif' }}>
              {threat.indicator_count.toLocaleString()}
            </p>
            <p className="text-xs text-gray-400 mt-0.5">IOCs</p>
          </div>
        </div>
      </div>

      <TechInfoPanel>
        <p>
          Détail d'une menace : l'institution ciblée, le décompte d'indicateurs par mécanisme de
          détection (typosquatting, certificats, domaines récents), les IPs exposées associées à
          cette même institution (surface d'attaque), et la liste complète des indicateurs
          membres du cluster.
        </p>
      </TechInfoPanel>

      {/* ── Grille infos + graphe ─────────────────────────────── */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-5">

        <Section icon={Shield} title="Informations">
          {threat.institution && (
            <MetaRow label="Institution">
              <span className="flex items-center gap-1.5 font-medium text-[#8b7355]">
                <Building2 size={13} /> {threat.institution}
              </span>
            </MetaRow>
          )}
          <MetaRow label="Type">{threat.threat_type}</MetaRow>
          <MetaRow label="TLP"><TLPBadge tlp={threat.tlp} /></MetaRow>
          <MetaRow label="1ère observation">{fmt(threat.first_seen)}</MetaRow>
          <MetaRow label="Créé le">{fmt(threat.created_at)}</MetaRow>
          {Object.keys(threat.mechanism_counts || {}).length > 0 && (
            <MetaRow label="Mécanismes">
              <div className="flex flex-wrap gap-1.5">
                {Object.entries(threat.mechanism_counts).map(([mech, count]) => (
                  <span key={mech}
                    className="px-2 py-0.5 bg-[#faf8f5] text-[#8b7355] border border-[#ede8e3] rounded-full text-xs">
                    {count} {MECHANISM_LABELS[mech] ?? mech}
                  </span>
                ))}
              </div>
            </MetaRow>
          )}
          <MetaRow label="Confidence moy.">
            <div className="flex items-center gap-2">
              <div className="w-24 bg-[#f5f0eb] rounded-full h-1.5">
                <div className={`${bar} h-1.5 rounded-full`} style={{ width: `${score}%` }} />
              </div>
              <span className={`text-sm font-semibold ${text}`}>{score}</span>
            </div>
          </MetaRow>
        </Section>

        <Section icon={BarChart2} title="Répartition par type d'IOC">
          {typeData.length === 0 ? (
            <p className="text-xs text-gray-400">Aucune donnée</p>
          ) : (
            <ResponsiveContainer width="100%" height={160}>
              <BarChart data={typeData} margin={{ top: 0, right: 10, left: -20, bottom: 0 }}
                        barCategoryGap="30%">
                <XAxis dataKey="name" tick={{ fontSize: 11, fill: '#9ca3af' }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 11, fill: '#9ca3af' }} axisLine={false} tickLine={false} />
                <Tooltip content={<CustomTooltip />} cursor={{ fill: '#faf8f5' }} />
                <Bar dataKey="value" radius={[6, 6, 0, 0]}>
                  {typeData.map((_, i) => (
                    <Cell key={i} fill={BEIGE_PALETTE[i % BEIGE_PALETTE.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </Section>
      </div>

      {/* ── IPs exposées (surface d'attaque de l'institution) ──── */}
      {threat.exposed_ips?.length > 0 && (
        <Section icon={Server} title={`Surface d'attaque exposée (${threat.exposed_ips.length} IP${threat.exposed_ips.length > 1 ? 's' : ''})`}>
          <div className="flex flex-wrap gap-2">
            {threat.exposed_ips.map(ip => (
              <span key={ip}
                className="px-2.5 py-1 bg-red-50 text-red-600 border border-red-100 rounded-full text-xs font-mono">
                {ip}
              </span>
            ))}
          </div>
        </Section>
      )}

      {/* ── Top tags ─────────────────────────────────────────── */}
      <Section icon={Tag} title="Tags dominants">
        {threat.top_tags?.length === 0 ? (
          <p className="text-xs text-gray-400">Aucun tag sur ce cluster</p>
        ) : (
          <div className="flex flex-wrap gap-2">
            {threat.top_tags.map(tag => (
              <span key={tag}
                className="px-2.5 py-1 bg-[#faf8f5] text-[#8b7355] border border-[#ede8e3] rounded-full text-xs font-mono">
                {tag}
              </span>
            ))}
          </div>
        )}
      </Section>

      {/* ── Liste IOCs ────────────────────────────────────────── */}
      <Section icon={List} title={`IOCs du cluster (${Math.min(threat.indicator_count, 50)} affichés)`}>
        <div className="overflow-x-auto">
          <table className="w-full text-sm min-w-[600px]">
            <thead>
              <tr className="border-b border-[#f5f0eb]">
                {['Valeur', 'Type', 'Confidence', 'Statut', 'Source', 'Dernier vu'].map(h => (
                  <th key={h} className="text-left px-3 py-2.5 text-xs font-semibold text-[#8b7355] uppercase tracking-wide bg-[#faf8f5]">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {threat.indicators.map(ind => {
                const s = Math.round(ind.confidence ?? 0)
                const { bar: iBar } = confidenceStyle(s)
                return (
                  <tr key={ind.id} className="border-b border-[#faf8f5] hover:bg-[#faf8f5] transition-colors">
                    <td className="px-3 py-2.5 max-w-[200px]">
                      <button
                        onClick={() => onOpenDetail && onOpenDetail(ind.value)}
                        className="font-mono text-xs text-[#8b7355] hover:text-[#6b5740] hover:underline truncate block w-full text-left transition-colors"
                        title={ind.value}
                      >
                        {ind.value}
                      </button>
                    </td>
                    <td className="px-3 py-2.5">
                      <span className="px-2 py-0.5 bg-[#faf8f5] text-[#8b7355] border border-[#ede8e3] rounded-full text-xs">
                        {ind.type}
                      </span>
                    </td>
                    <td className="px-3 py-2.5">
                      <div className="flex items-center gap-2">
                        <div className="w-12 bg-[#f5f0eb] rounded-full h-1.5">
                          <div className={`${iBar} h-1.5 rounded-full`} style={{ width: `${s}%` }} />
                        </div>
                        <span className="text-xs text-gray-500 tabular-nums">{s}</span>
                      </div>
                    </td>
                    <td className="px-3 py-2.5"><StatusBadge status={ind.status} /></td>
                    <td className="px-3 py-2.5 text-xs text-gray-400 truncate max-w-[120px]">{ind.source ?? '—'}</td>
                    <td className="px-3 py-2.5 text-xs text-gray-400 tabular-nums">
                      {ind.last_seen ? new Date(ind.last_seen).toLocaleDateString('fr-FR') : '—'}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </Section>
    </div>
  )
}