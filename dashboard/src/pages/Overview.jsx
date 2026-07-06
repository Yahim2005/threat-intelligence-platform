// src/pages/Overview.jsx
import { useEffect, useState, useRef } from 'react'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell,
  LineChart, Line, CartesianGrid, Area, AreaChart
} from 'recharts'
import { ArrowUpRight, Download, TrendingUp, Shield, Database, Activity } from 'lucide-react'
import { api } from '../api/client'
import AlertsPanel from '../components/AlertsPanel'
import ThreatGlobe from '../components/ThreatGlobe'
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
  const [stats,     setStats]     = useState(null)
  const [trends,    setTrends]    = useState([])
  const [loading,   setLoading]   = useState(true)
  const [error,     setError]     = useState(null)
  const [exporting, setExporting] = useState(null)

  useEffect(() => {
    Promise.all([api.stats(), api.trends(30)])
      .then(([s, t]) => { setStats(s); setTrends(t) })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  function downloadExport(format) {
    const apiKey = import.meta.env.VITE_API_KEY ?? ''
    const filenames = { stix: 'export.json', csv: 'export.csv', blocklist: 'blocklist.txt' }
    const urls = { stix: '/api/export/stix', csv: '/api/export/csv', blocklist: '/api/export/blocklist' }
    setExporting(format)
    fetch(urls[format], { headers: { 'X-API-Key': apiKey } })
      .then(res => res.blob())
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
          {window.innerWidth >= 768 ? {isMobile ? (
          <div className="flex items-center justify-center h-48 text-gray-400 text-sm italic">🌐 Globe 3D disponible sur desktop</div>
        ) : (
          <ThreatGlobe height={300} />
        )} : (
  <div className="flex items-center justify-center h-48 text-gray-400 text-sm">
    🌐 Globe 3D disponible sur desktop
  </div>
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
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-5">
        {[
          {
            emoji: '🛰️',
            title: 'Collecte OSINT automatique',
            desc: 'La plateforme agrège en continu des indicateurs de compromission (IOCs) depuis 10+ sources publiques : abuse.ch, AlienVault OTX, CISA KEV, Spamhaus, NVD et d\'autres. Chaque collecte est journalisée et traçable.',
            items: ['IPs malveillantes', 'Domaines suspects', 'Hashes de malwares', 'CVEs exploitées'],
          },
          {
            emoji: '⚡',
            title: 'Analyse & Scoring',
            desc: 'Chaque IOC est normalisé, enrichi (GeoIP, DNS, WHOIS) puis scoré via un algorithme à 7 composantes : fiabilité de la source, corroboration, diversité, type, récence, tags malware et réputation externe.',
            items: ['Score 0–100', 'Enrichissement GeoIP', 'Tags automatiques', 'MITRE ATT&CK'],
          },
          {
            emoji: '🔗',
            title: 'Corrélation & Alertes',
            desc: 'Le moteur de corrélation regroupe les IOCs liés en clusters de menaces (Threats). Les IOCs haute confiance déclenchent des alertes visibles en temps réel sur ce dashboard.',
            items: ['Clusters de menaces', 'Graphe de relations', 'Alertes temps réel', 'Export STIX/CSV'],
          },
        ].map(({ emoji, title, desc, items }) => (
          <div key={title}
               className="bg-white rounded-2xl border border-[#ede8e3] p-6 hover:border-[#c4a882] hover:shadow-md transition-all duration-200">
            <div className="text-3xl mb-3">{emoji}</div>
            <h3 className="text-sm font-bold text-gray-900 mb-2"
                style={{ fontFamily: 'Space Grotesk, sans-serif' }}>
              {title}
            </h3>
            <p className="text-xs text-gray-400 leading-relaxed mb-4">{desc}</p>
            <div className="space-y-1.5">
              {items.map(item => (
                <div key={item} className="flex items-center gap-2">
                  <div className="w-1.5 h-1.5 rounded-full bg-[#c4a882] shrink-0" />
                  <span className="text-xs text-[#8b7355] font-medium">{item}</span>
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

      {/* ── Alertes ───────────────────────────────────────────── */}
      <AlertsPanel onOpenDetail={onOpenDetail} />

    </div>
  )
}