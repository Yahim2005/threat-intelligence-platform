// src/pages/Sources.jsx
import { useEffect, useState } from 'react'
import { api } from '../api/client'
import TLPBadge from '../components/TLPBadge'
import { Database, CheckCircle, XCircle } from 'lucide-react'

export default function Sources() {
  const [sources, setSources] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.sources()
      .then(setSources)
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="flex items-center justify-center h-64 text-gray-400">Chargement…</div>

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-bold text-gray-800">Sources</h1>
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {sources.map(src => (
          <div key={src.id} className="bg-white rounded-xl border border-gray-100 shadow-sm p-5 space-y-3">
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-2">
                <Database size={16} className="text-indigo-400 mt-0.5" />
                <span className="font-semibold text-gray-800 text-sm">{src.name}</span>
              </div>
              {src.is_active
                ? <CheckCircle size={16} className="text-emerald-500" />
                : <XCircle    size={16} className="text-gray-300" />}
            </div>
            {src.url && (
              <a href={src.url} target="_blank" rel="noreferrer"
                className="text-xs text-indigo-500 hover:underline truncate block">{src.url}</a>
            )}
            <div className="flex items-center justify-between">
              <TLPBadge tlp={src.tlp} />
              <span className="text-xs text-gray-500">
                <span className="font-semibold text-gray-700">{src.indicator_count?.toLocaleString()}</span> IOCs
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
