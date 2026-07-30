// src/pages/Cameroon.jsx
import { useEffect, useState, useMemo } from 'react'
import {
  AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
} from 'recharts'
import {
  Shield, ChevronRight, Server, Globe2,
  CheckCircle2, HelpCircle, X, ExternalLink, Flag, XCircle, Info,
} from 'lucide-react'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'
import DetailModal from '../components/DetailModal'
import { levelForRiskScore } from '../lib/severity'
import {
  CATEGORY_LABELS, SeverityBadge, RiskGauge, InstitutionRankRow,
  TyposquatRow, ExposedRankRow, InstitutionRow, CveDonut, TyposquatMetadata,
} from '../components/cameroon/Shared'
import TechInfoPanel from '../components/TechInfoPanel'

function QuickNav({ sections, active }) {
  return (
    <div className="sticky top-0 z-10 -mx-4 px-4 py-3 bg-[#faf8f5]/95 backdrop-blur-sm border-b border-[#ede8e3]">
      <div className="flex gap-1.5 overflow-x-auto">
        {sections.map(s => (
          <a key={s.id}
            href={`#${s.id}`}
            className={`shrink-0 inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-full text-xs font-medium border transition-all ${
              active === s.id
                ? 'bg-[#8b7355] text-white border-[#8b7355]'
                : 'bg-white text-gray-500 border-[#ede8e3] hover:border-[#c4a882]'
            }`}
          >
            {s.label}
            {s.count != null && (
              <span className={`text-[10px] px-1.5 py-0.5 rounded-full ${
                active === s.id ? 'bg-white/20' : 'bg-[#f5f0eb] text-gray-400'
              }`}>
                {s.count}
              </span>
            )}
          </a>
        ))}
      </div>
    </div>
  )
}

function Kpi({ label, value, icon: Icon, tone = 'default' }) {
  const tones = {
    default: 'bg-[#faf8f5] text-[#8b7355]',
    danger:  'bg-red-50 text-red-600',
    ok:      'bg-emerald-50 text-emerald-600',
  }
  return (
    <div className="bg-white rounded-2xl border border-[#ede8e3] p-5 hover:border-[#c4a882] hover:shadow-sm transition-all">
      <div className={`inline-flex p-2 rounded-xl mb-3 ${tones[tone]}`}>
        <Icon size={16} />
      </div>
      <p className="text-2xl font-bold text-gray-900" style={{ fontFamily: 'Space Grotesk, sans-serif' }}>
        {typeof value === 'number' ? value.toLocaleString('fr-FR') : value}
      </p>
      <p className="text-xs text-gray-400 mt-1">{label}</p>
    </div>
  )
}

