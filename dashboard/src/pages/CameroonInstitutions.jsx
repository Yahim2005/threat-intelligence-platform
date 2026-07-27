// src/pages/CameroonInstitutions.jsx
import { useEffect, useState, useMemo } from 'react'
import { ArrowLeft, CheckCircle2, HelpCircle, XCircle, Info } from 'lucide-react'
import { api } from '../api/client'
import DetailModal from '../components/DetailModal'
import { CATEGORY_LABELS, InstitutionRow } from '../components/cameroon/Shared'

const PAGE_SIZE = 20
const STORAGE_KEY = 'cameroon_exposed_institution_filter'

export default function CameroonInstitutions({ onBack, onNavigate }) {
  const [institutions, setInstitutions] = useState([])
  const [loading, setLoading] = useState(true)
  const [categoryFilter, setCategoryFilter] = useState('')
  const [page, setPage] = useState(1)
  const [detailItem, setDetailItem] = useState(null)

  useEffect(() => {
    api.monitoredAssets().then(setInstitutions).catch(console.error).finally(() => setLoading(false))
  }, [])

  const filtered = useMemo(() => {
    if (!categoryFilter) return institutions
    return institutions.filter(i => i.category === categoryFilter)
  }, [institutions, categoryFilter])

  const totalPages = Math.max(Math.ceil(filtered.length / PAGE_SIZE), 1)
  const pageItems = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE)

  if (loading) return (
    <div className="flex flex-col items-center justify-center h-64 gap-3">
      <div className="w-6 h-6 border-2 border-[#c4a882] border-t-transparent rounded-full animate-spin" />
      <p className="text-sm text-gray-400">Chargement…</p>
    </div>
  )

  return (
    <div className="space-y-5" style={{ fontFamily: 'Inter, sans-serif' }}>
      <button onClick={onBack} className="flex items-center gap-1.5 text-sm text-[#8b7355] hover:text-[#6b5740] transition-colors">
        <ArrowLeft size={15} /> Retour à Surveillance nationale
      </button>

      <div>
        <h1 className="text-2xl font-bold text-gray-900" style={{ fontFamily: 'Space Grotesk, sans-serif' }}>
          Institutions surveillées
        </h1>
        <p className="text-sm text-gray-400 mt-0.5">{filtered.length} institutions</p>
      </div>

      <div className="flex gap-2 flex-wrap">
        {[{ v: '', l: 'Toutes' }, ...Object.entries(CATEGORY_LABELS).map(([v, l]) => ({ v, l }))].map(({ v, l }) => (
          <button
            key={v}
            onClick={() => { setCategoryFilter(v); setPage(1) }}
            className={`px-3 py-1.5 rounded-full text-xs font-medium border transition-all ${
              categoryFilter === v
                ? 'bg-[#8b7355] text-white border-[#8b7355]'
                : 'bg-white text-gray-500 border-[#ede8e3] hover:border-[#c4a882]'
            }`}
          >
            {l}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-2.5">
        {pageItems.map(a => (
          <InstitutionRow key={a.id} asset={a} onClick={() => setDetailItem(a)} />
        ))}
      </div>

      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}
            className="px-4 py-2 text-sm text-[#8b7355] border border-[#ede8e3] rounded-xl bg-white hover:border-[#c4a882] disabled:opacity-30 transition-all">
            Précédent
          </button>
          <span className="text-sm text-gray-400">Page {page} / {totalPages}</span>
          <button onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page === totalPages}
            className="px-4 py-2 text-sm text-[#8b7355] border border-[#ede8e3] rounded-xl bg-white hover:border-[#c4a882] disabled:opacity-30 transition-all">
            Suivant
          </button>
        </div>
      )}

      {detailItem && (
        <DetailModal
          title={detailItem.name}
          subtitle={detailItem.acronym ? `${detailItem.acronym} · ${CATEGORY_LABELS[detailItem.category]}` : CATEGORY_LABELS[detailItem.category]}
          onClose={() => setDetailItem(null)}
        >
          {detailItem.domain_status === 'not_found' ? (
            <div className="flex items-center gap-2 mb-3 text-sm">
              <XCircle size={14} className="text-red-400" />
              <span className="text-red-500">
                {detailItem.domain ? `${detailItem.domain} (non retenu)` : 'Aucun domaine officiel identifié'}
              </span>
            </div>
          ) : detailItem.domain && (
            <div className="flex items-center gap-2 mb-3 text-sm">
              {detailItem.domain_status === 'confirmed'
                ? <CheckCircle2 size={14} className="text-emerald-500" />
                : <HelpCircle size={14} className="text-amber-400" />}
              <span className="font-mono text-gray-700">{detailItem.domain}</span>
              <span className="text-xs text-gray-400">
                {detailItem.domain_status === 'confirmed' ? '(vérifié)' : '(à confirmer)'}
              </span>
            </div>
          )}
          {detailItem.verification_note && (
            <div className="flex items-start gap-2 mb-5 px-3 py-2.5 bg-[#faf8f5] rounded-xl">
              <Info size={13} className="text-[#8b7355] shrink-0 mt-0.5" />
              <p className="text-xs text-gray-600 leading-relaxed">{detailItem.verification_note}</p>
            </div>
          )}
          {detailItem.asn && (
            <p className="text-sm text-gray-500 mb-5">ASN : <span className="font-mono">AS{detailItem.asn}</span></p>
          )}
          <button
            onClick={() => {
              sessionStorage.setItem(STORAGE_KEY, JSON.stringify({ id: detailItem.id, name: detailItem.name }))
              setDetailItem(null)
              onNavigate('cameroon-exposed')
            }}
            className="w-full flex items-center justify-center gap-1.5 px-4 py-2.5 bg-[#8b7355] text-white text-sm font-medium rounded-xl hover:bg-[#6b5740] transition-colors"
          >
            Voir les IPs exposées de cette institution
          </button>
        </DetailModal>
      )}
    </div>
  )
}
