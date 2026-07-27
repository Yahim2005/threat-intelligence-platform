// src/lib/severity.js
//
// Système de sévérité unifié — utilisé sur TOUTE l'application
// (Cameroun, Overview, Indicators, Analytics) pour que le code couleur
// d'un niveau de risque soit strictement identique partout.

export const SEVERITY = {
  critical: {
    label: 'Critique',
    dot: 'bg-red-700',
    badge: 'bg-red-700 text-white border-red-700',
    hex: '#7a1f1f',
  },
  high: {
    label: 'Élevé',
    dot: 'bg-red-500',
    badge: 'bg-red-50 text-red-600 border-red-200',
    hex: '#ef4444',
  },
  medium: {
    label: 'Modéré',
    dot: 'bg-amber-400',
    badge: 'bg-amber-50 text-amber-600 border-amber-200',
    hex: '#f59e0b',
  },
  low: {
    label: 'Faible',
    dot: 'bg-gray-300',
    badge: 'bg-gray-50 text-gray-500 border-gray-200',
    hex: '#9ca3af',
  },
  info: {
    label: 'Info',
    dot: 'bg-gray-300',
    badge: 'bg-gray-50 text-gray-500 border-gray-200',
    hex: '#9ca3af',
  },
  unknown: {
    label: 'Inconnu',
    dot: 'bg-[#c4a882]',
    badge: 'bg-[#faf8f5] text-[#8b7355] border-[#c4a882] border-dashed',
    hex: '#c4a882',
  },
}

export function severityFor(level) {
  return SEVERITY[level] || SEVERITY.unknown
}

// Classe un score de risque composite d'institution (voir /cameroon/institutions/ranked)
export function levelForRiskScore(score) {
  if (score >= 500) return 'critical'
  if (score >= 100) return 'high'
  if (score >= 50) return 'medium'
  return 'low'
}

// Classe un score de confidence IOC (0-100) - seuils cohérents avec le
// RiskBadge de Lookup.jsx : >=75 menace confirmée, >=40 suspect, sinon faible.
export function levelForConfidence(score) {
  if (score == null) return 'unknown'
  if (score >= 75) return 'high'
  if (score >= 40) return 'medium'
  return 'low'
}