export default function Cameroon({ onOpenDetail, onNavigate }) {
  const { isAdmin } = useAuth()

  const [overview, setOverview] = useState(null)
  const [timeline, setTimeline] = useState([])
  const [institutionsRanked, setInstitutionsRanked] = useState([])
  const [vulnSeverity, setVulnSeverity] = useState(null)
  const [loading, setLoading] = useState(true)
  const [activeSection, setActiveSection] = useState('urgent')

  const [typosquatConfirmed, setTyposquatConfirmed] = useState([])
  const [typosquatPotential, setTyposquatPotential] = useState([])
  const [typosquatFilter, setTyposquatFilter] = useState('confirmed')

  const [exposedAssets, setExposedAssets] = useState([])
  const [institutionFilter, setInstitutionFilter] = useState(null)

  const [institutions, setInstitutions] = useState([])
  const [detailItem, setDetailItem] = useState(null)
  const [fpMessage, setFpMessage] = useState(null)

  useEffect(() => {
    Promise.all([
      api.cameroonOverview(),
      api.cameroonTimeline(30),
      api.institutionsRanked(),
      api.vulnSeverity(),
      api.indicators({ tag: 'typosquat:confirmed', page_size: 7 }),
      api.indicators({ tag: 'typosquat:potential', page_size: 7 }),
      api.monitoredAssets(),
    ]).then(([ov, tl, ranked, vs, confirmed, potential, allInst]) => {
      setOverview(ov)
      setTimeline(tl)
      setInstitutionsRanked(ranked)
      setVulnSeverity(vs)
      const extractTarget = i => i.tags?.find(t => t.startsWith('typosquat:') && t !== 'typosquat:confirmed' && t !== 'typosquat:potential')?.replace('typosquat:', '')
      setTyposquatConfirmed(confirmed.items.map(i => ({ id: i.id, value: i.value, target_name: extractTarget(i), confirmed: true, metadata: i.metadata })))
      setTyposquatPotential(potential.items.map(i => ({ id: i.id, value: i.value, target_name: extractTarget(i), confirmed: false, metadata: i.metadata })))
      setInstitutions(allInst)
    }).catch(console.error).finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    // Aperçu uniquement — la liste complète avec filtres vit sur la page dédiée
    api.exposedAssets({ risk_level: 'high', page_size: 7 }).then(d => setExposedAssets(d.items)).catch(console.error)
  }, [])

  const maxRiskScore = institutionsRanked[0]?.risk_score || 1
  const topInstitutions = institutionsRanked.slice(0, 5)
  const activeTyposquat = typosquatFilter === 'confirmed' ? typosquatConfirmed : typosquatPotential
  const topExposedHigh = useMemo(
    () => exposedAssets.filter(a => a.risk_level === 'high').slice(0, 5),
    [exposedAssets]
  )

  const criticalFeed = useMemo(() => {
    const items = []
    typosquatConfirmed.slice(0, 3).forEach(t => items.push({
      text: `Domaine suspect détecté : ${t.value}, imite ${t.target_name || 'une institution suivie'}`,
      key: `t-${t.id}`,
    }))
    topExposedHigh.slice(0, 3).forEach(a => items.push({
      text: `IP à haut risque : ${a.ip_address} (${a.institution_name || 'institution inconnue'}), ${a.vulns?.length || 0} CVE`,
      key: `e-${a.id}`,
    }))
    return items.slice(0, 5)
  }, [typosquatConfirmed, topExposedHigh])

  async function reportFalsePositive(item) {
    if (!isAdmin) return
    const matchedInst = institutions.find(i =>
      (i.acronym || i.name).toLowerCase().replace(/\s+/g, '_') === item.target_name
    )
    try {
      const res = await api.reportFalsePositive({
        indicator_id: item.id,
        monitored_asset_id: matchedInst?.id,
      })
      setFpMessage(`${res.value} marqué faux positif${res.alias_added ? ', alias ajouté' : ''}`)
      setTyposquatConfirmed(prev => prev.filter(t => t.id !== item.id))
      setTyposquatPotential(prev => prev.filter(t => t.id !== item.id))
      setDetailItem(null)
      setTimeout(() => setFpMessage(null), 4000)
    } catch (e) {
      setFpMessage(`Erreur : ${e.message}`)
    }
  }

  if (loading) return (
    <div className="flex flex-col items-center justify-center h-64 gap-3">
      <div className="w-6 h-6 border-2 border-[#c4a882] border-t-transparent rounded-full animate-spin" />
      <p className="text-sm text-gray-400">Chargement…</p>
    </div>
  )
  if (!overview) return null

  const sections = [
    { id: 'urgent', label: 'Prioritaire' },
    { id: 'overview', label: "Vue d'ensemble" },
    { id: 'timeline', label: 'Timeline' },
    { id: 'institutions-rank', label: 'Institutions' },
    { id: 'typosquat', label: 'Typosquatting', count: overview.typosquat_confirmed + overview.typosquat_potential },
    { id: 'exposed', label: "Surface d'attaque", count: overview.exposed_total },
    { id: 'certificates', label: 'Certificats', count: overview.ct_findings },
    { id: 'institutions', label: 'Toutes les institutions' },
  ]

  return (
    <div className="space-y-8" style={{ fontFamily: 'Inter, sans-serif' }}>

      <div
        className="rounded-2xl overflow-hidden px-6 py-6"
        style={{ background: 'linear-gradient(135deg, #2c1810 0%, #4a3020 55%, #6b5740 100%)' }}
      >
        <p className="text-xs font-semibold text-[#e8d5b7] uppercase tracking-widest mb-1">
          Surveillance nationale
        </p>
        <h1 className="text-2xl font-bold text-white" style={{ fontFamily: 'Space Grotesk, sans-serif' }}>
          Cyberespace camerounais
        </h1>
        <p className="text-sm text-white/60 mt-1 max-w-2xl">
          Détection de typosquatting, certificats suspects et surface d'attaque exposée
          pour {overview.total_monitored_assets} institutions nationales : ministères,
          banques, opérateurs télécom et sociétés publiques.
        </p>
      </div>

      <TechInfoPanel>
        <p>
          Vue d'ensemble de la surveillance nationale, structurée autour de 4 mécanismes
          indépendants :
        </p>
        <ul className="list-disc pl-5 space-y-1">
          <li>
            Typosquatting — dnstwist, permutations de caractères + dictionnaire de mots-clés
            phishing + variantes de TLD
          </li>
          <li>Certificats SSL suspects — crt.sh, recherche par mot-clé de marque</li>
          <li>
            Domaines nouvellement enregistrés suspects — WhoisDS.com, alternative gratuite à crt.sh
          </li>
          <li>
            Surface d'attaque exposée — RIPEstat pour les préfixes IP annoncés, Shodan InternetDB
            pour les ports/CVE déjà observés passivement (aucun scan actif n'est effectué)
          </li>
        </ul>
        <p>
          Le score de risque par institution combine ces signaux : (typosquats × 3) + (IPs
          exposées à haut risque × 3) + (IPs à risque moyen × 1) + (certificats suspects × 2), en
          excluant les faux positifs confirmés (statut whitelisted).
        </p>
      </TechInfoPanel>

      {fpMessage && (
        <div className="fixed bottom-6 right-6 z-50 bg-[#2c1810] text-white text-sm px-4 py-3 rounded-xl shadow-xl">
          {fpMessage}
        </div>
      )}

      <QuickNav sections={sections} active={activeSection} />

      <section id="urgent">
        <div className="flex items-center gap-2.5 mb-4">
          <span className="w-2 h-2 rounded-full bg-red-700" />
          <h2 className="text-lg font-bold text-gray-900" style={{ fontFamily: 'Space Grotesk, sans-serif' }}>
            Nécessite une attention immédiate
          </h2>
        </div>
        <div className="grid grid-cols-1 xl:grid-cols-[1.6fr_1fr] gap-4">
          <div className="bg-[#fdf7f5] border border-[#f3d9d9] rounded-2xl p-5">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-bold text-gray-900" style={{ fontFamily: 'Space Grotesk, sans-serif' }}>
                Top 5 institutions à risque
              </h3>
              <a href="#institutions-rank" className="text-xs font-semibold text-[#8b7355] hover:text-[#6b5740]">
                Classement complet →
              </a>
            </div>
            <div className="space-y-2">
              {topInstitutions.map((inst, i) => (
                <InstitutionRankRow
                  key={inst.id}
                  inst={inst}
                  rank={i + 1}
                  maxScore={maxRiskScore}
                  onClick={() => setDetailItem({ type: 'institution', data: inst })}
                />
              ))}
              {topInstitutions.length === 0 && (
                <p className="text-sm text-gray-400 italic py-4">Aucun signal pour le moment.</p>
              )}
            </div>
          </div>
          <div className="flex flex-col gap-4">
            <div className="bg-[#fdf7f5] border border-[#f3d9d9] rounded-2xl p-5">
              <p className="text-xs font-semibold text-red-800 uppercase tracking-wide mb-1">CVE critiques actives</p>
              <p className="text-4xl font-bold text-red-800" style={{ fontFamily: 'Space Grotesk, sans-serif' }}>
                {vulnSeverity?.critical ?? 0}
              </p>
              <p className="text-xs text-[#8b7355] mt-1">
                sur {vulnSeverity?.distinct_cves ?? 0} CVE distinctes · <a href="#exposed" className="font-semibold hover:underline">voir la répartition →</a>
              </p>
            </div>
            <div className="bg-white border border-[#ede8e3] rounded-2xl p-5 flex-1">
              <p className="text-xs font-semibold text-[#8b7355] uppercase tracking-wide mb-3">Détections récentes</p>
              <div className="space-y-2.5">
                {criticalFeed.length === 0 ? (
                  <p className="text-sm text-gray-400 italic">Rien à signaler.</p>
                ) : criticalFeed.map(f => (
                  <div key={f.key} className="flex gap-2 items-start">
                    <span className="w-1.5 h-1.5 rounded-full bg-red-700 mt-1.5 shrink-0" />
                    <p className="text-xs text-gray-700 leading-relaxed">{f.text}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      <section id="overview">
        <h2 className="text-lg font-bold text-gray-900 mb-4" style={{ fontFamily: 'Space Grotesk, sans-serif' }}>
          Vue d'ensemble
        </h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Kpi label="Institutions suivies" value={overview.total_monitored_assets} icon={Shield} />
          <Kpi label="Typosquats confirmés" value={overview.typosquat_confirmed} icon={Globe2} tone="danger" />
          <Kpi label="IPs à haut risque" value={overview.exposed_high_risk} icon={Server} tone="danger" />
          <Kpi label="Domaines vérifiés" value={overview.domains_confirmed} icon={CheckCircle2} tone="ok" />
        </div>
      </section>

      <section id="timeline">
        <div className="bg-white rounded-2xl border border-[#ede8e3] p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-bold text-gray-900" style={{ fontFamily: 'Space Grotesk, sans-serif' }}>
              Nouvelles détections sur 30 jours
            </h2>
            <div className="flex gap-4 text-xs text-gray-500">
              <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-sm bg-[#c4a882]" />Typosquatting</span>
              <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-sm bg-[#8b7355]" />Certificats</span>
              <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-sm bg-[#7a1f1f]" />IPs exposées</span>
            </div>
          </div>
          <ResponsiveContainer width="100%" height={200}>
            <AreaChart data={timeline} margin={{ top: 0, right: 10, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f5f0eb" vertical={false} />
              <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#9ca3af' }} axisLine={false} tickLine={false}
                     tickFormatter={d => d.slice(5)} interval="preserveStartEnd" />
              <YAxis tick={{ fontSize: 10, fill: '#9ca3af' }} axisLine={false} tickLine={false} />
              <Tooltip />
              <Area type="monotone" dataKey="typosquat" stackId="1" stroke="#c4a882" fill="#c4a882" fillOpacity={0.7} />
              <Area type="monotone" dataKey="ct_monitor" stackId="1" stroke="#8b7355" fill="#8b7355" fillOpacity={0.7} />
              <Area type="monotone" dataKey="exposed_assets" stackId="1" stroke="#7a1f1f" fill="#7a1f1f" fillOpacity={0.7} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </section>

      <section id="institutions-rank">
        <h2 className="text-lg font-bold text-gray-900 mb-4" style={{ fontFamily: 'Space Grotesk, sans-serif' }}>
          Classement des institutions par score de risque
        </h2>
        <div className="bg-white rounded-2xl border border-[#ede8e3] px-5 py-2">
          {institutionsRanked.length === 0 ? (
            <p className="text-sm text-gray-400 italic py-6">Aucune institution avec un signal de risque pour le moment.</p>
          ) : institutionsRanked.slice(0, 7).map((inst, i) => (
            <InstitutionRankRow
              key={inst.id}
              inst={inst}
              rank={i + 1}
              maxScore={maxRiskScore}
              onClick={() => setDetailItem({ type: 'institution', data: inst })}
            />
          ))}
        </div>
        {institutionsRanked.length > 7 && (
          <button
            onClick={() => onNavigate('cameroon-institutions-rank')}
            className="w-full mt-2 flex items-center justify-center gap-1.5 px-4 py-3 bg-white border border-[#ede8e3] text-[#8b7355] text-sm font-medium rounded-xl hover:border-[#c4a882] transition-colors"
          >
            Voir le classement complet ({institutionsRanked.length}) <ChevronRight size={14} />
          </button>
        )}
      </section>

      <section id="typosquat">
        <h2 className="text-lg font-bold text-gray-900 mb-4" style={{ fontFamily: 'Space Grotesk, sans-serif' }}>
          Typosquatting
        </h2>
        <div className="flex gap-2 mb-3">
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
        <div className="bg-white rounded-2xl border border-[#ede8e3] px-5 py-2">
          {activeTyposquat.length === 0 ? (
            <p className="text-sm text-gray-400 italic py-6">Aucun résultat.</p>
          ) : activeTyposquat.map(item => (
            <TyposquatRow key={item.id} item={item} onClick={() => setDetailItem({ type: 'typosquat', data: item })} />
          ))}
        </div>
        <button
          onClick={() => onNavigate('cameroon-typosquat')}
          className="w-full mt-2 flex items-center justify-center gap-1.5 px-4 py-3 bg-white border border-[#ede8e3] text-[#8b7355] text-sm font-medium rounded-xl hover:border-[#c4a882] transition-colors"
        >
          Voir tous les résultats ({overview.typosquat_confirmed + overview.typosquat_potential}) <ChevronRight size={14} />
        </button>
      </section>

      <section id="exposed">
        <h2 className="text-lg font-bold text-gray-900 mb-4" style={{ fontFamily: 'Space Grotesk, sans-serif' }}>
          Surface d'attaque
        </h2>
        <div className="grid grid-cols-1 xl:grid-cols-[1fr_1.3fr] gap-4 mb-4">
          <div className="bg-white rounded-2xl border border-[#ede8e3] p-5">
            <h3 className="text-sm font-bold text-gray-900 mb-1" style={{ fontFamily: 'Space Grotesk, sans-serif' }}>
              Répartition des CVE par sévérité
            </h3>
            <p className="text-xs text-gray-400 mb-4">
              {vulnSeverity?.distinct_cves ?? 0} CVE distinctes · {vulnSeverity?.total_occurrences ?? 0} occurrences
            </p>
            {vulnSeverity && <CveDonut severity={vulnSeverity} />}
          </div>
          <div className="bg-white rounded-2xl border border-[#ede8e3] p-5">
            <h3 className="text-sm font-bold text-gray-900 mb-3" style={{ fontFamily: 'Space Grotesk, sans-serif' }}>
              IPs exposées les plus critiques
            </h3>
            {topExposedHigh.length === 0 ? (
              <p className="text-sm text-gray-400 italic py-4">Aucune IP à haut risque pour le moment.</p>
            ) : topExposedHigh.map(a => (
              <ExposedRankRow key={a.id} asset={a} onClick={() => setDetailItem({ type: 'exposed', data: a })} />
            ))}
          </div>
        </div>

        <button
          onClick={() => onNavigate('cameroon-exposed')}
          className="w-full flex items-center justify-center gap-1.5 px-4 py-3 bg-white border border-[#ede8e3] text-[#8b7355] text-sm font-medium rounded-xl hover:border-[#c4a882] transition-colors"
        >
          Voir toute la surface d'attaque ({overview.exposed_total}) <ChevronRight size={14} />
        </button>
      </section>

      <section id="certificates">
        <h2 className="text-lg font-bold text-gray-900 mb-4" style={{ fontFamily: 'Space Grotesk, sans-serif' }}>
          Certificats
        </h2>
        <div className="bg-white rounded-2xl border border-[#ede8e3] p-10 text-center">
          <Shield size={28} className="text-[#ede8e3] mx-auto mb-3" />
          <p className="text-sm text-gray-500 font-medium">
            {overview.ct_findings > 0 ? `${overview.ct_findings} certificats détectés` : 'Aucun résultat pour le moment'}
          </p>
        </div>
      </section>

      <section id="institutions">
        <h2 className="text-lg font-bold text-gray-900 mb-4" style={{ fontFamily: 'Space Grotesk, sans-serif' }}>
          Institutions surveillées
        </h2>
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-2.5">
          {institutions.slice(0, 7).map(a => (
            <InstitutionRow
              key={a.id}
              asset={a}
              onClick={() => setDetailItem({ type: 'institution', data: a })}
            />
          ))}
        </div>
        {institutions.length > 7 && (
          <button
            onClick={() => onNavigate('cameroon-institutions')}
            className="w-full mt-2 flex items-center justify-center gap-1.5 px-4 py-3 bg-white border border-[#ede8e3] text-[#8b7355] text-sm font-medium rounded-xl hover:border-[#c4a882] transition-colors"
          >
            Voir toutes les institutions ({institutions.length}) <ChevronRight size={14} />
          </button>
        )}
      </section>

      {detailItem?.type === 'institution' && (() => {
        const inst = detailItem.data
        const key = (inst.acronym || inst.name).toLowerCase().replace(/\s+/g, '_')
        const relatedTyposquats = [...typosquatConfirmed, ...typosquatPotential].filter(t => t.target_name === key)
        return (
          <DetailModal
            title={inst.name}
            subtitle={inst.acronym ? `${inst.acronym} · ${CATEGORY_LABELS[inst.category] || inst.category}` : CATEGORY_LABELS[inst.category]}
            onClose={() => setDetailItem(null)}
          >
            {inst.domain_status === 'not_found' ? (
              <div className="flex items-center gap-2 mb-2 text-sm">
                <XCircle size={14} className="text-red-400" />
                <span className="text-red-500">
                  {inst.domain ? `${inst.domain} (non retenu)` : 'Aucun domaine officiel identifié'}
                </span>
              </div>
            ) : inst.domain && (
              <div className="flex items-center gap-2 mb-2 text-sm">
                {inst.domain_status === 'confirmed'
                  ? <CheckCircle2 size={14} className="text-emerald-500" />
                  : <HelpCircle size={14} className="text-amber-400" />}
                <span className="font-mono text-gray-700">{inst.domain}</span>
              </div>
            )}
            {inst.verification_note && (
              <div className="flex items-start gap-2 mb-4 px-3 py-2.5 bg-[#faf8f5] rounded-xl">
                <Info size={13} className="text-[#8b7355] shrink-0 mt-0.5" />
                <p className="text-xs text-gray-600 leading-relaxed">{inst.verification_note}</p>
              </div>
            )}
            {inst.risk_score != null && (
              <div className="grid grid-cols-3 gap-3 mb-5">
                <div className="bg-[#faf8f5] rounded-xl p-3 text-center">
                  <p className="text-lg font-bold text-gray-900" style={{ fontFamily: 'Space Grotesk, sans-serif' }}>{inst.risk_score}</p>
                  <p className="text-[10px] text-gray-400 uppercase">Score de risque</p>
                </div>
                <div className="bg-[#faf8f5] rounded-xl p-3 text-center">
                  <p className="text-lg font-bold text-gray-900" style={{ fontFamily: 'Space Grotesk, sans-serif' }}>{inst.typosquat_findings}</p>
                  <p className="text-[10px] text-gray-400 uppercase">Typosquats</p>
                </div>
                <div className="bg-[#faf8f5] rounded-xl p-3 text-center">
                  <p className="text-lg font-bold text-gray-900" style={{ fontFamily: 'Space Grotesk, sans-serif' }}>{inst.exposed_high_risk}</p>
                  <p className="text-[10px] text-gray-400 uppercase">IPs haut risque</p>
                </div>
              </div>
            )}
            {relatedTyposquats.length > 0 && (
              <div className="mb-4">
                <p className="text-xs font-semibold text-[#8b7355] uppercase tracking-wide mb-2">Domaines suspects liés</p>
                <div className="space-y-1.5">
                  {relatedTyposquats.map(t => (
                    <div key={t.id} className="flex items-center justify-between text-sm bg-[#faf8f5] rounded-lg px-3 py-2">
                      <span className="font-mono text-gray-700">{t.value}</span>
                      <SeverityBadge level={t.confirmed ? 'high' : 'medium'} />
                    </div>
                  ))}
                </div>
              </div>
            )}
            <button
              onClick={() => {
                sessionStorage.setItem('cameroon_exposed_institution_filter', JSON.stringify({ id: inst.id, name: inst.name }))
                setDetailItem(null)
                onNavigate('cameroon-exposed')
              }}
              className="w-full mt-2 flex items-center justify-center gap-1.5 px-4 py-2.5 bg-[#8b7355] text-white text-sm font-medium rounded-xl hover:bg-[#6b5740] transition-colors"
            >
              Voir les IPs exposées de cette institution <ArrowIcon />
            </button>
          </DetailModal>
        )
      })()}

      {detailItem?.type === 'typosquat' && (
        <DetailModal
          title={detailItem.data.value}
          subtitle={`cible : ${detailItem.data.target_name || 'non identifiée'}`}
          onClose={() => setDetailItem(null)}
        >
          <div className="flex items-center gap-2 mb-4">
            <SeverityBadge level={detailItem.data.confirmed ? 'high' : 'medium'} />
            <span className="text-xs text-gray-400">
              {detailItem.data.confirmed ? 'Signal fort : domaine cible distinctif' : 'Signal à vérifier : domaine cible court'}
            </span>
          </div>
          <TyposquatMetadata metadata={detailItem.data.metadata} />
          {onOpenDetail && (
            <button
              onClick={() => { onOpenDetail(detailItem.data.value); setDetailItem(null) }}
              className="w-full mb-2 flex items-center justify-center gap-1.5 px-4 py-2.5 border border-[#ede8e3] text-[#8b7355] text-sm font-medium rounded-xl hover:border-[#c4a882] transition-colors"
            >
              Voir la fiche IOC complète <ExternalLink size={14} />
            </button>
          )}
          {isAdmin && (
            <button
              onClick={() => reportFalsePositive(detailItem.data)}
              className="w-full flex items-center justify-center gap-1.5 px-4 py-2.5 bg-red-50 text-red-600 text-sm font-medium rounded-xl hover:bg-red-100 transition-colors"
            >
              <Flag size={14} /> Signaler comme faux positif
            </button>
          )}
        </DetailModal>
      )}

      {detailItem?.type === 'exposed' && (
        <DetailModal
          title={detailItem.data.ip_address}
          subtitle={detailItem.data.institution_name || 'Institution inconnue'}
          onClose={() => setDetailItem(null)}
        >
          <div className="mb-4"><SeverityBadge level={detailItem.data.risk_level} /></div>
          {detailItem.data.ports?.length > 0 && (
            <div className="mb-4">
              <p className="text-xs font-semibold text-[#8b7355] uppercase tracking-wide mb-2">Ports ouverts</p>
              <div className="flex flex-wrap gap-1.5">
                {detailItem.data.ports.map(p => (
                  <span key={p} className="text-xs font-mono px-2 py-1 bg-[#f5f0eb] text-[#8b7355] rounded-lg">:{p}</span>
                ))}
              </div>
            </div>
          )}
          {detailItem.data.hostnames?.length > 0 && (
            <div className="mb-4">
              <p className="text-xs font-semibold text-[#8b7355] uppercase tracking-wide mb-2">Noms d'hôte</p>
              <div className="space-y-1">
                {detailItem.data.hostnames.map(h => (
                  <p key={h} className="text-sm font-mono text-gray-700">{h}</p>
                ))}
              </div>
            </div>
          )}
          {detailItem.data.vulns?.length > 0 && (
            <div>
              <p className="text-xs font-semibold text-[#8b7355] uppercase tracking-wide mb-2">
                {detailItem.data.vulns.length} CVE identifiées
              </p>
              <div className="flex flex-wrap gap-1.5 max-h-52 overflow-y-auto">
                {detailItem.data.vulns.map(cve => (
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

function ArrowIcon() {
  return <ChevronRight size={14} />
}
