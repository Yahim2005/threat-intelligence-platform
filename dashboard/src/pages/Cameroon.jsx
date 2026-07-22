// src/pages/Cameroon.jsx
import { useEffect, useState } from 'react'
import {
  MapPin, Shield, AlertTriangle, Building2, Radio, Landmark,
  ChevronRight, ExternalLink, Server, Globe2, CheckCircle2, HelpCircle
} from 'lucide-react'
import { api } from '../api/client'

const CATEGORY_LABELS = {
  ministry: 'Ministère',
  bank: 'Banque',
  telecom: 'Télécom / ISP',
  public_company: 'Société publique',
  institution: 'Institution',
}
const CATEGORY_ICONS = {
  ministry: Landmark,
  bank: Building2,
  telecom: Radio,
  public_company: Building2,
  institution: Shield,
}

const RISK_STYLES = {
  high:   { bg: 'bg-red-50',    text: 'text-red-600',    dot: 'bg-red-500',    label: 'Haut risque' },
  medium: { bg: 'bg-amber-50',  text: 'text-amber-600',  dot: 'bg-amber-400',  label: 'Risque moyen' },
  info:   { bg: 'bg-gray-50',   text: 'text-gray-500',   dot: 'bg-gray-300',   label: 'Info' },
}

function Tab({ label, active, onClick, count }) {
  return (
    <button
      onClick={onClick}
      className={`relative px-4 py-2.5 text-sm font-medium transition-all border-b-2 ${
        active
          ? 'text-[#2c1810] border-[#8b7355]'
          : 'text-gray-400 border-transparent hover:text-[#8b7355]'
      }`}
    >
      {label}
      {count != null && (
        <span className={`ml-1.5 text-xs px-1.5 py-0.5 rounded-full ${
          active ? 'bg-[#8b7355] text-white' : 'bg-[#f5f0eb] text-gray-400'
        }`}>
          {count}
        </span>
      )}
    </button>
  )
}

function Kpi({ label, value, icon: Icon, tone = 'default' }) {
  const tones = {
    default: 'text-[#8b7355] bg-[#faf8f5]',
    danger:  'text-red-600 bg-red-50',
    warn:    'text-amber-600 bg-amber-50',
    ok:      'text-emerald-600 bg-emerald-50',
  }
  return (
    <div className="bg-white rounded-2xl border border-[#ede8e3] p-5 flex items-center gap-4">
      <div className={`p-2.5 rounded-xl ${tones[tone]}`}>
        <Icon size={18} />
      </div>
      <div>
        <p className="text-2xl font-bold text-gray-900" style={{ fontFamily: 'Space Grotesk, sans-serif' }}>
          {value?.toLocaleString?.() ?? value}
        </p>
        <p className="text-xs text-gray-400">{label}</p>
      </div>
    </div>
  )
}

