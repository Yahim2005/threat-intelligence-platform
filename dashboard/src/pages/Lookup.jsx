// src/pages/Lookup.jsx
import { useState } from 'react'
import { api } from '../api/client'
import TLPBadge from '../components/TLPBadge'
import StatusBadge from '../components/StatusBadge'
import { Search, ShieldCheck, ShieldAlert, ShieldX, Loader } from 'lucide-react'

function RiskBadge({ confidence }) {
  if (confidence >= 75) return (
    <div className="flex items-center gap-2 px-4 py-2 bg-red-50 border border-red-200 rounded-xl">
      <ShieldAlert size={20} className="text-red-500" />
      <div>
        <p className="text-sm font-semibold text-red-700">Menace confirmée</p>
        <p className="text-xs text-red-500">Confidence {confidence}/100 — IOC actif dans notre base</p>
      </div>
    </div>
  )
  if (confidence >= 40) return (
    <div className="flex items-center gap-2 px-4 py-2 bg-amber-50 border border-amber-200 rounded-xl">
      <ShieldX size={20} className="text-amber-500" />
      <div>
        <p className="text-sm font-semibold text-amber-700">Suspect</p>
        <p className="text-xs text-amber-500">Confidence {confidence}/100 — à surveiller</p>
      </div>
    </div>
  )
  return (
    <div className="flex items-center gap-2 px-4 py-2 bg-emerald-50 border border-emerald-200 rounded-xl">
      <ShieldCheck size={20} className="text-emerald-500" />
      <div>
        <p className="text-sm font-semibold text-emerald-700">Faible risque</p>
        <p className="text-xs text-emerald-500">Confidence {confidence}/100</p>
      </div>
    </div>
  )
}

export default function Lookup({ initialQuery = '' }) {
  const [query,   setQuery]   = useState(initialQuery)
  const [result,  setResult]  = useState(null)
  const [status,  setStatus]  = useState('idle') // idle | loading | found | notfound | error

  async function search(q) {
    const val = (q ?? query).trim()
    if (!val) return
    setStatus('loading')
    setResult(null)
    try {
      const data = await api.indicators({ page: 1, page_size: 1 })
      // On cherche par valeur exacte
      const ind = await api.lookupByValue(val)
      setResult(ind)
      setStatus('found')
    } catch (e) {
      if (e.message?.includes('404')) {
        setStatus('notfound')
      } else {
        setStatus('error')
      }
    }
  }

  function onKey(e) {
    if (e.key === 'Enter') search()
  }

  return (
    <div className="space-y-6 max-w-2xl mx-auto">
      <div>
        <h1 className="text-xl font-bold text-gray-800">IOC Lookup</h1>
        <p className="text-sm text-gray-400 mt-1">
          Vérifie si une IP, un domaine, un email ou un hash est référencé dans notre base de menaces.
        </p>
      </div>

      {/* Barre de recherche */}
      <div className="flex gap-2">
        <div className="relative flex-1">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            value={query}
            onChange={e => setQuery(e.target.value)}
            onKeyDown={onKey}
            placeholder="Ex : 185.220.101.47 · evil.com · test@phishing.com · d41d8cd9..."
            className="w-full pl-9 pr-4 py-3 border border-gray-200 rounded-xl text-sm bg-white focus:outline-none focus:ring-2 focus:ring-indigo-300 shadow-sm"
            autoFocus
          />
        </div>
        <button
          onClick={() => search()}
          disabled={status === 'loading' || !query.trim()}
          className="px-5 py-3 bg-indigo-600 text-white text-sm font-medium rounded-xl hover:bg-indigo-700 disabled:opacity-50 transition-colors flex items-center gap-2 shadow-sm"
        >
          {status === 'loading'
            ? <Loader size={15} className="animate-spin" />
            : <Search size={15} />}
          Rechercher
        </button>
      </div>

      {/* Résultats */}
      {status === 'loading' && (
        <div className="flex items-center justify-center py-16 text-gray-400 gap-2">
          <Loader size={18} className="animate-spin" /> Recherche en cours…
        </div>
      )}

      {status === 'notfound' && (
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-8 text-center space-y-2">
          <ShieldCheck size={36} className="text-emerald-400 mx-auto" />
          <p className="font-semibold text-gray-700">Non trouvé dans notre base</p>
          <p className="text-sm text-gray-400">
            <span className="font-mono text-gray-600">{query}</span> n'est pas référencé comme IOC.
          </p>
          <p className="text-xs text-gray-300 mt-2">Cela ne garantit pas l'innocuité — notre base couvre les sources OSINT publiques.</p>
        </div>
      )}

      {status === 'found' && result && (
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
          {/* Header */}
          <div className="px-6 py-5 border-b border-gray-50 space-y-3">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="text-xs text-gray-400 mb-1">Valeur recherchée</p>
                <p className="font-mono text-sm text-gray-800 break-all">{result.value}</p>
              </div>
              <span className="px-2.5 py-1 bg-indigo-50 text-indigo-700 rounded-lg text-xs font-semibold shrink-0">
                {result.type}
              </span>
            </div>
            <RiskBadge confidence={result.confidence} />
          </div>

          {/* Détails */}
          <div className="px-6 py-5 grid grid-cols-2 gap-4 text-sm">
            <div>
              <p className="text-xs text-gray-400 mb-1">Statut</p>
              <StatusBadge status={result.status} />
            </div>
            <div>
              <p className="text-xs text-gray-400 mb-1">TLP</p>
              <TLPBadge tlp={result.tlp} />
            </div>
            <div>
              <p className="text-xs text-gray-400 mb-1">Source</p>
              <p className="text-gray-700 font-medium">{result.source ?? '—'}</p>
            </div>
            <div>
              <p className="text-xs text-gray-400 mb-1">Confidence</p>
              <div className="flex items-center gap-2">
                <div className="w-20 bg-gray-100 rounded-full h-2">
                  <div className="bg-indigo-500 h-2 rounded-full" style={{ width: `${result.confidence}%` }} />
                </div>
                <span className="text-gray-700 font-medium">{result.confidence}/100</span>
              </div>
            </div>
            <div>
              <p className="text-xs text-gray-400 mb-1">Premier vu</p>
              <p className="text-gray-700">{result.first_seen ? new Date(result.first_seen).toLocaleDateString('fr-FR') : '—'}</p>
            </div>
            <div>
              <p className="text-xs text-gray-400 mb-1">Dernier vu</p>
              <p className="text-gray-700">{result.last_seen ? new Date(result.last_seen).toLocaleDateString('fr-FR') : '—'}</p>
            </div>
            {result.tags?.length > 0 && (
              <div className="col-span-2">
                <p className="text-xs text-gray-400 mb-2">Tags</p>
                <div className="flex flex-wrap gap-1.5">
                  {result.tags.map(tag => (
                    <span key={tag} className="px-2 py-0.5 bg-gray-100 text-gray-600 rounded text-xs">{tag}</span>
                  ))}
                </div>
              </div>
            )}
            {result.attack_techniques?.length > 0 && (
              <div className="col-span-2">
                <p className="text-xs text-gray-400 mb-2">Techniques ATT&CK</p>
                <div className="flex flex-wrap gap-1.5">
                  {result.attack_techniques.map(t => (
                    <span key={t} className="px-2 py-0.5 bg-red-50 text-red-600 rounded text-xs font-mono">{t}</span>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {status === 'error' && (
        <div className="text-center py-8 text-red-400 text-sm">
          Erreur lors de la recherche. Vérifie que l'API est accessible.
        </div>
      )}
    </div>
  )
}
