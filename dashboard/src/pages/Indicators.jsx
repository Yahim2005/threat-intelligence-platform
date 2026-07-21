// src/pages/Indicators.jsx
import { useEffect, useState } from 'react'
import { api } from '../api/client'
import TLPBadge from '../components/TLPBadge'
import StatusBadge from '../components/StatusBadge'
import { ChevronLeft, ChevronRight, Search, X, SlidersHorizontal } from 'lucide-react'

const TYPES    = ['ip', 'domain', 'url', 'md5', 'sha1', 'sha256', 'cve', 'email', 'cidr', 'phone']
const STATUSES = ['active', 'expired', 'whitelisted']
const TLPS     = ['CLEAR', 'GREEN', 'AMBER', 'RED']

const DEFAULT_FILTERS = {
  type: '', status: 'active', tlp: '', cameroon: false,
  confidence_min: '', source: '', tag: '', search: '',
}

// ── Pill button sélectionnable ────────────────────────────────────
function Pill({ label, active, onClick }) {
  return (
    <button
      onClick={onClick}
      className={`px-3 py-1.5 rounded-full text-xs font-medium transition-all border ${
        active
          ? 'bg-[#8b7355] text-white border-[#8b7355]'
          : 'bg-white text-gray-500 border-[#ede8e3] hover:border-[#c4a882] hover:text-[#8b7355]'
      }`}
    >
      {label}
    </button>
  )
}

// ── Badge confidence ──────────────────────────────────────────────
function ConfidenceBadge({ value }) {
  if (value == null) return <span className="text-gray-300">—</span>
  const color = value >= 75 ? 'text-red-600 bg-red-50' : value >= 50 ? 'text-amber-600 bg-amber-50' : 'text-gray-500 bg-gray-50'
  return (
    <div className="flex items-center gap-2">
      <div className="w-12 bg-[#f5f0eb] rounded-full h-1.5">
        <div
          className={`h-1.5 rounded-full transition-all ${value >= 75 ? 'bg-red-400' : value >= 50 ? 'bg-amber-400' : 'bg-gray-300'}`}
          style={{ width: `${value}%` }}
        />
      </div>
      <span className={`text-xs font-medium px-1.5 py-0.5 rounded ${color}`}>{value}</span>
    </div>
  )
}

