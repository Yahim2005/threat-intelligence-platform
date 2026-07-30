// src/pages/IndicatorDetail.jsx
import { useEffect, useState } from 'react'
import { ArrowLeft, Shield, Tag, Link2, BarChart2, MapPin, ExternalLink } from 'lucide-react'
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer
} from 'recharts'
import { api } from '../api/client'
import TLPBadge from '../components/TLPBadge'
import StatusBadge from '../components/StatusBadge'
import TechInfoPanel from '../components/TechInfoPanel'

// ── Badge de risque ───────────────────────────────────────────────
function RiskBadge({ confidence }) {
  if (confidence == null) return null
  if (confidence >= 75) return (
    <span className="px-3 py-1.5 bg-red-50 text-red-700 border border-red-200 rounded-full text-xs font-semibold">
      🔴 Menace confirmée · {confidence}/100
    </span>
  )
  if (confidence >= 40) return (
    <span className="px-3 py-1.5 bg-amber-50 text-amber-700 border border-amber-200 rounded-full text-xs font-semibold">
      🟡 Suspect · {confidence}/100
    </span>
  )
  return (
    <span className="px-3 py-1.5 bg-emerald-50 text-emerald-700 border border-emerald-200 rounded-full text-xs font-semibold">
      🟢 Risque faible · {confidence}/100
    </span>
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
      <span className="text-xs text-gray-400 w-28 shrink-0 pt-0.5 uppercase tracking-wide">{label}</span>
      <span className="text-sm text-gray-700 font-mono break-all">{children}</span>
    </div>
  )
}

