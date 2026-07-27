// src/pages/CameroonTyposquat.jsx
import { useEffect, useState } from 'react'
import { ArrowLeft, ExternalLink, Flag } from 'lucide-react'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'
import DetailModal from '../components/DetailModal'
import { SeverityBadge, TyposquatRow, TyposquatMetadata } from '../components/cameroon/Shared'

const PAGE_SIZE = 20

export default function CameroonTyposquat({ onBack, onOpenDetail }) {
  const { isAdmin } = useAuth()
  const [filter, setFilter] = useState('confirmed')
  const [items, setItems] = useState([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [institutions, setInstitutions] = useState([])
  const [detailItem, setDetailItem] = useState(null)
  const [fpMessage, setFpMessage] = useState(null)

  useEffect(() => {
    api.monitoredAssets().then(setInstitutions).catch(console.error)
  }, [])

  useEffect(() => {
    setLoading(true)
    const tag = filter === 'confirmed' ? 'typosquat:confirmed' : 'typosquat:potential'
    api.indicators({ tag, page, page_size: PAGE_SIZE }).then(d => {
      const extractTarget = i => i.tags?.find(t => t.startsWith('typosquat:') && t !== 'typosquat:confirmed' && t !== 'typosquat:potential')?.replace('typosquat:', '')
      setItems(d.items.map(i => ({ id: i.id, value: i.value, target_name: extractTarget(i), confirmed: filter === 'confirmed', metadata: i.metadata })))
      setTotal(d.total)
    }).catch(console.error).finally(() => setLoading(false))
  }, [filter, page])

  async function reportFalsePositive(item) {
    if (!isAdmin) return
    const matchedInst = institutions.find(i =>
      (i.acronym || i.name).toLowerCase().replace(/\s+/g, '_') === item.target_name
    )
    try {
      const res = await api.reportFalsePositive({ indicator_id: item.id, monitored_asset_id: matchedInst?.id })
      setFpMessage(`${res.value} marqué faux positif${res.alias_added ? ', alias ajouté' : ''}`)
      setItems(prev => prev.filter(t => t.id !== item.id))
      setDetailItem(null)
      setTimeout(() => setFpMessage(null), 4000)
    } catch (e) {
      setFpMessage(`Erreur : ${e.message}`)
    }
  }

  const totalPages = Math.max(Math.ceil(total / PAGE_SIZE), 1)

  return (
    <div className="space-y-5" style={{ fontFamily: 'Inter, sans-serif' }}>
      <button onClick={onBack} className="flex items-center gap-1.5 text-sm text-[#8b7355] hover:text-[#6b5740] transition-colors">
        <ArrowLeft size={15} /> Retour à Surveillance nationale
      </button>

      {fpMessage && (
        <div className="fixed bottom-6 right-6 z-50 bg-[#2c1810] text-white text-sm px-4 py-3 rounded-xl shadow-xl">
          {fpMessage}
        </div>
      )}

      <div>
        <h1 className="text-2xl font-bold text-gray-900" style={{ fontFamily: 'Space Grotesk, sans-serif' }}>
          Typosquatting
        </h1>
        <p className="text-sm text-gray-400 mt-0.5">{total} domaines détectés</p>
      </div>

      <div className="flex gap-2">
        {['confirmed', 'potential'].map(f => (
          <button
            key={f}
            onClick={() => { setFilter(f); setPage(1) }}
            className={`px-3 py-1.5 rounded-full text-xs font-medium border transition-all ${
              filter === f
                ? 'bg-[#8b7355] text-white border-[#8b7355]'
                : 'bg-white text-gray-500 border-[#ede8e3] hover:border-[#c4a882]'
            }`}
          >
            {f === 'confirmed' ? 'Confirmés' : 'Potentiels'}
          </button>
        ))}
      </div>

      <div className="bg-white rounded-2xl border border-[#ede8e3] px-5 py-2">
        {loading ? (
          <div className="flex justify-center py-8">
            <div className="w-6 h-6 border-2 border-[#c4a882] border-t-transparent rounded-full animate-spin" />
          </div>
        ) : items.length === 0 ? (
          <p className="text-sm text-gray-400 italic py-6">Aucun résultat.</p>
        ) : items.map(item => (
          <TyposquatRow key={item.id} item={item} onClick={() => setDetailItem(item)} />
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
          title={detailItem.value}
          subtitle={`cible : ${detailItem.target_name || 'non identifiée'}`}
          onClose={() => setDetailItem(null)}
        >
          <div className="flex items-center gap-2 mb-5">
            <SeverityBadge level={detailItem.confirmed ? 'high' : 'medium'} />
            <span className="text-xs text-gray-400">
              {detailItem.confirmed ? 'Signal fort : domaine cible distinctif' : 'Signal à vérifier : domaine cible court'}
            </span>
          </div>
          <TyposquatMetadata metadata={detailItem.metadata} />
          {onOpenDetail && (
            <button
              onClick={() => { onOpenDetail(detailItem.value); setDetailItem(null) }}
              className="w-full mb-2 flex items-center justify-center gap-1.5 px-4 py-2.5 border border-[#ede8e3] text-[#8b7355] text-sm font-medium rounded-xl hover:border-[#c4a882] transition-colors"
            >
              Voir la fiche IOC complète <ExternalLink size={14} />
            </button>
          )}
          {isAdmin && (
            <button
              onClick={() => reportFalsePositive(detailItem)}
              className="w-full flex items-center justify-center gap-1.5 px-4 py-2.5 bg-red-50 text-red-600 text-sm font-medium rounded-xl hover:bg-red-100 transition-colors"
            >
              <Flag size={14} /> Signaler comme faux positif
            </button>
          )}
        </DetailModal>
      )}
    </div>
  )
}
