// src/components/cameroon/Shared.jsx
// Composants réutilisés par Cameroon.jsx et les 4 pages dédiées
// (classement institutions, typosquatting, surface d'attaque, institutions).
import { Shield, Building2, Radio, Landmark, ChevronRight, XCircle, CheckCircle2, HelpCircle } from 'lucide-react'
import { SEVERITY, severityFor, levelForRiskScore } from '../../lib/severity'

export const CATEGORY_LABELS = {
  ministry: 'Ministère',
  bank: 'Banque',
  telecom: 'Télécom / ISP',
  public_company: 'Société publique',
  institution: 'Institution',
}
export const CATEGORY_ICONS = {
  ministry: Landmark,
  bank: Building2,
  telecom: Radio,
  public_company: Building2,
  institution: Shield,
}

export function SeverityBadge({ level }) {
  const s = severityFor(level)
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-semibold border ${s.badge}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${s.dot}`} />
      {s.label}
    </span>
  )
}

export function RiskGauge({ score, maxScore }) {
  const pct = Math.max(Math.round((Math.log10(score + 1) / Math.log10(maxScore + 1)) * 100), 6)
  const level = levelForRiskScore(score)
  return (
    <div className="h-1.5 rounded-full bg-[#f3f0eb] overflow-hidden">
      <div className={`h-full rounded-full ${severityFor(level).dot}`} style={{ width: `${pct}%` }} />
    </div>
  )
}

export function InstitutionRankRow({ inst, rank, maxScore, onClick }) {
  const level = levelForRiskScore(inst.risk_score)
  return (
    <div
      onClick={onClick}
      className="flex items-center gap-4 py-3.5 border-t border-[#f2ede6] first:border-t-0 cursor-pointer hover:bg-[#faf8f5] transition-colors -mx-2 px-2 rounded-lg"
    >
      <span className="w-6 text-xs font-bold text-[#c4a882] shrink-0" style={{ fontFamily: 'Space Grotesk, sans-serif' }}>
        {rank}
      </span>
      <div className="w-48 shrink-0 min-w-0">
        <p className="text-sm font-semibold text-gray-800 truncate">{inst.name}</p>
        <p className="text-[11px] text-[#8b7355] mt-0.5">
          {inst.typosquat_findings} typosquats · {inst.exposed_high_risk} IPs haut risque · {inst.ct_findings} certificats
        </p>
      </div>
      <div className="flex-1">
        <RiskGauge score={inst.risk_score} maxScore={maxScore} />
      </div>
      <div className="shrink-0"><SeverityBadge level={level} /></div>
      <span className="w-12 text-right text-sm font-bold text-gray-800 shrink-0" style={{ fontFamily: 'Space Grotesk, sans-serif' }}>
        {inst.risk_score}
      </span>
      <ChevronRight size={15} className="text-gray-300 shrink-0" />
    </div>
  )
}

export function TyposquatRow({ item, onClick }) {
  return (
    <div
      onClick={onClick}
      className="flex items-center gap-4 py-3 border-t border-[#f2ede6] first:border-t-0 cursor-pointer hover:bg-[#faf8f5] transition-colors -mx-2 px-2 rounded-lg"
    >
      <div className="flex-1 min-w-0">
        <p className="font-mono text-sm font-semibold text-gray-800 truncate">{item.value}</p>
        <p className="text-[11px] text-[#8b7355] mt-0.5">cible : {item.target_name || 'non identifiée'}</p>
      </div>
      <SeverityBadge level={item.confirmed ? 'high' : 'medium'} />
      <ChevronRight size={15} className="text-gray-300 shrink-0" />
    </div>
  )
}

export function ExposedRankRow({ asset, onClick }) {
  return (
    <div
      onClick={onClick}
      className="flex items-center gap-4 py-3 border-t border-[#f2ede6] first:border-t-0 cursor-pointer hover:bg-[#faf8f5] transition-colors -mx-2 px-2 rounded-lg"
    >
      <div className="flex-1 min-w-0 flex items-center gap-3">
        <p className="font-mono text-sm text-gray-800 shrink-0">{asset.ip_address}</p>
        <p className="text-xs text-gray-400 truncate">{asset.institution_name || 'Institution inconnue'}</p>
      </div>
      {asset.vulns?.length > 0 && (
        <span className="text-[11px] text-[#8b7355] shrink-0">{asset.vulns.length} CVE</span>
      )}
      <SeverityBadge level={asset.risk_level} />
      <ChevronRight size={15} className="text-gray-300 shrink-0" />
    </div>
  )
}

export function DomainStatusBadge({ asset }) {
  const status = asset.domain_status

  if (status === 'not_found') {
    return (
      <div className="flex items-center gap-1.5 justify-end">
        <XCircle size={12} className="text-red-400 shrink-0" />
        <span className="text-xs text-red-400">domaine non retenu</span>
      </div>
    )
  }
  if (status === 'confirmed' && asset.domain) {
    return (
      <div className="flex items-center gap-1.5 justify-end">
        <CheckCircle2 size={12} className="text-emerald-500 shrink-0" />
        <span className="text-xs font-mono text-gray-500">{asset.domain}</span>
      </div>
    )
  }
  if (asset.domain) {
    return (
      <div className="flex items-center gap-1.5 justify-end">
        <HelpCircle size={12} className="text-amber-400 shrink-0" />
        <span className="text-xs font-mono text-gray-500">{asset.domain}</span>
      </div>
    )
  }
  return <span className="text-xs text-gray-300 italic">domaine inconnu</span>
}

export function InstitutionRow({ asset, onClick }) {
  const Icon = CATEGORY_ICONS[asset.category] || Shield
  return (
    <div
      onClick={onClick}
      className="bg-white rounded-xl border border-[#ede8e3] p-4 flex items-center justify-between gap-3
                 cursor-pointer hover:border-[#c4a882] hover:shadow-sm transition-all"
    >
      <div className="flex items-center gap-3 min-w-0">
        <div className="p-2 rounded-lg bg-[#faf8f5] shrink-0">
          <Icon size={14} className="text-[#8b7355]" />
        </div>
        <div className="min-w-0">
          <p className="text-sm font-medium text-gray-800 truncate">{asset.name}</p>
          <p className="text-xs text-gray-400">{asset.acronym || 'sans sigle'} · {CATEGORY_LABELS[asset.category]}</p>
        </div>
      </div>
      <div className="shrink-0 text-right">
        <DomainStatusBadge asset={asset} />
      </div>
    </div>
  )
}

export function CveDonut({ severity }) {
  const rows = [
    { key: 'critical', count: severity.critical },
    { key: 'high', count: severity.high },
    { key: 'medium', count: severity.medium },
    { key: 'low', count: severity.low },
    { key: 'unknown', count: severity.unknown },
  ]
  const total = rows.reduce((s, r) => s + r.count, 0) || 1
  let acc = 0
  const stops = rows.map(r => {
    const start = (acc / total) * 360
    acc += r.count
    const end = (acc / total) * 360
    return `${SEVERITY[r.key].hex} ${start}deg ${end}deg`
  })
  const gradient = `conic-gradient(${stops.join(', ')})`

  return (
    <div className="flex items-center gap-6">
      <div className="w-28 h-28 rounded-full shrink-0" style={{ background: gradient }} />
      <div className="flex-1 space-y-2">
        {rows.map(r => (
          <div key={r.key} className="flex items-center justify-between text-sm">
            <div className="flex items-center gap-2 text-gray-600">
              <span className={`w-2 h-2 rounded-full ${SEVERITY[r.key].dot}`} />
              {SEVERITY[r.key].label}
            </div>
            <span className="font-bold text-gray-900" style={{ fontFamily: 'Space Grotesk, sans-serif' }}>
              {r.count.toLocaleString('fr-FR')}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}
