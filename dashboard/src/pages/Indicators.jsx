// src/pages/Indicators.jsx
import { useEffect, useState } from 'react'
import { api } from '../api/client'
import TLPBadge from '../components/TLPBadge'
import StatusBadge from '../components/StatusBadge'
import { ChevronLeft, ChevronRight, Search, X } from 'lucide-react'

const TYPES    = ['', 'ip', 'domain', 'url', 'md5', 'sha1', 'sha256', 'cve', 'email', 'cidr']
const STATUSES = ['', 'active', 'expired', 'whitelisted']
const TLPS     = ['', 'CLEAR', 'GREEN', 'AMBER', 'RED']

const DEFAULT_FILTERS = {
  type: '', status: 'active', tlp: '',
  confidence_min: '', source: '', search: '',
}

export default function Indicators({ onOpenDetail }) {
  const [data,    setData]    = useState(null)
  const [loading, setLoading] = useState(true)
  const [page,    setPage]    = useState(1)
  const [filters, setFilters] = useState(DEFAULT_FILTERS)
  const [draft,   setDraft]   = useState(DEFAULT_FILTERS)
  const [sources, setSources] = useState([])

  // Charge la liste des sources pour le filtre
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
    if (f.search)         params.search         = f.search
    api.indicators(params)
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false))
  }

  function apply() {
    setFilters(draft)
    setPage(1)
    load(1, draft)
  }

  function reset() {
    setDraft(DEFAULT_FILTERS)
    setFilters(DEFAULT_FILTERS)
    setPage(1)
    load(1, DEFAULT_FILTERS)
  }

  function goTo(p) {
    setPage(p)
    load(p, filters)
  }

  const totalPages = data ? Math.ceil(data.total / 20) : 1
  const hasActiveFilters = Object.entries(filters).some(([k, v]) => v !== '' && v !== DEFAULT_FILTERS[k])

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-800">Indicators</h1>
        {data && <span className="text-sm text-gray-400">{data.total.toLocaleString()} résultats</span>}
      </div>

      {/* Filtres */}
      <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-4 space-y-3">
        <div className="flex flex-wrap gap-3">
          {/* Type */}
          <div className="flex flex-col gap-1">
            <label className="text-xs text-gray-500">Type</label>
            <select value={draft.type} onChange={e => setDraft(d => ({ ...d, type: e.target.value }))}
              className="text-sm border border-gray-200 rounded-lg px-3 py-1.5 bg-gray-50 focus:outline-none focus:ring-2 focus:ring-indigo-300">
              {TYPES.map(t => <option key={t} value={t}>{t || 'Tous'}</option>)}
            </select>
          </div>

          {/* Statut */}
          <div className="flex flex-col gap-1">
            <label className="text-xs text-gray-500">Statut</label>
            <select value={draft.status} onChange={e => setDraft(d => ({ ...d, status: e.target.value }))}
              className="text-sm border border-gray-200 rounded-lg px-3 py-1.5 bg-gray-50 focus:outline-none focus:ring-2 focus:ring-indigo-300">
              {STATUSES.map(s => <option key={s} value={s}>{s || 'Tous'}</option>)}
            </select>
          </div>

          {/* TLP */}
          <div className="flex flex-col gap-1">
            <label className="text-xs text-gray-500">TLP</label>
            <select value={draft.tlp} onChange={e => setDraft(d => ({ ...d, tlp: e.target.value }))}
              className="text-sm border border-gray-200 rounded-lg px-3 py-1.5 bg-gray-50 focus:outline-none focus:ring-2 focus:ring-indigo-300">
              {TLPS.map(t => <option key={t} value={t}>{t || 'Tous'}</option>)}
            </select>
          </div>

          {/* Source */}
          <div className="flex flex-col gap-1">
            <label className="text-xs text-gray-500">Source</label>
            <select value={draft.source} onChange={e => setDraft(d => ({ ...d, source: e.target.value }))}
              className="text-sm border border-gray-200 rounded-lg px-3 py-1.5 bg-gray-50 focus:outline-none focus:ring-2 focus:ring-indigo-300">
              <option value="">Toutes</option>
              {sources.map(s => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>

          {/* Confidence min */}
          <div className="flex flex-col gap-1">
            <label className="text-xs text-gray-500">Confidence min</label>
            <input type="number" min="0" max="100"
              value={draft.confidence_min}
              onChange={e => setDraft(d => ({ ...d, confidence_min: e.target.value }))}
              placeholder="0–100"
              className="text-sm border border-gray-200 rounded-lg px-3 py-1.5 w-24 bg-gray-50 focus:outline-none focus:ring-2 focus:ring-indigo-300" />
          </div>
        </div>

        {/* Actions */}
        {/* Recherche textuelle */}
        <div className="flex flex-col gap-1 flex-1 min-w-[200px]">
          <label className="text-xs text-gray-500">Recherche</label>
          <input
            type="text"
            value={draft.search}
            onChange={e => setDraft(d => ({ ...d, search: e.target.value }))}
            onKeyDown={e => { if (e.key === 'Enter') apply() }}
            placeholder="cbmelipilla, emotet, 192.168…"
            className="text-sm border border-gray-200 rounded-lg px-3 py-1.5 bg-gray-50 focus:outline-none focus:ring-2 focus:ring-indigo-300"
          />
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2 pt-1">
          <button onClick={apply}
            className="flex items-center gap-1.5 px-4 py-1.5 bg-indigo-600 text-white text-sm rounded-lg hover:bg-indigo-700 transition-colors">
            <Search size={13} /> Appliquer
          </button>
          {hasActiveFilters && (
            <button onClick={reset}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-gray-500 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors">
              <X size={13} /> Réinitialiser
            </button>
          )}
        </div>
      </div>

      {/* Tableau */}
      <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-x-auto">
        <table className="w-full text-sm min-w-[700px]">
          <thead className="bg-gray-50 border-b border-gray-100">
            <tr>
              {['Valeur', 'Type', 'Statut', 'Confidence', 'TLP', 'Source', 'Vu le'].map(h => (
                <th key={h} className="text-left px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {loading ? (
              <tr><td colSpan={7} className="text-center py-12 text-gray-400">Chargement…</td></tr>
            ) : data?.items?.length === 0 ? (
              <tr><td colSpan={7} className="text-center py-12 text-gray-400">Aucun résultat</td></tr>
            ) : data?.items?.map(ind => (
              <tr key={ind.id} className="hover:bg-gray-50 transition-colors">
                <td className="px-4 py-3 font-mono text-xs max-w-[200px] truncate">
                  <button
                    onClick={() => onOpenDetail(ind.value)}
                    className="text-indigo-600 hover:text-indigo-800 hover:underline text-left truncate w-full"
                    title={ind.value}
                  >
                    {ind.value}
                  </button>
                </td>
                <td className="px-4 py-3">
                  <span className="px-2 py-0.5 bg-indigo-50 text-indigo-700 rounded text-xs font-medium">{ind.type}</span>
                </td>
                <td className="px-4 py-3"><StatusBadge status={ind.status} /></td>
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    <div className="w-14 bg-gray-100 rounded-full h-1.5">
                      <div className="bg-indigo-500 h-1.5 rounded-full" style={{ width: `${ind.confidence}%` }} />
                    </div>
                    <span className="text-xs text-gray-500 tabular-nums">{ind.confidence}</span>
                  </div>
                </td>
                <td className="px-4 py-3"><TLPBadge tlp={ind.tlp} /></td>
                <td className="px-4 py-3 text-xs text-gray-500 max-w-[120px] truncate" title={ind.source}>{ind.source ?? '—'}</td>
                <td className="px-4 py-3 text-xs text-gray-400 tabular-nums">
                  {ind.last_seen ? new Date(ind.last_seen).toLocaleDateString('fr-FR') : '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {data && totalPages > 1 && (
        <div className="flex items-center justify-between">
          <button onClick={() => goTo(page - 1)} disabled={page === 1}
            className="flex items-center gap-1 px-3 py-1.5 text-sm text-gray-600 border border-gray-200 rounded-lg disabled:opacity-40 hover:bg-gray-50">
            <ChevronLeft size={14} /> Précédent
          </button>
          <span className="text-sm text-gray-500">Page {page} / {totalPages}</span>
          <button onClick={() => goTo(page + 1)} disabled={page === totalPages}
            className="flex items-center gap-1 px-3 py-1.5 text-sm text-gray-600 border border-gray-200 rounded-lg disabled:opacity-40 hover:bg-gray-50">
            Suivant <ChevronRight size={14} />
          </button>
        </div>
      )}
    </div>
  )
}
