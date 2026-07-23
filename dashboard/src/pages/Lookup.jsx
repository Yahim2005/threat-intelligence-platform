// src/pages/Lookup.jsx
import { useEffect, useState } from 'react'
import { api } from '../api/client'
import TLPBadge from '../components/TLPBadge'
import StatusBadge from '../components/StatusBadge'
import { Search, ShieldCheck, ShieldAlert, ShieldX, Loader, AlertTriangle } from 'lucide-react'

function RiskBadge({ confidence }) {
  if (confidence >= 75) return (
    <div className="flex items-center gap-2 px-4 py-2 bg-red-50 border border-red-200 rounded-xl">
      <ShieldAlert size={20} className="text-red-500" />
      <div>
        <p className="text-sm font-semibold text-red-700">Menace confirmée</p>
        <p className="text-xs text-red-500">Confidence {confidence}/100, IOC actif dans notre base</p>
      </div>
    </div>
  )
  if (confidence >= 40) return (
    <div className="flex items-center gap-2 px-4 py-2 bg-amber-50 border border-amber-200 rounded-xl">
      <ShieldX size={20} className="text-amber-500" />
      <div>
        <p className="text-sm font-semibold text-amber-700">Suspect</p>
        <p className="text-xs text-amber-500">Confidence {confidence}/100, à surveiller</p>
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

// ── Défilement d'exemples réels (chargés depuis l'API) ──────────────
function ExamplesTicker({ onPick }) {
  const [examples, setExamples] = useState([])

  useEffect(() => {
    api.indicators({ page_size: 12, status: 'active' })
      .then(d => setExamples(d.items.map(i => i.value)))
      .catch(() => {})
  }, [])

  if (examples.length === 0) return null

  const doubled = [...examples, ...examples]

  return (
    <div className="overflow-hidden">
      <p className="text-xs text-gray-400 mb-2">Exemples issus de notre base, cliquez pour essayer :</p>
      <div className="relative overflow-hidden">
        <div className="flex gap-2 animate-lookup-scroll w-max">
          {doubled.map((v, i) => (
            <button
              key={i}
              onClick={() => onPick(v)}
              className="shrink-0 px-3 py-1.5 text-xs font-mono bg-white border border-[#ede8e3] text-[#8b7355] rounded-full hover:border-[#c4a882] hover:bg-[#faf8f5] transition-colors"
            >
              {v.length > 28 ? v.slice(0, 28) + '…' : v}
            </button>
          ))}
        </div>
      </div>
      <style>{`
        @keyframes lookup-scroll {
          0% { transform: translateX(0); }
          100% { transform: translateX(-50%); }
        }
        .animate-lookup-scroll {
          animation: lookup-scroll 30s linear infinite;
        }
        .animate-lookup-scroll:hover {
          animation-play-state: paused;
        }
      `}</style>
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

  function pickExample(value) {
    setQuery(value)
    search(value)
  }

  return (
    <div className="space-y-6 max-w-2xl mx-auto">
      <div>
        <h1 className="text-xl font-bold text-gray-800">IOC Lookup</h1>
        <p className="text-sm text-gray-400 mt-1">
          Vérifie si une IP, un domaine, un email, un numéro de téléphone ou un hash est référencé dans notre base de menaces.
        </p>
      </div>

      {/* Avertissement liens non sûrs */}
      <div className="flex items-start gap-2.5 px-4 py-3 bg-amber-50 border border-amber-200 rounded-xl">
        <AlertTriangle size={16} className="text-amber-500 shrink-0 mt-0.5" />
        <p className="text-xs text-amber-700 leading-relaxed">
          Ne cliquez jamais sur un lien dont vous n'êtes pas sûr à 100 %. Vérifiez-le d'abord ici.
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
            placeholder="Ex : 185.220.101.47, evil.com, 656708967, d41d8cd9…"
            className="w-full pl-9 pr-4 py-3 border border-gray-200 rounded-xl text-sm bg-white focus:outline-none focus:ring-2 focus:ring-[#c4a882]/40 shadow-sm"
            autoFocus
          />
        </div>
        <button
          onClick={() => search()}
          disabled={status === 'loading' || !query.trim()}
          className="px-5 py-3 bg-[#8b7355] text-white text-sm font-medium rounded-xl hover:bg-[#6b5740] disabled:opacity-50 transition-colors flex items-center gap-2 shadow-sm"
        >
          {status === 'loading'
            ? <Loader size={15} className="animate-spin" />
            : <Search size={15} />}
          Rechercher
        </button>
      </div>

      <ExamplesTicker onPick={pickExample} />

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
          <p className="text-xs text-gray-300 mt-2">
            Cela ne garantit pas l'innocuité, notre base couvre les sources OSINT publiques.
          </p>
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
              <span className="px-2.5 py-1 bg-[#faf8f5] text-[#8b7355] border border-[#ede8e3] rounded-lg text-xs font-semibold shrink-0">
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
              <p className="text-gray-700 font-medium">{result.source ?? 'non renseigné'}</p>
            </div>
            <div>
              <p className="text-xs text-gray-400 mb-1">Confidence</p>
              <div className="flex items-center gap-2">
                <div className="w-20 bg-gray-100 rounded-full h-2">
                  <div className="bg-[#8b7355] h-2 rounded-full" style={{ width: `${result.confidence}%` }} />
                </div>
                <span className="text-gray-700 font-medium">{result.confidence}/100</span>
              </div>
            </div>
            <div>
              <p className="text-xs text-gray-400 mb-1">Premier vu</p>
              <p className="text-gray-700">{result.first_seen ? new Date(result.first_seen).toLocaleDateString('fr-FR') : 'non renseigné'}</p>
            </div>
            <div>
              <p className="text-xs text-gray-400 mb-1">Dernier vu</p>
              <p className="text-gray-700">{result.last_seen ? new Date(result.last_seen).toLocaleDateString('fr-FR') : 'non renseigné'}</p>
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
