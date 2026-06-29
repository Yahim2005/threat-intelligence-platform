// src/components/StatusBadge.jsx
const COLORS = {
  active:      'bg-emerald-100 text-emerald-700',
  expired:     'bg-gray-100 text-gray-500',
  whitelisted: 'bg-blue-100 text-blue-700',
}

export default function StatusBadge({ status }) {
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${COLORS[status] ?? 'bg-gray-100 text-gray-500'}`}>
      {status}
    </span>
  )
}
