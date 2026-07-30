// src/pages/CameroonExposed.jsx
import { useEffect, useState } from 'react'
import { ArrowLeft, X } from 'lucide-react'
import { api } from '../api/client'
import DetailModal from '../components/DetailModal'
import { SeverityBadge, ExposedRankRow } from '../components/cameroon/Shared'
import TechInfoPanel from '../components/TechInfoPanel'

const PAGE_SIZE = 20
const STORAGE_KEY = 'cameroon_exposed_institution_filter'

export default function CameroonExposed({ onBack }) {
  const [items, setItems] = useState([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [riskFilter, setRiskFilter] = useState('')
  const [institutionFilter, setInstitutionFilter] = useState(null)
  const [detailItem, setDetailItem] = useState(null)

  useEffect(() => {
    const stored = sessionStorage.getItem(STORAGE_KEY)
    if (stored) {
      try { setInstitutionFilter(JSON.parse(stored)) } catch {}
      sessionStorage.removeItem(STORAGE_KEY)
    }
  }, [])

  useEffect(() => {
    setLoading(true)
    const params = { page, page_size: PAGE_SIZE }
    if (riskFilter) params.risk_level = riskFilter
    if (institutionFilter) params.monitored_asset_id = institutionFilter.id
    api.exposedAssets(params).then(d => {
      setItems(d.items)
      setTotal(d.total)
    }).catch(console.error).finally(() => setLoading(false))
  }, [riskFilter, institutionFilter, page])

  const totalPages = Math.max(Math.ceil(total / PAGE_SIZE), 1)

  return (
    <div className="space-y-5" style={{ fontFamily: 'Inter, sans-serif' }}>
      <button onClick={onBack} className="flex items-center gap-1.5 text-sm text-[#8b7355] hover:text-[#6b5740] transition-colors">
        <ArrowLeft size={15} /> Retour à Surveillance nationale
      </button>

      <div>
        <h1 className="text-2xl font-bold text-gray-900" style={{ fontFamily: 'Space Grotesk, sans-serif' }}>
          Surface d'attaque
        </h1>
        <p className="text-sm text-gray-400 mt-0.5">{total} IPs exposées identifiées</p>
      </div>

      <TechInfoPanel>
        <p>
          Surface d'attaque exposée des institutions camerounaises. Les adresses IP proviennent
          des préfixes réellement annoncés par chaque opérateur (via RIPEstat), et chaque IP est
          vérifiée auprès de Shodan InternetDB — un service passif qui restitue ce qui a déjà été
          observé publiquement sur Internet, sans qu'aucun scan actif ne soit effectué depuis
          cette plateforme. Le niveau de risque dépend des ports sensibles ouverts (ex: RDP,
          bases de données exposées) et des vulnérabilités (CVE) déjà associées à l'IP.
        </p>
      </TechInfoPanel>

      {institutionFilter && (
        <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium bg-[#8b7355] text-white">
          Filtré : {institutionFilter.name}
          <button onClick={() => { setInstitutionFilter(null); setPage(1) }} className="hover:opacity-70">
            <X size={12} />
          </button>
        </span>
      )}

      <div className="flex gap-2">
        {[{ v: '', l: 'Tous' }, { v: 'high', l: 'Haut risque' }, { v: 'medium', l: 'Risque moyen' }, { v: 'info', l: 'Info' }].map(({ v, l }) => (
          <button
            key={v}
            onClick={() => { setRiskFilter(v); setPage(1) }}
            className={`px-3 py-1.5 rounded-full text-xs font-medium border transition-all ${
              riskFilter === v
                ? 'bg-[#8b7355] text-white border-[#8b7355]'
                : 'bg-white text-gray-500 border-[#ede8e3] hover:border-[#c4a882]'
            }`}
          >
            {l}
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
        ) : items.map(a => (
          <ExposedRankRow key={a.id} asset={a} onClick={() => setDetailItem(a)} />
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
          title={detailItem.ip_address}
          subtitle={detailItem.institution_name || 'Institution inconnue'}
          onClose={() => setDetailItem(null)}
        >
          <div className="mb-4"><SeverityBadge level={detailItem.risk_level} /></div>
          {detailItem.ports?.length > 0 && (
            <div className="mb-4">
              <p className="text-xs font-semibold text-[#8b7355] uppercase tracking-wide mb-2">Ports ouverts</p>
              <div className="flex flex-wrap gap-1.5">
                {detailItem.ports.map(p => (
                  <span key={p} className="text-xs font-mono px-2 py-1 bg-[#f5f0eb] text-[#8b7355] rounded-lg">:{p}</span>
                ))}
              </div>
            </div>
          )}
          {detailItem.hostnames?.length > 0 && (
            <div className="mb-4">
              <p className="text-xs font-semibold text-[#8b7355] uppercase tracking-wide mb-2">Noms d'hôte</p>
              <div className="space-y-1">
                {detailItem.hostnames.map(h => (
                  <p key={h} className="text-sm font-mono text-gray-700">{h}</p>
                ))}
              </div>
            </div>
          )}
          {detailItem.vulns?.length > 0 && (
            <div>
              <p className="text-xs font-semibold text-[#8b7355] uppercase tracking-wide mb-2">
                {detailItem.vulns.length} CVE identifiées
              </p>
              <div className="flex flex-wrap gap-1.5 max-h-52 overflow-y-auto">
                {detailItem.vulns.map(cve => (
                  <a key={cve}
                    href={`https://nvd.nist.gov/vuln/detail/${cve}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-[11px] font-mono bg-red-50 text-red-500 rounded px-1.5 py-0.5 hover:underline"
                  >
                    {cve}
                  </a>
                ))}
              </div>
            </div>
          )}
        </DetailModal>
      )}
    </div>
  )
}
