// src/components/Navbar.jsx
import { Shield, LayoutDashboard, AlertTriangle, Database, Activity, BarChart2, Radar } from 'lucide-react'

const links = [
  { id: 'overview',   label: 'Overview',   icon: LayoutDashboard },
  { id: 'indicators', label: 'Indicators', icon: AlertTriangle },
  { id: 'threats',    label: 'Threats',    icon: Shield },
  { id: 'analytics',  label: 'Analytics',  icon: BarChart2 },
  { id: 'sources',    label: 'Sources',    icon: Database },
  { id: 'health',     label: 'Health',     icon: Activity },
]

export default function Navbar({ current, onChange }) {
  return (
    <aside
      className="w-56 min-h-screen flex flex-col"
      style={{ backgroundColor: '#faf8f5', fontFamily: 'Inter, sans-serif' }}
    >

      {/* ── Logo ─────────────────────────────────────────────── */}
      <div className="px-5 py-6 border-b border-[#ede8e3]">
        <div className="flex items-center gap-2.5">
          <div className="p-1.5 rounded-lg" style={{ backgroundColor: '#c4a882' }}>
            <Radar size={16} className="text-white" />
          </div>
          <div>
            <p className="text-[#1f1712] text-xs font-bold tracking-widest uppercase"
               style={{ fontFamily: 'Space Grotesk, sans-serif' }}>
              TIP
            </p>
            <p className="text-xs" style={{ color: '#8b7355' }}>ANTIC · v1.0</p>
          </div>
        </div>
      </div>

      {/* ── Navigation ───────────────────────────────────────── */}
      <nav className="flex-1 px-3 py-5 space-y-0.5">
        {links.map(({ id, label, icon: Icon }) => {
          const active = current === id || (id === 'indicators' && current === 'detail') || (id === 'threats' && current === 'threat-detail')
          return (
            <button
              key={id}
              onClick={() => onChange(id)}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm transition-all duration-150 group relative ${
                active
                  ? 'bg-[#c4a882] text-[#faf8f5]'
                  : 'text-[#6b5740] hover:bg-[#2c1810] hover:text-[#c4a882]'
              }`}
            >
              <Icon size={15} />
              <span className="font-medium">{label}</span>
              {active && (
                <div className="absolute right-3 w-1.5 h-1.5 rounded-full bg-[#faf8f5] opacity-40" />
              )}
            </button>
          )
        })}
      </nav>

      {/* ── Séparateur ───────────────────────────────────────── */}
      <div className="mx-4 border-t border-[#ede8e3] mb-4" />

      {/* ── Footer ───────────────────────────────────────────── */}
      <div className="px-5 pb-6">
        <div className="rounded-xl p-3 bg-white border border-[#ede8e3]">
          <p className="text-xs font-semibold text-[#8b7355]">ANTIC</p>
          <p className="text-xs mt-0.5 text-gray-400">Threat Intelligence</p>
          <div className="flex items-center gap-1.5 mt-2">
            <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
            <p className="text-xs text-gray-400">Système opérationnel</p>
          </div>
        </div>
      </div>
    </aside>
  )
}