// ── Tooltip custom ────────────────────────────────────────────────
function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-white border border-[#ede8e3] rounded-xl px-3 py-2 shadow-xl text-xs">
      <p className="text-[#8b7355] mb-0.5">{label}</p>
      <p className="font-bold text-gray-800">{payload[0].value} sightings</p>
    </div>
  )
}

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

  if (loading) return (
    <div className="flex flex-col items-center justify-center h-64 gap-3">
      <div className="w-6 h-6 border-2 border-[#c4a882] border-t-transparent rounded-full animate-spin" />
      <p className="text-sm text-gray-400">Chargement…</p>
    </div>
  )
  if (error) return <div className="text-red-500 p-6">Erreur : {error}</div>
  if (!ind)  return null

  const fmt = (dt) => dt ? new Date(dt).toLocaleString('fr-FR') : '—'

  return (
    <div className="space-y-5" style={{ fontFamily: 'Inter, sans-serif' }}>

      {/* ── Retour ───────────────────────────────────────────── */}
      <button
        onClick={onBack}
        className="flex items-center gap-1.5 text-sm text-[#8b7355] hover:text-[#6b5740] transition-colors"
      >
        <ArrowLeft size={15} /> Retour aux indicateurs
      </button>

      {/* ── En-tête IOC ──────────────────────────────────────── */}
      <div className="bg-white rounded-2xl border border-[#ede8e3] p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0">
            <p className="text-xs text-[#8b7355] uppercase tracking-widest mb-1">Indicateur</p>
            <p className="font-mono text-base font-semibold text-gray-900 break-all">{ind.value}</p>
          </div>
          <RiskBadge confidence={ind.confidence} />
        </div>
      </div>

      <TechInfoPanel>
        <p>
          Fiche détaillée d'un indicateur, avec le détail du calcul de confidence (contribution
          de chaque composante), ses tags, et les indicateurs liés.
        </p>
        <p>
          Un lien technique existe entre deux IOCs dans deux cas précis : une résolution DNS
          partagée (domaine vers IP), ou un tag malware:* commun. Ces liens sont uniquement
          informatifs sur cette fiche — ils ne regroupent plus les IOCs en clusters de menaces
          (voir la page Threats pour cette logique, différente depuis la refonte du moteur de
          clustering).
        </p>
      </TechInfoPanel>

      {/* ── Grille infos + score ──────────────────────────────── */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-5">

        {/* Métadonnées */}
        <Section icon={Shield} title="Informations">
          <MetaRow label="Type">
            <span className="px-2.5 py-0.5 bg-[#faf8f5] text-[#8b7355] border border-[#ede8e3] rounded-full text-xs font-medium not-italic">
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

        {/* Score breakdown */}
        {ind.score_breakdown ? (
          <Section icon={BarChart2} title="Décomposition du score">
            <div className="space-y-2.5">
              {[
                { key: 'source_reliability',   label: 'Fiabilité source' },
                { key: 'corroboration',         label: 'Corroboration' },
                { key: 'source_diversity',      label: 'Diversité sources' },
                { key: 'type_bonus',            label: 'Type IOC' },
                { key: 'recency',               label: 'Récence' },
                { key: 'malware_tag_bonus',     label: 'Tag malware' },
                { key: 'external_reputation',   label: 'Réputation ext.' },
              ].map(({ key, label }) => {
                const item = ind.score_breakdown[key]
                if (!item) return null
                const pct = Math.round(item.value * 100)
                const color = pct >= 75 ? 'bg-[#8b7355]' : pct >= 50 ? 'bg-[#c4a882]' : 'bg-[#e8d5b7]'
                return (
                  <div key={key} className="flex items-center gap-3">
                    <span className="text-xs text-gray-500 w-32 shrink-0">{label}</span>
                    <div className="flex-1 bg-[#f5f0eb] rounded-full h-1.5">
                      <div className={`${color} h-1.5 rounded-full transition-all duration-500`}
                           style={{ width: `${pct}%` }} />
                    </div>
                    <span className="text-xs text-gray-400 tabular-nums w-7 text-right">{pct}%</span>
                    <span className="text-xs text-[#8b7355] tabular-nums w-10 text-right font-medium">
                      +{item.contribution}
                    </span>
                  </div>
                )
              })}
            </div>
            <p className="text-xs text-gray-400 mt-3 pt-3 border-t border-[#f5f0eb]">
              Contribution = valeur × poids × 100
            </p>
          </Section>
        ) : (
          <Section icon={BarChart2} title="Décomposition du score">
            <p className="text-xs text-gray-400">Score non disponible pour cet indicateur.</p>
          </Section>
        )}
      </div>

      {/* ── Tags + MITRE ─────────────────────────────────────── */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-5">
        <Section icon={Tag} title="Tags">
          {ind.tags?.length > 0 ? (
            <div className="flex flex-wrap gap-2">
              {ind.tags.map(tag => (
                <span key={tag}
                  className="px-2.5 py-1 bg-[#faf8f5] text-[#8b7355] border border-[#ede8e3] rounded-full text-xs font-mono">
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
                <a key={t}
                   href={`https://attack.mitre.org/techniques/${t.replace('.', '/')}`}
                   target="_blank" rel="noreferrer"
                   className="flex items-center gap-1 px-2.5 py-1 bg-purple-50 text-purple-700 border border-purple-100 rounded-full text-xs font-mono hover:bg-purple-100 transition-colors">
                  {t} <ExternalLink size={9} />
                </a>
              ))}
            </div>
          ) : (
            <p className="text-xs text-gray-400">Aucune technique associée</p>
          )}
        </Section>
      </div>

      {/* ── Timeline ─────────────────────────────────────────── */}
      <Section icon={BarChart2} title="Timeline des sightings (30 jours)">
        {timeline.length === 0 ? (
          <p className="text-xs text-gray-400">Aucun sighting enregistré sur cette période.</p>
        ) : (
          <ResponsiveContainer width="100%" height={180}>
            <AreaChart data={timeline} margin={{ top: 0, right: 10, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="sightingGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor="#c4a882" stopOpacity={0.2} />
                  <stop offset="95%" stopColor="#c4a882" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#f5f0eb" vertical={false} />
              <XAxis dataKey="label" tick={{ fontSize: 10, fill: '#9ca3af' }} axisLine={false} tickLine={false} interval="preserveStartEnd" />
              <YAxis tick={{ fontSize: 10, fill: '#9ca3af' }} axisLine={false} tickLine={false} />
              <Tooltip content={<CustomTooltip />} />
              <Area type="monotone" dataKey="sightings" stroke="#8b7355" strokeWidth={2}
                    fill="url(#sightingGrad)" dot={false} activeDot={{ r: 4, fill: '#8b7355', strokeWidth: 0 }} />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </Section>

      {/* ── GeoIP ────────────────────────────────────────────── */}
      {ind.geoip?.country_code && (
        <Section icon={MapPin} title="Géolocalisation">
          <div className="grid grid-cols-2 gap-4">
            <div className="bg-[#faf8f5] rounded-xl p-3">
              <p className="text-xs text-[#8b7355] uppercase tracking-wide mb-1">Pays</p>
              <p className="text-sm font-semibold text-gray-800">
                {ind.geoip.country_name}
                <span className="ml-2 text-xs text-gray-400 font-normal">({ind.geoip.country_code})</span>
              </p>
            </div>
            <div className="bg-[#faf8f5] rounded-xl p-3">
              <p className="text-xs text-[#8b7355] uppercase tracking-wide mb-1">Ville</p>
              <p className="text-sm font-semibold text-gray-800">{ind.geoip.city ?? '—'}</p>
            </div>
            <div className="bg-[#faf8f5] rounded-xl p-3">
              <p className="text-xs text-[#8b7355] uppercase tracking-wide mb-1">ASN</p>
              <p className="text-sm font-mono font-semibold text-gray-800">AS{ind.geoip.asn ?? '—'}</p>
            </div>
            <div className="bg-[#faf8f5] rounded-xl p-3">
              <p className="text-xs text-[#8b7355] uppercase tracking-wide mb-1">Organisation</p>
              <p className="text-sm font-semibold text-gray-800 truncate">{ind.geoip.asn_org ?? '—'}</p>
            </div>
            {ind.geoip.latitude != null && (
              <div className="col-span-2 bg-[#faf8f5] rounded-xl p-3">
                <p className="text-xs text-[#8b7355] uppercase tracking-wide mb-1">Coordonnées</p>
                <a href={`https://www.openstreetmap.org/?mlat=${ind.geoip.latitude}&mlon=${ind.geoip.longitude}&zoom=10`}
                   target="_blank" rel="noreferrer"
                   className="flex items-center gap-1.5 text-sm font-mono text-[#8b7355] hover:text-[#6b5740] transition-colors">
                  {ind.geoip.latitude}, {ind.geoip.longitude}
                  <ExternalLink size={11} />
                </a>
              </div>
            )}
          </div>
        </Section>
      )}

      {/* ── IOCs liés ────────────────────────────────────────── */}
      <Section icon={Link2} title={`IOCs liés (${related.length})`}>
        {related.length === 0 ? (
          <p className="text-xs text-gray-400">Aucun IOC corrélé trouvé.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm min-w-[500px]">
              <thead>
                <tr className="border-b border-[#f5f0eb]">
                  {['Valeur', 'Type', 'Confidence', 'Relation', 'Règle'].map(h => (
                    <th key={h} className="text-left px-3 py-2.5 text-xs font-semibold text-[#8b7355] uppercase tracking-wide bg-[#faf8f5]">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {related.map((r, i) => (
                  <tr key={i} className="border-b border-[#faf8f5] hover:bg-[#faf8f5] transition-colors">
                    <td className="px-3 py-2.5 font-mono text-xs text-[#8b7355] max-w-[180px] truncate" title={r.value}>
                      {r.value}
                    </td>
                    <td className="px-3 py-2.5">
                      <span className="px-2 py-0.5 bg-[#faf8f5] text-[#8b7355] border border-[#ede8e3] rounded-full text-xs">
                        {r.type}
                      </span>
                    </td>
                    <td className="px-3 py-2.5 text-xs text-gray-500 tabular-nums">{r.confidence ?? '—'}</td>
                    <td className="px-3 py-2.5">
                      <span className="px-2 py-0.5 bg-amber-50 text-amber-700 border border-amber-100 rounded-full text-xs">
                        {r.relationship_type}
                      </span>
                    </td>
                    <td className="px-3 py-2.5 font-mono text-xs text-gray-400 max-w-[150px] truncate" title={r.rule}>
                      {r.rule ?? '—'}
                    </td>
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
