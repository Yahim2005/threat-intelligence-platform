// src/components/SubmitIOC.jsx
import { useState } from 'react'
import { Plus, X, CheckCircle, AlertCircle } from 'lucide-react'

const TLP_OPTIONS = ['CLEAR', 'GREEN', 'AMBER', 'RED']

export default function SubmitIOC({ onSuccess }) {
  const [open,    setOpen]    = useState(false)
  const [loading, setLoading] = useState(false)
  const [result,  setResult]  = useState(null)  // { success, message }
  const [form,    setForm]    = useState({
    value: '', tlp: 'CLEAR', tags: '', source_name: 'Manual Entry'
  })

  function reset() {
    setForm({ value: '', tlp: 'CLEAR', tags: '', source_name: 'Manual Entry' })
    setResult(null)
  }

  async function submit() {
    if (!form.value.trim()) return
    setLoading(true)
    setResult(null)

    const tags = form.tags
      .split(',')
      .map(t => t.trim())
      .filter(Boolean)

    try {
      const res = await fetch('/api/indicators', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': import.meta.env.VITE_API_KEY ?? '',
        },
        body: JSON.stringify({
          value: form.value.trim(),
          tlp: form.tlp,
          tags,
          source_name: form.source_name || 'Manual Entry',
        }),
      })

      if (res.ok) {
        const data = await res.json()
        setResult({ success: true, message: `IOC créé : ${data.value} (${data.type}) — confidence ${data.confidence}` })
        if (onSuccess) onSuccess(data)
        setForm({ value: '', tlp: 'CLEAR', tags: '', source_name: 'Manual Entry' })
      } else {
        const err = await res.json()
        setResult({ success: false, message: err.detail ?? 'Erreur inconnue' })
      }
    } catch (e) {
      setResult({ success: false, message: e.message })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      {/* Bouton d'ouverture */}
      <button
        onClick={() => { setOpen(true); reset() }}
        className="flex items-center gap-1.5 px-4 py-2 bg-[#8b7355] text-white text-sm rounded-xl hover:bg-[#c4a882] transition-colors"
      >
        <Plus size={14} /> Soumettre un IOC
      </button>

      {/* Modal */}
      {open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md mx-4 p-6 space-y-4">
            {/* Header */}
            <div className="flex items-center justify-between">
              <h2 className="text-base font-semibold text-gray-800">Soumettre un IOC manuellement</h2>
              <button onClick={() => setOpen(false)} className="p-1 rounded-lg text-gray-400 hover:text-gray-600">
                <X size={16} />
              </button>
            </div>

            {/* Champs */}
            <div className="space-y-3">
              <div>
                <label className="text-xs text-gray-500 mb-1 block">Valeur *</label>
                <input
                  type="text"
                  value={form.value}
                  onChange={e => setForm(f => ({ ...f, value: e.target.value }))}
                  onKeyDown={e => { if (e.key === 'Enter') submit() }}
                  placeholder="IP, domaine, hash, URL, CVE…"
                  className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 bg-gray-50 focus:outline-none focus:ring-2 focus:ring-indigo-300"
                  autoFocus
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-gray-500 mb-1 block">TLP</label>
                  <select
                    value={form.tlp}
                    onChange={e => setForm(f => ({ ...f, tlp: e.target.value }))}
                    className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 bg-gray-50 focus:outline-none focus:ring-2 focus:ring-indigo-300"
                  >
                    {TLP_OPTIONS.map(t => <option key={t} value={t}>{t}</option>)}
                  </select>
                </div>
                <div>
                  <label className="text-xs text-gray-500 mb-1 block">Source</label>
                  <input
                    type="text"
                    value={form.source_name}
                    onChange={e => setForm(f => ({ ...f, source_name: e.target.value }))}
                    className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 bg-gray-50 focus:outline-none focus:ring-2 focus:ring-indigo-300"
                  />
                </div>
              </div>

              <div>
                <label className="text-xs text-gray-500 mb-1 block">Tags <span className="text-gray-400">(séparés par des virgules)</span></label>
                <input
                  type="text"
                  value={form.tags}
                  onChange={e => setForm(f => ({ ...f, tags: e.target.value }))}
                  placeholder="malware:emotet, kind:phishing"
                  className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 bg-gray-50 focus:outline-none focus:ring-2 focus:ring-indigo-300"
                />
              </div>
            </div>

            {/* Résultat */}
            {result && (
              <div className={`flex items-start gap-2 p-3 rounded-lg text-sm ${
                result.success ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'
              }`}>
                {result.success
                  ? <CheckCircle size={15} className="shrink-0 mt-0.5" />
                  : <AlertCircle size={15} className="shrink-0 mt-0.5" />
                }
                {result.message}
              </div>
            )}

            {/* Actions */}
            <div className="flex justify-end gap-2 pt-1">
              <button
                onClick={() => setOpen(false)}
                className="px-4 py-2 text-sm text-gray-500 border border-gray-200 rounded-lg hover:bg-gray-50"
              >
                Fermer
              </button>
              <button
                onClick={submit}
                disabled={loading || !form.value.trim()}
                className="px-4 py-2 text-sm bg-[#c4a882] text-white rounded-lg hover:bg-[#8b7355] disabled:opacity-60 transition-colors"
              >
                {loading ? 'Envoi…' : 'Soumettre'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}