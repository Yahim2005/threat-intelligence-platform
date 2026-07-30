// src/pages/Overview.jsx
import { useEffect, useState, useRef } from 'react'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell,
  LineChart, Line, CartesianGrid, Area, AreaChart
} from 'recharts'
import { ArrowUpRight, Download, TrendingUp, Shield, Database, Activity, AlertTriangle, MapPin } from 'lucide-react'
import { api, getAuthToken } from '../api/client'
import AlertsPanel from '../components/AlertsPanel'
import ThreatGlobe from '../components/ThreatGlobe'
import TechInfoPanel from '../components/TechInfoPanel'
const TYPE_COLORS = ['#8b7355','#c4a882','#d4b896','#a0845c','#6b5740','#e8d5b7','#bfa07a']
const TLP_COLORS  = { CLEAR: '#9ca3af', GREEN: '#40916c', AMBER: '#f59e0b', AMBER_STRICT: '#f97316', RED: '#ef4444' }

// ── Compteur animé ────────────────────────────────────────────────
function AnimatedNumber({ value }) {
  const [display, setDisplay] = useState(0)
  const ref = useRef(null)

  useEffect(() => {
    if (!value || typeof value !== 'number') return
    const duration = 1200
    const steps = 40
    const increment = value / steps
    let current = 0
    const timer = setInterval(() => {
      current += increment
      if (current >= value) {
        setDisplay(value)
        clearInterval(timer)
      } else {
        setDisplay(Math.floor(current))
      }
    }, duration / steps)
    return () => clearInterval(timer)
  }, [value])

  return <span>{display.toLocaleString()}</span>
}

// ── Stat Card ─────────────────────────────────────────────────────
function StatCard({ label, value, sub, icon: Icon, accent, onClick }) {
  return (
    <div
      onClick={onClick}
      className={`
      rounded-2xl p-6 flex flex-col justify-between min-h-[150px]
      transition-all duration-200 ${onClick ? 'cursor-pointer' : 'cursor-default'}
      hover:-translate-y-1 hover:shadow-lg
      ${accent
        ? 'bg-[#2c1810] text-white'
        : 'bg-white border border-[#ede8e3] hover:border-[#c4a882]'
      }
    `}>
      <div className="flex items-start justify-between">
        <div className={`p-2 rounded-xl ${accent ? 'bg-white/10' : 'bg-[#faf8f5]'}`}>
          <Icon size={16} className={accent ? 'text-[#e8d5b7]' : 'text-[#8b7355]'} />
        </div>
        <div className={`p-1.5 rounded-full border transition-colors ${
          accent ? 'border-white/20 text-white/60' : 'border-[#ede8e3] text-[#c4a882]'
        }`}>
          <ArrowUpRight size={12} />
        </div>
      </div>
      <div>
        <p className={`text-xs font-medium uppercase tracking-wider mb-1 ${
          accent ? 'text-[#e8d5b7]' : 'text-[#8b7355]'
        }`}>{label}</p>
        <p className={`text-3xl font-bold tracking-tight ${accent ? 'text-white' : 'text-gray-900'}`}
           style={{ fontFamily: 'Space Grotesk, sans-serif' }}>
          {typeof value === 'number' ? <AnimatedNumber value={value} /> : value}
        </p>
        {sub && (
          <p className={`text-xs mt-1 ${accent ? 'text-white/50' : 'text-gray-400'}`}>{sub}</p>
        )}
      </div>
    </div>
  )
}

// ── Tooltip custom ────────────────────────────────────────────────
function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-white border border-[#ede8e3] rounded-xl px-3 py-2 shadow-xl text-xs">
      <p className="text-[#8b7355] mb-0.5 font-medium">{label}</p>
      <p className="font-bold text-gray-800">{payload[0].value?.toLocaleString()}</p>
    </div>
  )
}

// ── Bouton export ─────────────────────────────────────────────────
function ExportButton({ format, label, exporting, onClick }) {
  const isLoading = exporting === format
  return (
    <button
      onClick={() => onClick(format)}
      disabled={exporting !== null}
      className="flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-lg border border-[#ede8e3] bg-white text-[#8b7355] hover:bg-[#faf8f5] hover:border-[#c4a882] disabled:opacity-40 transition-all"
    >
      <Download size={11} className={isLoading ? 'animate-bounce' : ''} />
      {isLoading ? 'Export…' : label}
    </button>
  )
}

