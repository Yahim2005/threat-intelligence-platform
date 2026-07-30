// src/pages/Sources.jsx
import { useEffect, useState, useRef } from 'react'
import { api } from '../api/client'
import TLPBadge from '../components/TLPBadge'
import TechInfoPanel from '../components/TechInfoPanel'
import { Database, CheckCircle, XCircle, ExternalLink, ArrowUpRight } from 'lucide-react'

// ── Barre de volume relative ──────────────────────────────────────
function VolumeBar({ count, max }) {
  const pct = max > 0 ? Math.round((count / max) * 100) : 0
  return (
    <div className="w-full bg-[#f5f0eb] rounded-full h-1.5 mt-2">
      <div
        className="bg-[#8b7355] h-1.5 rounded-full transition-all duration-700"
        style={{ width: `${pct}%` }}
      />
    </div>
  )
}

// ── Carte Source ──────────────────────────────────────────────────
function SourceCard({ source, max, style }) {
  return (
    <div
      style={style}
      className="bg-white rounded-2xl border border-[#ede8e3] p-5 space-y-3
                 hover:border-[#c4a882] hover:shadow-md hover:-translate-y-0.5
                 transition-all duration-200"
    >
      {/* En-tête */}
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0">
          <div className={`p-2 rounded-xl shrink-0 ${source.is_active ? 'bg-[#faf8f5]' : 'bg-gray-50'}`}>
            <Database size={14} className={source.is_active ? 'text-[#8b7355]' : 'text-gray-300'} />
          </div>
          <span className="font-semibold text-gray-900 text-sm truncate"
                style={{ fontFamily: 'Space Grotesk, sans-serif' }}>
            {source.name}
          </span>
        </div>
        {source.is_active
          ? <CheckCircle size={15} className="text-emerald-500 shrink-0" />
          : <XCircle     size={15} className="text-gray-200 shrink-0" />
        }
      </div>

      {/* URL */}
      {source.url && (
        <a href={source.url} target="_blank" rel="noreferrer"
           className="flex items-center gap-1 text-xs text-[#c4a882] hover:text-[#8b7355] truncate transition-colors">
          <ExternalLink size={10} className="shrink-0" />
          {source.url.replace(/^https?:\/\//, '').split('/')[0]}
        </a>
      )}

      {/* Stats */}
      <div className="flex items-center justify-between">
        <TLPBadge tlp={source.tlp} />
        <div className="text-right">
          <p className="text-lg font-bold text-gray-900 tabular-nums"
             style={{ fontFamily: 'Space Grotesk, sans-serif' }}>
            {source.indicator_count?.toLocaleString() ?? '0'}
          </p>
          <p className="text-xs text-gray-400">IOCs</p>
        </div>
      </div>

      {/* Barre de volume */}
      <VolumeBar count={source.indicator_count ?? 0} max={max} />
    </div>
  )
}

export default function Sources() {
  const [sources, setSources] = useState([])
  const [loading, setLoading] = useState(true)
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    api.sources()
      .then(data => {
        setSources(data)
        // Petit délai pour l'animation d'entrée
        setTimeout(() => setVisible(true), 50)
      })
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  const maxCount = Math.max(...sources.map(s => s.indicator_count ?? 0), 1)
  const total    = sources.reduce((sum, s) => sum + (s.indicator_count ?? 0), 0)
  const active   = sources.filter(s => s.is_active).length

  if (loading) return (
    <div className="flex flex-col items-center justify-center h-64 gap-3">
      <div className="w-6 h-6 border-2 border-[#c4a882] border-t-transparent rounded-full animate-spin" />
      <p className="text-sm text-gray-400">Chargement des sources…</p>
    </div>
  )

  return (
    <div className="space-y-5" style={{ fontFamily: 'Inter, sans-serif' }}>

      {/* ── En-tête ───────────────────────────────────────────── */}
      <div className="flex items-end justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold text-gray-900"
              style={{ fontFamily: 'Space Grotesk, sans-serif' }}>
            Sources
          </h1>
          <p className="text-sm text-gray-400 mt-0.5">
            {active} sources actives · {total.toLocaleString()} IOCs collectés
          </p>
        </div>
      </div>

      <TechInfoPanel>
        <p>
          Liste des sources de collecte intégrées (OSINT généralistes et modules de surveillance
          nationale spécifiques au Cameroun), avec le statut et la date du dernier cycle de
          collecte pour chacune.
        </p>
      </TechInfoPanel>

      {/* ── Stat rapide ───────────────────────────────────────── */}
      <div className="grid grid-cols-3 gap-4">
        {[
          { label: 'Sources totales', value: sources.length },
          { label: 'Sources actives', value: active },
          { label: 'Total IOCs',      value: total.toLocaleString() },
        ].map(({ label, value }) => (
          <div key={label} className="bg-white rounded-2xl border border-[#ede8e3] px-5 py-4">
            <p className="text-xs text-[#8b7355] uppercase tracking-wider font-medium">{label}</p>
            <p className="text-2xl font-bold text-gray-900 mt-1"
               style={{ fontFamily: 'Space Grotesk, sans-serif' }}>
              {value}
            </p>
          </div>
        ))}
      </div>

      {/* ── Grille des sources ────────────────────────────────── */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {sources
          .sort((a, b) => (b.indicator_count ?? 0) - (a.indicator_count ?? 0))
          .map((src, i) => (
            <SourceCard
              key={src.id}
              source={src}
              max={maxCount}
              style={{
                opacity:   visible ? 1 : 0,
                transform: visible ? 'translateY(0)' : 'translateY(12px)',
                transition: `opacity 0.3s ease ${i * 40}ms, transform 0.3s ease ${i * 40}ms`,
              }}
            />
          ))}
      </div>
    </div>
  )
}