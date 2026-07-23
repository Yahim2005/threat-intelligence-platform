// src/components/DetailModal.jsx
// Overlay générique de détail — réutilisé pour institutions, typosquats,
// IPs exposées sur la page Cameroun.
import { X } from 'lucide-react'

export default function DetailModal({ title, subtitle, onClose, children }) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-2xl shadow-2xl w-full max-w-xl max-h-[85vh] overflow-y-auto"
        onClick={e => e.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-3 px-6 py-5 border-b border-[#ede8e3] sticky top-0 bg-white">
          <div className="min-w-0">
            <h2 className="text-base font-bold text-gray-900 truncate"
                style={{ fontFamily: 'Space Grotesk, sans-serif' }}>
              {title}
            </h2>
            {subtitle && <p className="text-xs text-gray-400 mt-0.5">{subtitle}</p>}
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-50 shrink-0"
          >
            <X size={16} />
          </button>
        </div>
        <div className="px-6 py-5">
          {children}
        </div>
      </div>
    </div>
  )
}