export default function Indicators({ onOpenDetail }) {
  const [data,    setData]    = useState(null)
  const [loading, setLoading] = useState(true)
  const [page,    setPage]    = useState(1)
  const [filters, setFilters] = useState(DEFAULT_FILTERS)
  const [draft,   setDraft]   = useState(DEFAULT_FILTERS)
  const [sources, setSources] = useState([])
  const [showAdvanced, setShowAdvanced] = useState(false)

  useEffect(() => {
    api.sources().then(s => setSources(s.map(x => x.name))).catch(() => {})
    load(1, DEFAULT_FILTERS)
  }, [])

  function load(p, f) {
    setLoading(true)
    const params = { page: p, page_size: 20 }
    if (f.type)           params.type           = f.type
    if (f.status)         params.status         = f.status
    if (f.tlp)            params.tlp            = f.tlp
    if (f.confidence_min) params.confidence_min = f.confidence_min
    if (f.source)         params.source         = f.source
    if (f.tag)            params.tag            = f.tag
    if (f.search)         params.search         = f.search
    if (f.cameroon)       params.cameroon       = true
    api.indicators(params)
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false))
  }

  function apply(newDraft) {
    const f = newDraft ?? draft
    setFilters(f)
    setPage(1)
    load(1, f)
  }

  function reset() {
    setDraft(DEFAULT_FILTERS)
    setFilters(DEFAULT_FILTERS)
    setPage(1)
    load(1, DEFAULT_FILTERS)
  }

  function togglePill(key, value) {
    const newDraft = { ...draft, [key]: draft[key] === value ? '' : value }
    setDraft(newDraft)
    apply(newDraft)
  }

  function goTo(p) {
    setPage(p)
    load(p, filters)
  }

  const totalPages = data ? Math.ceil(data.total / 20) : 1
  const hasActiveFilters = Object.entries(filters).some(([k, v]) => v !== '' && v !== DEFAULT_FILTERS[k])

  return (
    <div className="space-y-4" style={{ fontFamily: 'Inter, sans-serif' }}>

      {/* ── En-tête ───────────────────────────────────────────── */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900"
              style={{ fontFamily: 'Space Grotesk, sans-serif' }}>
            Indicators
          </h1>
          <p className="text-sm text-gray-400 mt-0.5">
            {data ? `${data.total.toLocaleString()} résultats` : 'Chargement…'}
          </p>
        </div>
        {hasActiveFilters && (
          <button onClick={reset}
            className="flex items-center gap-1.5 text-xs text-[#8b7355] hover:text-[#6b5740] transition-colors">
            <X size={12} /> Réinitialiser les filtres
          </button>
        )}
      </div>

      {/* ── Panneau de filtres ────────────────────────────────── */}
      <div className="bg-white rounded-2xl border border-[#ede8e3] p-5 space-y-4">

        {/* Barre de recherche principale */}
        <div className="relative">
          <Search size={15} className="absolute left-4 top-1/2 -translate-y-1/2 text-[#c4a882]" />
          <input
            type="text"
            value={draft.search}
            onChange={e => setDraft(d => ({ ...d, search: e.target.value }))}
            onKeyDown={e => { if (e.key === 'Enter') apply() }}
            placeholder="Rechercher un IOC : IP, domaine, hash, URL…"
            className="w-full pl-11 pr-4 py-3 text-sm border border-[#ede8e3] rounded-xl bg-[#faf8f5] focus:outline-none focus:border-[#c4a882] focus:bg-white transition-all placeholder-gray-300"
          />
          {draft.search && (
            <button onClick={() => { setDraft(d => ({ ...d, search: '' })); apply({ ...draft, search: '' }) }}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-300 hover:text-gray-500">
              <X size={14} />
            </button>
          )}
        </div>

        {/* Type — pills */}
        <div>
          <p className="text-xs font-medium text-[#8b7355] uppercase tracking-wider mb-2">Type</p>
          <div className="flex flex-wrap gap-2">
            <Pill label="Tous" active={draft.type === ''} onClick={() => togglePill('type', '')} />
            {TYPES.map(t => (
              <Pill key={t} label={t} active={draft.type === t} onClick={() => togglePill('type', t)} />
            ))}
          </div>
        </div>

        {/* Statut — pills */}
        <div>
          <p className="text-xs font-medium text-[#8b7355] uppercase tracking-wider mb-2">Statut</p>
          <div className="flex flex-wrap gap-2">
            <Pill label="Tous" active={draft.status === ''} onClick={() => togglePill('status', '')} />
            {STATUSES.map(s => (
              <Pill key={s} label={s} active={draft.status === s} onClick={() => togglePill('status', s)} />
            ))}
          </div>
        </div>

        {/* Cameroun */}
        <div>
          <p className="text-xs font-medium text-[#8b7355] uppercase tracking-wider mb-2">Pertinence</p>
          <div className="flex flex-wrap gap-2">
            <Pill
              label="🇨🇲 Cameroun uniquement"
              active={draft.cameroon}
              onClick={() => { const n = { ...draft, cameroon: !draft.cameroon }; setDraft(n); apply(n) }}
            />
          </div>
        </div>
        {/* Filtres avancés (toggle) */}
        <div>
          <button
            onClick={() => setShowAdvanced(v => !v)}
            className="flex items-center gap-1.5 text-xs text-gray-400 hover:text-[#8b7355] transition-colors"
          >
            <SlidersHorizontal size={13} />
            {showAdvanced ? 'Masquer les filtres avancés' : 'Filtres avancés'}
          </button>

          {showAdvanced && (
            <div className="mt-3 grid grid-cols-2 xl:grid-cols-4 gap-3">
              {/* TLP */}
              <div>
                <p className="text-xs text-gray-400 mb-1.5">TLP</p>
                <div className="flex flex-wrap gap-1.5">
                  {TLPS.map(t => (
                    <Pill key={t} label={t} active={draft.tlp === t} onClick={() => togglePill('tlp', t)} />
                  ))}
                </div>
              </div>

              {/* Source */}
              <div>
                <p className="text-xs text-gray-400 mb-1.5">Source</p>
                <select
                  value={draft.source}
                  onChange={e => { const v = { ...draft, source: e.target.value }; setDraft(v); apply(v) }}
                  className="w-full text-xs border border-[#ede8e3] rounded-lg px-3 py-2 bg-[#faf8f5] focus:outline-none focus:border-[#c4a882] text-gray-600"
                >
                  <option value="">Toutes les sources</option>
                  {sources.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>

              {/* Tag */}
              <div>
                <p className="text-xs text-gray-400 mb-1.5">Tag</p>
                <input
                  type="text"
                  value={draft.tag}
                  onChange={e => setDraft(d => ({ ...d, tag: e.target.value }))}
                  onKeyDown={e => { if (e.key === 'Enter') apply() }}
                  placeholder="malware:emotet"
                  className="w-full text-xs border border-[#ede8e3] rounded-lg px-3 py-2 bg-[#faf8f5] focus:outline-none focus:border-[#c4a882] text-gray-600 placeholder-gray-300"
                />
              </div>

              {/* Confidence min */}
              <div>
                <p className="text-xs text-gray-400 mb-1.5">Confidence min</p>
                <input
                  type="number" min="0" max="100"
                  value={draft.confidence_min}
                  onChange={e => setDraft(d => ({ ...d, confidence_min: e.target.value }))}
                  onKeyDown={e => { if (e.key === 'Enter') apply() }}
                  placeholder="0–100"
                  className="w-full text-xs border border-[#ede8e3] rounded-lg px-3 py-2 bg-[#faf8f5] focus:outline-none focus:border-[#c4a882] text-gray-600 placeholder-gray-300"
                />
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ── Tableau ───────────────────────────────────────────── */}
      <div className="bg-white rounded-2xl border border-[#ede8e3] overflow-x-auto" style={{WebkitOverflowScrolling: "touch"}}>
        <table className="w-full text-sm min-w-[700px]">
          <thead>
            <tr className="border-b border-[#f5f0eb]">
              {['Valeur', 'Type', 'Statut', 'Confidence', 'TLP', 'Source', 'Vu le'].map(h => (
                <th key={h} className="text-left px-5 py-4 text-xs font-semibold text-[#8b7355] uppercase tracking-wider bg-[#faf8f5]">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={7} className="text-center py-16">
                <div className="flex flex-col items-center gap-2">
                  <div className="w-6 h-6 border-2 border-[#c4a882] border-t-transparent rounded-full animate-spin" />
                  <span className="text-xs text-gray-400">Chargement…</span>
                </div>
              </td></tr>
            ) : data?.items?.length === 0 ? (
              <tr><td colSpan={7} className="text-center py-16 text-gray-400 text-sm">
                Aucun résultat pour ces filtres
              </td></tr>
            ) : data?.items?.map((ind, idx) => (
              <tr key={ind.id}
                  className="border-b border-[#faf8f5] hover:bg-[#faf8f5] transition-colors group">
                <td className="px-5 py-3.5">
                  <button
                    onClick={() => onOpenDetail && onOpenDetail(ind.value)}
                    className="font-mono text-xs text-[#8b7355] hover:text-[#6b5740] hover:underline text-left truncate max-w-[200px] block transition-colors"
                    title={ind.value}
                  >
                    {ind.value}
                  </button>
                </td>
                <td className="px-5 py-3.5">
                  <span className="px-2.5 py-1 bg-[#faf8f5] text-[#8b7355] rounded-full text-xs font-medium border border-[#ede8e3]">
                    {ind.type}
                  </span>
                </td>
                <td className="px-5 py-3.5"><StatusBadge status={ind.status} /></td>
                <td className="px-5 py-3.5"><ConfidenceBadge value={ind.confidence} /></td>
                <td className="px-5 py-3.5"><TLPBadge tlp={ind.tlp} /></td>
                <td className="px-5 py-3.5 text-xs text-gray-400 max-w-[120px] truncate" title={ind.source}>
                  {ind.source ?? '—'}
                </td>
                <td className="px-5 py-3.5 text-xs text-gray-400 tabular-nums">
                  {ind.last_seen ? new Date(ind.last_seen).toLocaleDateString('fr-FR') : '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* ── Pagination ────────────────────────────────────────── */}
      {data && totalPages > 1 && (
        <div className="flex items-center justify-between">
          <button onClick={() => goTo(page - 1)} disabled={page === 1}
            className="flex items-center gap-1.5 px-4 py-2 text-sm text-[#8b7355] border border-[#ede8e3] rounded-xl bg-white hover:border-[#c4a882] disabled:opacity-30 transition-all">
            <ChevronLeft size={14} /> Précédent
          </button>
          <div className="flex items-center gap-1">
            {Array.from({ length: Math.min(totalPages, 5) }, (_, i) => {
              const p = page <= 3 ? i + 1 : page - 2 + i
              if (p > totalPages) return null
              return (
                <button key={p} onClick={() => goTo(p)}
                  className={`w-8 h-8 rounded-lg text-sm transition-all ${
                    p === page
                      ? 'bg-[#8b7355] text-white'
                      : 'text-gray-400 hover:bg-[#faf8f5]'
                  }`}>
                  {p}
                </button>
              )
            })}
          </div>
          <button onClick={() => goTo(page + 1)} disabled={page === totalPages}
            className="flex items-center gap-1.5 px-4 py-2 text-sm text-[#8b7355] border border-[#ede8e3] rounded-xl bg-white hover:border-[#c4a882] disabled:opacity-30 transition-all">
            Suivant <ChevronRight size={14} />
          </button>
        </div>
      )}
    </div>
  )
}