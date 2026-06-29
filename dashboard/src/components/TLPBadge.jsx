// src/components/TLPBadge.jsx
const COLORS = {
  CLEAR:        'bg-gray-100 text-gray-700',
  GREEN:        'bg-green-100 text-green-700',
  AMBER:        'bg-amber-100 text-amber-700',
  AMBER_STRICT: 'bg-orange-100 text-orange-700',
  RED:          'bg-red-100 text-red-700',
}

export default function TLPBadge({ tlp }) {
  const label = tlp ?? 'CLEAR'
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${COLORS[label] ?? COLORS.CLEAR}`}>
      TLP:{label.replace('_', '+')}
    </span>
  )
}
