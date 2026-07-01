// src/api/client.js
const BASE = '/api'

async function get(path) {
  const res = await fetch(`${BASE}${path}`)
  if (!res.ok) throw new Error(`API error ${res.status}: ${path}`)
  return res.json()
}

export const api = {
  stats:          ()           => get('/stats'),
  related:        (value)      => get(`/indicators/${encodeURIComponent(value)}/related`),
  timeline:       (value, days = 30) => get(`/indicators/${encodeURIComponent(value)}/timeline?days=${days}`),
  alerts: (threshold = 75, hours = 168) => get(`/alerts?threshold=${threshold}&hours=${hours}`),
  trends:         (days = 30)  => get(`/stats/trends?days=${days}`),
  health:         ()           => get('/health'),
  metrics:        ()           => get('/metrics'),
  sources:        ()           => get('/sources'),
  threats:        (page = 1)   => get(`/threats?page=${page}&page_size=20`),
  lookupByValue:  (value)      => get(`/indicators/${encodeURIComponent(value)}`),
  threatDetail: (id) => get(`/threats/${id}`),
  indicators:     (params = {}) => {
    const q = new URLSearchParams()
    Object.entries(params).forEach(([k, v]) => {
      if (v !== '' && v !== null && v !== undefined) q.append(k, v)
    })
    return get(`/indicators?${q.toString()}`)
  },
}
