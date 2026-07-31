// src/components/TechInfoPanel.jsx
// Panneau technique repliable, réutilisé sur chaque page pour expliquer sa
// logique métier (fermé par défaut, pour ne pas surcharger la page).
import { useState } from 'react'
import { Info, ChevronDown } from 'lucide-react'

export default function TechInfoPanel({ title = 'Comment ça marche', defaultOpen = false, children }) {
  const [open, setOpen] = useState(defaultOpen)

  return (
    <div className="bg-white rounded-2xl border border-[#ede8e3] overflow-hidden">
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center justify-between gap-3 px-5 py-3.5 text-left hover:bg-[#faf8f5] transition-colors"
      >
        <div className="flex items-center gap-2.5">
          <Info size={15} className="text-[#8b7355]" />
          <span className="text-sm font-medium text-[#2c1810]" style={{ fontFamily: 'Space Grotesk, sans-serif' }}>
            {title}
          </span>
        </div>
        <ChevronDown
          size={15}
          className={`text-[#c4a882] shrink-0 transition-transform duration-200 ${open ? 'rotate-180' : ''}`}
        />
      </button>
      {open && (
        <div className="px-5 pb-4 pt-1 border-t border-[#faf8f5] text-sm text-gray-600 leading-relaxed space-y-2.5">
          {children}
        </div>
      )}
    </div>
  )
}