function DomainCard({ item, onOpenDetail }) {
  return (
    <div
      onClick={() => onOpenDetail && onOpenDetail(item.value)}
      className="bg-white rounded-xl border border-[#ede8e3] p-4 cursor-pointer
                 hover:border-[#c4a882] hover:shadow-sm transition-all flex items-center justify-between gap-3"
    >
      <div className="min-w-0">
        <p className="font-mono text-sm text-gray-800 truncate">{item.value}</p>
        <p className="text-xs text-gray-400 mt-0.5">
          imite <span className="text-[#8b7355] font-medium">{item.target_name || '—'}</span>
        </p>
      </div>
      <ChevronRight size={16} className="text-gray-300 shrink-0" />
    </div>
  )
}

function ExposedRow({ asset }) {
  const risk = RISK_STYLES[asset.risk_level] || RISK_STYLES.info
  return (
    <div className="bg-white rounded-xl border border-[#ede8e3] p-4">
      <div className="flex items-center justify-between gap-3 mb-2">
        <div className="flex items-center gap-2 min-w-0">
          <span className={`w-2 h-2 rounded-full shrink-0 ${risk.dot}`} />
          <p className="font-mono text-sm font-medium text-gray-800 truncate">{asset.ip_address}</p>
          <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${risk.bg} ${risk.text} shrink-0`}>
            {risk.label}
          </span>
        </div>
        <span className="text-xs text-gray-400 shrink-0">{asset.institution_name || 'Institution inconnue'}</span>
      </div>
      <div className="flex flex-wrap gap-1.5">
        {(asset.ports || []).slice(0, 8).map(p => (
          <span key={p} className="text-[10px] font-mono px-1.5 py-0.5 bg-[#f5f0eb] text-[#8b7355] rounded">
            :{p}
          </span>
        ))}
        {asset.vulns?.length > 0 && (
          <span className="text-[10px] px-1.5 py-0.5 bg-red-50 text-red-500 rounded font-medium">
            {asset.vulns.length} CVE{asset.vulns.length > 1 ? 's' : ''}
          </span>
        )}
      </div>
    </div>
  )
}

function InstitutionRow({ asset }) {
  const Icon = CATEGORY_ICONS[asset.category] || Shield
  return (
    <div className="bg-white rounded-xl border border-[#ede8e3] p-4 flex items-center justify-between gap-3">
      <div className="flex items-center gap-3 min-w-0">
        <div className="p-2 rounded-lg bg-[#faf8f5] shrink-0">
          <Icon size={14} className="text-[#8b7355]" />
        </div>
        <div className="min-w-0">
          <p className="text-sm font-medium text-gray-800 truncate">{asset.name}</p>
          <p className="text-xs text-gray-400">{asset.acronym || '—'} · {CATEGORY_LABELS[asset.category]}</p>
        </div>
      </div>
      <div className="shrink-0 text-right">
        {asset.domain ? (
          <div className="flex items-center gap-1.5 justify-end">
            {asset.domain_status === 'confirmed'
              ? <CheckCircle2 size={12} className="text-emerald-500" />
              : <HelpCircle size={12} className="text-amber-400" />}
            <span className="text-xs font-mono text-gray-500">{asset.domain}</span>
          </div>
        ) : (
          <span className="text-xs text-gray-300 italic">domaine inconnu</span>
        )}
      </div>
    </div>
  )
}

export default function Cameroon({ onOpenDetail }) {
  const [overview, setOverview] = useState(null)
  const [tab, setTab] = useState('overview')
  const [loading, setLoading] = useState(true)

  const [typosquatConfirmed, setTyposquatConfirmed] = useState([])
  const [typosquatPotential, setTyposquatPotential] = useState([])
  const [typosquatFilter, setTyposquatFilter] = useState('confirmed')

  const [exposedAssets, setExposedAssets] = useState([])
  const [riskFilter, setRiskFilter] = useState('')

  const [institutions, setInstitutions] = useState([])
  const [categoryFilter, setCategoryFilter] = useState('')

  useEffect(() => {
    api.cameroonOverview().then(setOverview).catch(console.error).finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    if (tab !== 'typosquat') return
    api.indicators({ tag: 'typosquat:confirmed', page_size: 100 })
      .then(d => setTyposquatConfirmed(
        d.items.map(i => ({ value: i.value, target_name: i.metadata?.target_name || i.tags?.find(t => t.startsWith('typosquat:') && t !== 'typosquat:confirmed' && t !== 'typosquat:potential')?.replace('typosquat:', '') }))
      ))
      .catch(console.error)
    api.indicators({ tag: 'typosquat:potential', page_size: 100 })
      .then(d => setTyposquatPotential(
        d.items.map(i => ({ value: i.value, target_name: i.tags?.find(t => t.startsWith('typosquat:') && t !== 'typosquat:confirmed' && t !== 'typosquat:potential')?.replace('typosquat:', '') }))
      ))
      .catch(console.error)
  }, [tab])

  useEffect(() => {
    if (tab !== 'exposed') return
    const params = riskFilter ? { risk_level: riskFilter, page_size: 100 } : { page_size: 100 }
    api.exposedAssets(params).then(d => setExposedAssets(d.items)).catch(console.error)
  }, [tab, riskFilter])

  useEffect(() => {
    if (tab !== 'institutions') return
    const params = categoryFilter ? { category: categoryFilter } : {}
    api.monitoredAssets(params).then(setInstitutions).catch(console.error)
  }, [tab, categoryFilter])

  if (loading) return (
    <div className="flex flex-col items-center justify-center h-64 gap-3">
      <div className="w-6 h-6 border-2 border-[#c4a882] border-t-transparent rounded-full animate-spin" />
      <p className="text-sm text-gray-400">Chargement…</p>
    </div>
  )
  if (!overview) return null

  const activeTyposquat = typosquatFilter === 'confirmed' ? typosquatConfirmed : typosquatPotential

  return (
    <div className="space-y-6" style={{ fontFamily: 'Inter, sans-serif' }}>

      <div
        className="rounded-2xl overflow-hidden px-6 py-6"
        style={{ background: 'linear-gradient(135deg, #1a3d2e 0%, #2c1810 55%, #7a1f1f 100%)' }}
      >
        <div className="flex items-center gap-3 mb-1">
          <MapPin size={18} className="text-[#e8d5b7]" />
          <p className="text-xs font-semibold text-[#e8d5b7] uppercase tracking-widest">
            Surveillance nationale
          </p>
        </div>
        <h1 className="text-2xl font-bold text-white" style={{ fontFamily: 'Space Grotesk, sans-serif' }}>
          Cyberespace camerounais
        </h1>
        <p className="text-sm text-white/60 mt-1 max-w-2xl">
          Détection de typosquatting, certificats suspects et surface d'attaque exposée
          pour {overview.total_monitored_assets} institutions nationales — ministères,
          banques, opérateurs télécom et sociétés publiques.
        </p>
      </div>

      <div className="grid grid-cols-2 xl:grid-cols-4 gap-4">
        <Kpi label="Institutions suivies" value={overview.total_monitored_assets} icon={Shield} />
        <Kpi label="Typosquats confirmés" value={overview.typosquat_confirmed} icon={Globe2} tone="danger" />
        <Kpi label="IPs à haut risque" value={overview.exposed_high_risk} icon={Server} tone="danger" />
        <Kpi label="Domaines vérifiés" value={overview.domains_confirmed} icon={CheckCircle2} tone="ok" />
      </div>

      <div className="border-b border-[#ede8e3] flex gap-1 overflow-x-auto">
        <Tab label="Vue d'ensemble" active={tab === 'overview'} onClick={() => setTab('overview')} />
        <Tab label="Typosquatting" active={tab === 'typosquat'} onClick={() => setTab('typosquat')}
             count={overview.typosquat_confirmed + overview.typosquat_potential} />
        <Tab label="Surface d'attaque" active={tab === 'exposed'} onClick={() => setTab('exposed')}
             count={overview.exposed_total} />
        <Tab label="Certificats" active={tab === 'ct'} onClick={() => setTab('ct')}
             count={overview.ct_findings} />
        <Tab label="Institutions" active={tab === 'institutions'} onClick={() => setTab('institutions')}
             count={overview.total_monitored_assets} />
      </div>

      {tab === 'overview' && (
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-5">
          <div className="bg-white rounded-2xl border border-[#ede8e3] p-6 xl:col-span-2">
            <h3 className="text-sm font-bold text-gray-900 mb-1" style={{ fontFamily: 'Space Grotesk, sans-serif' }}>
              Méthodologie de surveillance
            </h3>
            <p className="text-xs text-gray-400 mb-4">Trois angles complémentaires, tous automatisés</p>
            <div className="space-y-3">
              <div className="flex gap-3">
                <div className="p-2 rounded-lg bg-[#faf8f5] h-fit"><Globe2 size={14} className="text-[#8b7355]" /></div>
                <div>
                  <p className="text-sm font-medium text-gray-800">Typosquatting (dnstwist)</p>
                  <p className="text-xs text-gray-400">Détecte les domaines enregistrés qui imitent nos institutions officielles.</p>
                </div>
              </div>
              <div className="flex gap-3">
                <div className="p-2 rounded-lg bg-[#faf8f5] h-fit"><Shield size={14} className="text-[#8b7355]" /></div>
                <div>
                  <p className="text-sm font-medium text-gray-800">Certificate Transparency (crt.sh)</p>
                  <p className="text-xs text-gray-400">Surveille les certificats SSL émis pour des domaines suspects — souvent le premier signal avant une campagne de phishing.</p>
                </div>
              </div>
              <div className="flex gap-3">
                <div className="p-2 rounded-lg bg-[#faf8f5] h-fit"><Server size={14} className="text-[#8b7355]" /></div>
                <div>
                  <p className="text-sm font-medium text-gray-800">Surface d'attaque (RIPEstat + Shodan InternetDB)</p>
                  <p className="text-xs text-gray-400">Recense les services exposés et vulnérabilités connues sur les plages IP des opérateurs camerounais.</p>
                </div>
              </div>
            </div>
          </div>
          <div className="bg-white rounded-2xl border border-[#ede8e3] p-6">
            <h3 className="text-sm font-bold text-gray-900 mb-3" style={{ fontFamily: 'Space Grotesk, sans-serif' }}>
              Répartition des signaux
            </h3>
            <div className="space-y-2.5">
              {[
                { label: 'Typosquats confirmés', value: overview.typosquat_confirmed, tone: 'text-red-600' },
                { label: 'Typosquats potentiels', value: overview.typosquat_potential, tone: 'text-amber-500' },
                { label: 'IPs haut risque', value: overview.exposed_high_risk, tone: 'text-red-600' },
                { label: 'IPs risque moyen', value: overview.exposed_medium_risk, tone: 'text-amber-500' },
                { label: 'Certificats suspects', value: overview.ct_findings, tone: 'text-gray-400' },
              ].map(row => (
                <div key={row.label} className="flex items-center justify-between text-sm">
                  <span className="text-gray-500">{row.label}</span>
                  <span className={`font-bold ${row.tone}`} style={{ fontFamily: 'Space Grotesk, sans-serif' }}>
                    {row.value}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {tab === 'typosquat' && (
        <div className="space-y-4">
          <div className="flex gap-2">
            {['confirmed', 'potential'].map(f => (
              <button
                key={f}
                onClick={() => setTyposquatFilter(f)}
                className={`px-3 py-1.5 rounded-full text-xs font-medium border transition-all ${
                  typosquatFilter === f
                    ? 'bg-[#8b7355] text-white border-[#8b7355]'
                    : 'bg-white text-gray-500 border-[#ede8e3] hover:border-[#c4a882]'
                }`}
              >
                {f === 'confirmed' ? `Confirmés (${overview.typosquat_confirmed})` : `Potentiels (${overview.typosquat_potential})`}
              </button>
            ))}
          </div>
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-3">
            {activeTyposquat.length === 0 ? (
              <p className="text-sm text-gray-400 italic col-span-2">Aucun résultat.</p>
            ) : activeTyposquat.map(item => (
              <DomainCard key={item.value} item={item} onOpenDetail={onOpenDetail} />
            ))}
          </div>
        </div>
      )}

      {tab === 'exposed' && (
        <div className="space-y-4">
          <div className="flex gap-2">
            {[{ v: '', l: 'Tous' }, { v: 'high', l: 'Haut risque' }, { v: 'medium', l: 'Risque moyen' }, { v: 'info', l: 'Info' }].map(({ v, l }) => (
              <button
                key={v}
                onClick={() => setRiskFilter(v)}
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
          <div className="space-y-2.5">
            {exposedAssets.length === 0 ? (
              <p className="text-sm text-gray-400 italic">Aucun résultat — le scan est peut-être encore en cours.</p>
            ) : exposedAssets.map(a => <ExposedRow key={a.id} asset={a} />)}
          </div>
        </div>
      )}

      {tab === 'ct' && (
        <div className="bg-white rounded-2xl border border-[#ede8e3] p-10 text-center">
          <Shield size={28} className="text-[#ede8e3] mx-auto mb-3" />
          <p className="text-sm text-gray-500 font-medium">
            {overview.ct_findings > 0 ? `${overview.ct_findings} certificats détectés` : 'Aucun résultat pour le moment'}
          </p>
        </div>
      )}

      {tab === 'institutions' && (
        <div className="space-y-4">
          <div className="flex gap-2 flex-wrap">
            {[{ v: '', l: 'Toutes' }, ...Object.entries(CATEGORY_LABELS).map(([v, l]) => ({ v, l }))].map(({ v, l }) => (
              <button
                key={v}
                onClick={() => setCategoryFilter(v)}
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
            {institutions.map(a => <InstitutionRow key={a.id} asset={a} />)}
          </div>
        </div>
      )}
    </div>
  )
}
