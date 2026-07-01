// src/components/Navbar.jsx
import { Shield, LayoutDashboard, AlertTriangle, Database, Radio, Activity, BarChart2 } from 'lucide-react'

const links = [
  { id: 'overview',    label: 'Overview',    icon: LayoutDashboard },
  { id: 'indicators',  label: 'Indicators',  icon: AlertTriangle },
  { id: 'threats',     label: 'Threats',     icon: Shield },
  { id: 'analytics',   label: 'Analytics',   icon: BarChart2 },
  { id: 'sources',     label: 'Sources',     icon: Database },
  { id: 'health',      label: 'Health',      icon: Activity },
]

export default function Navbar({ current, onChange }) {
  return (
    <aside className="w-56 min-h-screen bg-gray-900 flex flex-col">
      {/* Logo */}
      <div className="flex items-center gap-2 px-5 py-6 border-b border-gray-700">
        <Radio size={20} className="text-indigo-400" />
        <span className="text-white font-semibold text-sm tracking-wide">TIP Dashboard</span>
      </div>
      {/* Nav links */}
      <nav className="flex-1 px-3 py-4 space-y-1">
        {links.map(({ id, label, icon: Icon }) => {
          const active = current === id
          return (
            <button
              key={id}
              onClick={() => onChange(id)}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors ${
                active
                  ? 'bg-indigo-600 text-white'
                  : 'text-gray-400 hover:bg-gray-800 hover:text-white'
              }`}
            >
              <Icon size={16} />
              {label}
            </button>
          )
        })}
      </nav>
      {/* Footer */}
      <div className="px-5 py-4 border-t border-gray-700">
        <p className="text-xs text-gray-500">TIP v1.0.0</p>
      </div>
    </aside>
  )
}