// src/pages/CameroonInstitutionsRank.jsx
import { useEffect, useState, useMemo } from 'react'
import { ArrowLeft, CheckCircle2, HelpCircle } from 'lucide-react'
import { api } from '../api/client'
import DetailModal from '../components/DetailModal'
import {
  CATEGORY_LABELS, SeverityBadge, InstitutionRankRow,
} from '../components/cameroon/Shared'
import TechInfoPanel from '../components/TechInfoPanel'

const PAGE_SIZE = 20

export default function CameroonInstitutionsRank({ onBack }) {
  const [institutions, setInstitutions] = useState([])
  const [typosquatConfirmed, setTyposquatConfirmed] = useState([])
  const [typosquatPotential, setTyposquatPotential] = useState([])
  const [loading, setLoading] = useState(true)
  const [categoryFilter, setCategoryFilter] = useState('')
  const [page, setPage] = useState(1)
  const [detailItem, setDetailItem] = useState(null)

  useEffect(() => {
    Promise.all([
      api.institutionsRanked(),
      api.indicators({ tag: 'typosquat:confirmed', page_size: 200 }),
      api.indicators({ tag: 'typosquat:potential', page_size: 200 }),
    ]).then(([ranked, confirmed, potential]) => {
      setInstitutions(ranked)
      const extractTarget = i => i.tags?.find(t => t.startsWith('typosquat:') && t !== 'typosquat:confirmed' && t !== 'typosquat:potential')?.replace('typosquat:', '')
      setTyposquatConfirmed(confirmed.items.map(i => ({ id: i.id, value: i.value, target_name: extractTarget(i), confirmed: true })))
      setTyposquatPotential(potential.items.map(i => ({ id: i.id, value: i.value, target_name: extractTarget(i), confirmed: false })))
    }).catch(console.error).finally(() => setLoading(false))
  }, [])

  const filtered = useMemo(() => {
    if (!categoryFilter) return institutions
    return institutions.filter(i => i.category === categoryFilter)
  }, [institutions, categoryFilter])

  const maxScore = institutions[0]?.risk_score || 1
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
          Classement des institutions par risque
        </h1>
        <p className="text-sm text-gray-400 mt-0.5">{filtered.length} institutions avec un signal actif</p>
      </div>

      <TechInfoPanel>
        <p>
          Classement complet des institutions camerounaises surveillées par score de risque
          composé (voir la page Cameroun pour le détail de la formule). Seules les institutions
          avec au moins un signal réel (score supérieur à zéro) apparaissent ici.
        </p>
      </TechInfoPanel>

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

      <div className="bg-white rounded-2xl border border-[#ede8e3] px-5 py-2">
        {pageItems.length === 0 ? (
          <p className="text-sm text-gray-400 italic py-6">Aucun résultat.</p>
        ) : pageItems.map((inst, i) => (
          <InstitutionRankRow
            key={inst.id}
            inst={inst}
            rank={(page - 1) * PAGE_SIZE + i + 1}
            maxScore={maxScore}
            onClick={() => setDetailItem(inst)}
          />
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

      {detailItem && (() => {
        const key = (detailItem.acronym || detailItem.name).toLowerCase().replace(/\s+/g, '_')
        const related = [...typosquatConfirmed, ...typosquatPotential].filter(t => t.target_name === key)
        return (
          <DetailModal
            title={detailItem.name}
            subtitle={CATEGORY_LABELS[detailItem.category]}
            onClose={() => setDetailItem(null)}
          >
            <div className="grid grid-cols-3 gap-3 mb-5">
              <div className="bg-[#faf8f5] rounded-xl p-3 text-center">
                <p className="text-lg font-bold text-gray-900" style={{ fontFamily: 'Space Grotesk, sans-serif' }}>{detailItem.risk_score}</p>
                <p className="text-[10px] text-gray-400 uppercase">Score de risque</p>
              </div>
              <div className="bg-[#faf8f5] rounded-xl p-3 text-center">
                <p className="text-lg font-bold text-gray-900" style={{ fontFamily: 'Space Grotesk, sans-serif' }}>{detailItem.typosquat_findings}</p>
                <p className="text-[10px] text-gray-400 uppercase">Typosquats</p>
              </div>
              <div className="bg-[#faf8f5] rounded-xl p-3 text-center">
                <p className="text-lg font-bold text-gray-900" style={{ fontFamily: 'Space Grotesk, sans-serif' }}>{detailItem.exposed_high_risk}</p>
                <p className="text-[10px] text-gray-400 uppercase">IPs haut risque</p>
              </div>
            </div>
            {related.length > 0 && (
              <div>
                <p className="text-xs font-semibold text-[#8b7355] uppercase tracking-wide mb-2">Domaines suspects liés</p>
                <div className="space-y-1.5">
                  {related.map(t => (
                    <div key={t.id} className="flex items-center justify-between text-sm bg-[#faf8f5] rounded-lg px-3 py-2">
                      <span className="font-mono text-gray-700">{t.value}</span>
                      <SeverityBadge level={t.confirmed ? 'high' : 'medium'} />
                    </div>
                  ))}
                </div>
              </div>
            )}
          </DetailModal>
        )
      })()}
    </div>
  )
}
