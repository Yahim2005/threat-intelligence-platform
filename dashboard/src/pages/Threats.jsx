// src/pages/Threats.jsx
import { useEffect, useState } from 'react'
import { api } from '../api/client'
import { Shield, ChevronLeft, ChevronRight } from 'lucide-react'

export default function Threats() {
  const [data, setData]       = useState([])
  const [loading, setLoading] = useState(true)
  const [page, setPage]       = useState(1)

  function load(p) {
    setLoading(true)
    api.threats(p)
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false))
  }

  useEffect(() => { load(1) }, [])

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-bold text-gray-800">Threats</h1>
      {loading ? (
        <div className="flex items-center justify-center h-64 text-gray-400">Chargement…</div>
      ) : (
        <div className="space-y-3">
          {data.map(t => (
            <div key={t.id} className="bg-white rounded-xl border border-gray-100 shadow-sm p-5">
              <div className="flex items-start gap-3">
                <div className="p-2 bg-red-50 rounded-lg mt-0.5">
                  <Shield size={16} className="text-red-500" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-2">
                    <h3 className="font-semibold text-gray-800 text-sm truncate">{t.name}</h3>
                    <span className="text-xs text-gray-400 shrink-0">{t.indicator_count} IOCs</span>
                  </div>
                  {t.description && (
                    <p className="text-xs text-gray-500 mt-1 line-clamp-2">{t.description}</p>
                  )}
                  <div className="flex items-center gap-4 mt-3">
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-gray-400">Confidence moy.</span>
                      <div className="w-20 bg-gray-100 rounded-full h-1.5">
                        <div className="bg-red-400 h-1.5 rounded-full" style={{ width: `${t.avg_confidence}%` }} />
                      </div>
                      <span className="text-xs text-gray-600 font-medium">{Math.round(t.avg_confidence)}</span>
                    </div>
                    {t.top_tags?.length > 0 && (
                      <div className="flex gap-1 flex-wrap">
                        {t.top_tags.slice(0, 3).map(tag => (
                          <span key={tag} className="px-2 py-0.5 bg-gray-100 text-gray-600 rounded text-xs">{tag}</span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
      <div className="flex items-center justify-between">
        <button onClick={() => { const p = page - 1; setPage(p); load(p) }} disabled={page === 1}
          className="flex items-center gap-1 px-3 py-1.5 text-sm text-gray-600 border border-gray-200 rounded-lg disabled:opacity-40 hover:bg-gray-50">
          <ChevronLeft size={14} /> Précédent
        </button>
        <span className="text-sm text-gray-500">Page {page}</span>
        <button onClick={() => { const p = page + 1; setPage(p); load(p) }} disabled={data.length < 20}
          className="flex items-center gap-1 px-3 py-1.5 text-sm text-gray-600 border border-gray-200 rounded-lg disabled:opacity-40 hover:bg-gray-50">
          Suivant <ChevronRight size={14} />
        </button>
      </div>
    </div>
  )
}