export default function Overview({ onOpenDetail, onNavigate }) {
  const [isMobile, setIsMobile] = useState(window.innerWidth < 768)
  useEffect(() => {
    const handler = () => setIsMobile(window.innerWidth < 768)
    window.addEventListener('resize', handler)
    return () => window.removeEventListener('resize', handler)
  }, [])
  const [stats,     setStats]     = useState(null)
  const [trends,    setTrends]    = useState([])
  const [cameroon,  setCameroon]  = useState(null)
  const [loading,   setLoading]   = useState(true)
  const [error,     setError]     = useState(null)
  const [exporting, setExporting] = useState(null)

  useEffect(() => {
    Promise.all([api.stats(), api.trends(30), api.cameroonOverview()])
      .then(([s, t, c]) => { setStats(s); setTrends(t); setCameroon(c) })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  function downloadExport(format) {
    // Authentifié par le token JWT de la session dashboard (même mécanisme
    // que le reste de l'app, voir getAuthToken/authHeaders dans api/client.js)
    // -- pas une clé API, qui n'a plus lieu d'être exposée côté navigateur.
    const filenames = { stix: 'export.json', csv: 'export.csv', blocklist: 'blocklist.txt' }
    const urls = { stix: '/api/export/stix', csv: '/api/export/csv', blocklist: '/api/export/blocklist' }
    setExporting(format)
    fetch(urls[format], { headers: { Authorization: `Bearer ${getAuthToken()}` } })
      .then(res => {
        if (!res.ok) throw new Error(`Échec de l'export (${res.status})`)
        return res.blob()
      })
      .then(blob => {
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = filenames[format]
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
        URL.revokeObjectURL(url)
      })
      .catch(console.error)
      .finally(() => setExporting(null))
  }

  if (loading) return (
    <div className="flex flex-col items-center justify-center h-64 gap-3">
      <div className="w-8 h-8 border-2 border-[#c4a882] border-t-transparent rounded-full animate-spin" />
      <p className="text-sm text-gray-400">Chargement des données…</p>
    </div>
  )
  if (error)  return <div className="text-red-500 p-6">Erreur : {error}</div>
  if (!stats) return null

  const typeData = Object.entries(stats.indicators_by_type ?? {})
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value)

  const tlpData = Object.entries(stats.indicators_by_tlp ?? {})
    .map(([name, value]) => ({ name, value }))

  const trendsFormatted = trends.map(d => ({
    ...d,
    label: d.date.slice(5).replace('-', '/'),
  }))

  return (
    <div className="space-y-6" style={{ fontFamily: 'Inter, sans-serif' }}>

      {/* ── Banner ANTIC ─────────────────────────────────────── */}
      <div className="rounded-2xl overflow-hidden border border-[#ede8e3] shadow-sm">
        <img
          src="/antic-banner.png"
          alt="ANTIC"
          className="w-full object-cover"
          style={{ height: '110px', objectPosition: 'center' }}
        />
        <div className="px-6 py-3 bg-[#faf8f5] border-t border-[#ede8e3] flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <img src="/Logo-Antic.png" alt="ANTIC" className="h-9 w-auto object-contain" />
            <div>
              <p className="text-xs font-semibold text-[#8b7355] uppercase tracking-widest">
                Threat Intelligence Platform
              </p>
              <p className="text-xs text-gray-400 mt-0.5">
                Sécurité Numérique · Souveraineté Digitale
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs text-gray-400 mr-1">Exporter :</span>
            <ExportButton format="stix"      label="STIX"      exporting={exporting} onClick={downloadExport} />
            <ExportButton format="csv"       label="CSV"       exporting={exporting} onClick={downloadExport} />
            <ExportButton format="blocklist" label="Blocklist" exporting={exporting} onClick={downloadExport} />
          </div>
        </div>
      </div>

      <TechInfoPanel>
        <p>
          Cette page affiche les indicateurs clés agrégés de toute la plateforme (nombre total
          d'IOCs actifs, clusters de menaces, sources de collecte) et un globe 3D géolocalisant
          les IOCs de type IP via GeoIP.
        </p>
        <p>
          Les boutons d'export (STIX 2.1, CSV, Blocklist) téléchargent un instantané complet des
          indicateurs actifs au-dessus d'un seuil de confidence — authentifiés par votre session
          (JWT), séparément du système de clés API réservé aux partenaires externes.
        </p>
      </TechInfoPanel>

      {/* ── Surveillance nationale ──────────────────────────────── */}
      {cameroon && (
        <div
          onClick={() => onNavigate('cameroon')}
          className="rounded-2xl border border-[#2c1810]/10 overflow-hidden cursor-pointer
                     hover:shadow-lg hover:-translate-y-0.5 transition-all duration-200"
          style={{ background: 'linear-gradient(135deg, #2c1810 0%, #4a3020 55%, #6b5740 100%)' }}
        >
          <div className="px-6 py-5 flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-4">
              <div className="p-3 rounded-xl bg-white/10 shrink-0">
                <MapPin size={20} className="text-[#e8d5b7]" />
              </div>
              <div>
                <p className="text-xs font-semibold text-[#e8d5b7] uppercase tracking-widest mb-1">
                  Surveillance nationale
                </p>
                <h2 className="text-lg font-bold text-white"
                    style={{ fontFamily: 'Space Grotesk, sans-serif' }}>
                  {cameroon.total_monitored_assets} institutions surveillées
                </h2>
                <p className="text-xs text-white/50 mt-0.5">
                  Ministères, banques, opérateurs télécom et sociétés publiques
                </p>
              </div>
            </div>

            <div className="flex items-center gap-6">
              <div className="text-center">
                <p className="text-2xl font-bold text-white" style={{ fontFamily: 'Space Grotesk, sans-serif' }}>
                  {cameroon.typosquat_confirmed}
                </p>
                <p className="text-[10px] text-white/50 uppercase tracking-wider">Typosquats confirmés</p>
              </div>
              <div className="w-px h-10 bg-white/15" />
              <div className="text-center">
                <p className="text-2xl font-bold text-white" style={{ fontFamily: 'Space Grotesk, sans-serif' }}>
                  {cameroon.exposed_high_risk}
                </p>
                <p className="text-[10px] text-white/50 uppercase tracking-wider">IPs à haut risque</p>
              </div>
              <div className="w-px h-10 bg-white/15" />
              <div className="text-center flex flex-col items-center">
                <div className="flex items-center gap-1">
                  <AlertTriangle size={14} className="text-[#e8b896]" />
                  <p className="text-2xl font-bold text-white" style={{ fontFamily: 'Space Grotesk, sans-serif' }}>
                    {cameroon.typosquat_confirmed + cameroon.typosquat_potential + cameroon.exposed_high_risk + cameroon.ct_findings}
                  </p>
                </div>
                <p className="text-[10px] text-white/50 uppercase tracking-wider">Signaux actifs</p>
              </div>
              <button className="flex items-center gap-1.5 px-4 py-2 text-xs font-medium rounded-xl
                                 bg-white/10 text-white hover:bg-white/20 transition-all shrink-0">
                Voir le détail <ArrowUpRight size={13} />
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Titre ────────────────────────────────────────────── */}
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900"
              style={{ fontFamily: 'Space Grotesk, sans-serif' }}>
            Overview
          </h1>
          <p className="text-sm text-gray-400 mt-0.5">
            {new Date().toLocaleDateString('fr-FR', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}
          </p>
        </div>
      </div>

      {/* ── Globe 3D ─────────────────────────────────────────── */}
      {/* ── Globe 3D ─────────────────────────────────────────── */}
      <div className="bg-white rounded-2xl border border-[#ede8e3] p-6 flex flex-row items-center gap-6">
        <div className="flex-1 min-w-0">
          <p className="text-xs text-[#8b7355] uppercase tracking-widest font-semibold mb-1">
            Surveillance mondiale
          </p>
          <h2 className="text-xl font-bold text-gray-900 mb-2"
              style={{ fontFamily: 'Space Grotesk, sans-serif' }}>
            Réseau de menaces actif
          </h2>
          <p className="text-sm text-gray-400 leading-relaxed">
            La plateforme surveille en continu {stats.total_indicators?.toLocaleString()} indicateurs 
            de compromission issus de {stats.total_sources} sources OSINT publiques.
          </p>
          <div className="flex items-center gap-4 mt-4">
            <div>
              <p className="text-2xl font-bold text-gray-900"
                 style={{ fontFamily: 'Space Grotesk, sans-serif' }}>
                {stats.total_threats?.toLocaleString()}
              </p>
              <p className="text-xs text-gray-400">Clusters détectés</p>
            </div>
            <div className="w-px h-8 bg-[#ede8e3]" />
            <div>
              <p className="text-2xl font-bold text-gray-900"
                 style={{ fontFamily: 'Space Grotesk, sans-serif' }}>
                {stats.total_sources}
              </p>
              <p className="text-xs text-gray-400">Sources actives</p>
            </div>
            <div className="w-px h-8 bg-[#ede8e3]" />
            <div>
              <p className="text-2xl font-bold text-gray-900"
                 style={{ fontFamily: 'Space Grotesk, sans-serif' }}>
                {stats.avg_confidence ? Math.round(stats.avg_confidence) : '—'}
              </p>
              <p className="text-xs text-gray-400">Score moyen</p>
            </div>
          </div>
        </div>
        <div className="w-96 h-80 shrink-0">
          {isMobile ? (
            <div className="flex items-center justify-center h-48 text-gray-400 text-sm italic">🌐 Globe 3D disponible sur desktop</div>
          ) : (
            <ThreatGlobe height={300} />
          )}
        </div>
      </div>

      {/* ── Stat cards ───────────────────────────────────────── */}
      <div className="grid grid-cols-2 xl:grid-cols-4 gap-4">
        <StatCard label="Total IOCs"     value={stats.total_indicators}  sub="Tous types confondus"  icon={Database}  accent onClick={() => onNavigate('indicators')} />
        <StatCard label="IOCs actifs"    value={stats.active_indicators} sub="Statut : active"       icon={Activity}        onClick={() => onNavigate('indicators')} />
        <StatCard label="Threats"        value={stats.total_threats}     sub="Clusters corrélés"     icon={Shield}          onClick={() => onNavigate('threats')} />
        <StatCard label="Confidence moy" value={stats.avg_confidence ? Math.round(stats.avg_confidence) : 0} sub="Score moyen /100" icon={TrendingUp} onClick={() => onNavigate('analytics')} />
      </div>

      {/* ── Section explicative ───────────────────────────────── */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-5">
        {[
          {
            emoji: '🛰️',
            title: 'Collecte OSINT automatique',
            desc: 'Agrégation continue d\'indicateurs de compromission (IOCs) depuis 10+ sources publiques : abuse.ch, AlienVault OTX, CISA KEV, Spamhaus, NVD et d\'autres. Chaque collecte est journalisée et traçable.',
            items: ['IPs malveillantes', 'Domaines suspects', 'Hashes de malwares', 'CVEs exploitées'],
            accent: false,
          },
          {
            emoji: '⚡',
            title: 'Analyse & Scoring',
            desc: 'Chaque IOC est normalisé, enrichi (GeoIP, DNS, WHOIS) puis scoré via un algorithme à 7 composantes : fiabilité de la source, corroboration, diversité, type, récence, tags malware et réputation externe.',
            items: ['Score 0–100', 'Enrichissement GeoIP', 'Tags automatiques', 'MITRE ATT&CK'],
            accent: false,
          },
          {
            emoji: '🔗',
            title: 'Corrélation',
            desc: 'Le moteur de corrélation regroupe les IOCs liés en clusters de menaces (Threats), révélant des campagnes coordonnées plutôt que des indicateurs isolés.',
            items: ['Clusters de menaces', 'Graphe de relations', 'Score Cameroun agrégé'],
            accent: false,
          },
          {
            emoji: '🛡️',
            title: 'Surveillance nationale',
            desc: 'Trois modules dédiés surveillent activement les institutions camerounaises : typosquatting de leurs domaines officiels, certificats SSL suspects, et surface d\'attaque exposée sur leurs plages IP.',
            items: ['Typosquatting (dnstwist)', 'Certificate Transparency', 'Surface d\'attaque exposée'],
            accent: true,
          },
        ].map(({ emoji, title, desc, items, accent }) => (
          <div key={title}
               className={`rounded-2xl border p-6 hover:shadow-md transition-all duration-200 ${
                 accent
                   ? 'bg-[#2c1810] border-[#2c1810] hover:border-[#4a3020]'
                   : 'bg-white border-[#ede8e3] hover:border-[#c4a882]'
               }`}>
            <div className="text-3xl mb-3">{emoji}</div>
            <h3 className={`text-sm font-bold mb-2 ${accent ? 'text-white' : 'text-gray-900'}`}
                style={{ fontFamily: 'Space Grotesk, sans-serif' }}>
              {title}
            </h3>
            <p className={`text-xs leading-relaxed mb-4 ${accent ? 'text-white/60' : 'text-gray-400'}`}>{desc}</p>
            <div className="space-y-1.5">
              {items.map(item => (
                <div key={item} className="flex items-center gap-2">
                  <div className={`w-1.5 h-1.5 rounded-full shrink-0 ${accent ? 'bg-[#e8d5b7]' : 'bg-[#c4a882]'}`} />
                  <span className={`text-xs font-medium ${accent ? 'text-[#e8d5b7]' : 'text-[#8b7355]'}`}>{item}</span>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>

      {/* ── Graphiques ───────────────────────────────────────── */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-5">

        <div className="bg-white rounded-2xl border border-[#ede8e3] p-6 hover:border-[#c4a882] transition-colors">
          <h2 className="text-sm font-semibold text-gray-800 mb-0.5"
              style={{ fontFamily: 'Space Grotesk, sans-serif' }}>IOCs par type</h2>
          <p className="text-xs text-gray-400 mb-4">Répartition par catégorie</p>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={typeData} margin={{ top: 0, right: 10, left: -20, bottom: 0 }} barCategoryGap="35%">
              <XAxis dataKey="name" tick={{ fontSize: 11, fill: '#9ca3af' }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 11, fill: '#9ca3af' }} axisLine={false} tickLine={false} />
              <Tooltip content={<CustomTooltip />} cursor={{ fill: '#faf8f5' }} />
              <Bar dataKey="value" radius={[6, 6, 0, 0]}>
                {typeData.map((_, i) => <Cell key={i} fill={TYPE_COLORS[i % TYPE_COLORS.length]} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="bg-white rounded-2xl border border-[#ede8e3] p-6 hover:border-[#c4a882] transition-colors">
          <h2 className="text-sm font-semibold text-gray-800 mb-0.5"
              style={{ fontFamily: 'Space Grotesk, sans-serif' }}>IOCs par TLP</h2>
          <p className="text-xs text-gray-400 mb-4">Niveau de confidentialité</p>
          <ResponsiveContainer width="100%" height={220}>
            <PieChart>
              <Pie data={tlpData} dataKey="value" nameKey="name"
                   cx="50%" cy="50%" outerRadius={85} innerRadius={50}
                   paddingAngle={3}
                   label={({ name, percent }) => `${name} ${(percent*100).toFixed(0)}%`}
                   labelLine={false}>
                {tlpData.map((entry, i) => <Cell key={i} fill={TLP_COLORS[entry.name] ?? '#9ca3af'} />)}
              </Pie>
              <Tooltip content={<CustomTooltip />} />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* ── Tendance ─────────────────────────────────────────── */}
      <div className="bg-white rounded-2xl border border-[#ede8e3] p-6 hover:border-[#c4a882] transition-colors">
        <h2 className="text-sm font-semibold text-gray-800 mb-0.5"
            style={{ fontFamily: 'Space Grotesk, sans-serif' }}>Ingestion sur 30 jours</h2>
        <p className="text-xs text-gray-400 mb-4">Nombre d'IOCs nouveaux créés par jour</p>
        <ResponsiveContainer width="100%" height={200}>
          <AreaChart data={trendsFormatted} margin={{ top: 0, right: 10, left: -20, bottom: 0 }}>
            <defs>
              <linearGradient id="trendGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%"  stopColor="#c4a882" stopOpacity={0.2} />
                <stop offset="95%" stopColor="#c4a882" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#f5f0eb" vertical={false} />
            <XAxis dataKey="label" tick={{ fontSize: 11, fill: '#9ca3af' }} axisLine={false} tickLine={false} interval="preserveStartEnd" />
            <YAxis tick={{ fontSize: 11, fill: '#9ca3af' }} axisLine={false} tickLine={false} />
            <Tooltip content={<CustomTooltip />} />
            <Area type="monotone" dataKey="count" stroke="#8b7355" strokeWidth={2}
                  fill="url(#trendGrad)" dot={false} activeDot={{ r: 5, fill: '#8b7355', strokeWidth: 0 }} />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* ── Alertes Cameroun ───────────────────────────────────── */}
      <AlertsPanel onOpenDetail={onOpenDetail} cameroonOnly />

    </div>
  )
}