// src/pages/Threats.jsx
import { useEffect, useState } from 'react'
import { api } from '../api/client'
import { Shield, ChevronLeft, ChevronRight, ArrowUpRight, Tag } from 'lucide-react'

// ── Couleur selon confidence ──────────────────────────────────────
function confidenceColor(score) {
  if (score >= 60)  return { bar: 'bg-red-500',          text: 'text-red-600',        bg: 'bg-red-50' }
  if (score >= 50)  return { bar: 'bg-orange-500',       text: 'text-orange-600',     bg: 'bg-orange-50' }
  if (score >= 40)  return { bar: 'bg-yellow-400',       text: 'text-orange-500',     bg: 'bg-orange-50' }
  return                   { bar: 'bg-green-300',       text: 'text-yellow-600',     bg: 'bg-yellow-50' }
}

// ── Carte Threat ──────────────────────────────────────────────────
function ThreatCard({ threat, onClick }) {
  const score = Math.round(threat.avg_confidence ?? 0)
  const { bar, text, bg } = confidenceColor(score)

  return (
    <div
      onClick={onClick}
      className="bg-white rounded-2xl border border-[#ede8e3] p-5 cursor-pointer
                 hover:border-[#c4a882] hover:shadow-md hover:-translate-y-0.5
                 transition-all duration-200 group"
    >
      <div className="flex items-start gap-4">

        {/* Icône */}
        <div className={`p-2.5 rounded-xl shrink-0 ${bg}`}>
          <Shield size={16} className={text} />
        </div>

        {/* Contenu */}
        <div className="flex-1 min-w-0">

          {/* Titre + compteur */}
          <div className="flex items-start justify-between gap-2 mb-2">
            <h3 className="font-semibold text-gray-900 text-sm leading-snug truncate"
                style={{ fontFamily: 'Space Grotesk, sans-serif' }}>
              {threat.name}
            </h3>
            <div className="flex items-center gap-2 shrink-0">
              <span className="text-xs text-gray-400 tabular-nums">
                {threat.indicator_count.toLocaleString()} IOCs
              </span>
              <ArrowUpRight size={14} className="text-gray-300 group-hover:text-[#c4a882] transition-colors" />
            </div>
          </div>

          {/* Confidence */}
          <div className="flex items-center gap-3 mb-3">
            <div className="flex-1 bg-[#f5f0eb] rounded-full h-1.5">
              <div
                className={`${bar} h-1.5 rounded-full transition-all duration-500`}
                style={{ width: `${score}%` }}
              />
            </div>
            <span className={`text-xs font-semibold tabular-nums ${text}`}>
              {score}
            </span>
          </div>

          {/* Tags */}
          {threat.top_tags?.length > 0 && (
            <div className="flex items-center gap-1.5 flex-wrap">
              <Tag size={11} className="text-[#c4a882] shrink-0" />
              {threat.top_tags.slice(0, 4).map(tag => (
                <span key={tag}
                  className="px-2 py-0.5 bg-[#faf8f5] text-[#8b7355] border border-[#ede8e3] rounded-full text-xs font-mono">
                  {tag}
                </span>
              ))}
              {threat.top_tags.length > 4 && (
                <span className="text-xs text-gray-400">+{threat.top_tags.length - 4}</span>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default function Threats({ onOpenThreat }) {
  const [data,    setData]    = useState([])
  const [loading, setLoading] = useState(true)
  const [page,    setPage]    = useState(1)
  const [minScore, setMinScore] = useState(0)

  function load(p) {
    setLoading(true)
    api.threats(p)
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false))
  }

  useEffect(() => { load(1) }, [])

  return (
    <div className="space-y-5" style={{ fontFamily: 'Inter, sans-serif' }}>

      {/* ── En-tête ───────────────────────────────────────────── */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900"
            style={{ fontFamily: 'Space Grotesk, sans-serif' }}>
          Threats
        </h1>
        <p className="text-sm text-gray-400 mt-0.5">
          Clusters de menaces corrélés automatiquement
        </p>
      </div>

      {/* ── Filtre par score ─────────────────────────────────── */}
<div className="bg-white rounded-2xl border border-[#ede8e3] px-5 py-4 flex items-center gap-4 flex-wrap">
  <span className="text-xs font-medium text-[#8b7355] uppercase tracking-wider shrink-0">
    Score minimum
  </span>
  <div className="flex items-center gap-2 flex-wrap">
    {[
      { label: 'Tous',   value: 0  },
      { label: '40+',    value: 40 },
      { label: '50+',    value: 50 },
      { label: '60+',    value: 60 },
    ].map(({ label, value }) => (
      <button
        key={value}
        onClick={() => setMinScore(value)}
        className={`px-3 py-1.5 rounded-full text-xs font-medium transition-all border ${
          minScore === value
            ? 'bg-[#8b7355] text-white border-[#8b7355]'
            : 'bg-white text-gray-500 border-[#ede8e3] hover:border-[#c4a882] hover:text-[#8b7355]'
        }`}
      >
        {label}
      </button>
    ))}
  </div>
  <span className="text-xs text-gray-400 ml-auto">
    {data.filter(t => Math.round(t.avg_confidence ?? 0) >= minScore).length} clusters affichés
  </span>
</div>

      {/* ── Contenu ───────────────────────────────────────────── */}
      {loading ? (
        <div className="flex flex-col items-center justify-center h-64 gap-3">
          <div className="w-6 h-6 border-2 border-[#c4a882] border-t-transparent rounded-full animate-spin" />
          <p className="text-sm text-gray-400">Chargement des threats…</p>
        </div>
      ) : data.length === 0 ? (
        <div className="flex flex-col items-center justify-center h-64 gap-2">
          <Shield size={32} className="text-[#ede8e3]" />
          <p className="text-sm text-gray-400">Aucun cluster de menaces détecté</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
          {data.filter(t => Math.round(t.avg_confidence ?? 0) >= minScore).map(t => (
            <ThreatCard
              key={t.id}
              threat={t}
              onClick={() => onOpenThreat && onOpenThreat(t.id)}
            />
          ))}
        </div>
      )}

      {/* ── Pagination ────────────────────────────────────────── */}
      <div className="flex items-center justify-between pt-2">
        <button
          onClick={() => { const p = page - 1; setPage(p); load(p) }}
          disabled={page === 1}
          className="flex items-center gap-1.5 px-4 py-2 text-sm text-[#8b7355] border border-[#ede8e3] rounded-xl bg-white hover:border-[#c4a882] disabled:opacity-30 transition-all"
        >
          <ChevronLeft size={14} /> Précédent
        </button>
        <span className="text-sm text-[#8b7355] font-medium">Page {page}</span>
        <button
          onClick={() => { const p = page + 1; setPage(p); load(p) }}
          disabled={data.length < 20}
          className="flex items-center gap-1.5 px-4 py-2 text-sm text-[#8b7355] border border-[#ede8e3] rounded-xl bg-white hover:border-[#c4a882] disabled:opacity-30 transition-all"
        >
          Suivant <ChevronRight size={14} />
        </button>
      </div>
    </div>
  )
}