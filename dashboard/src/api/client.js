// src/api/client.js
const BASE = '/api'

async function get(path) {
  const res = await fetch(`${BASE}${path}`)
  if (!res.ok) throw new Error(`API error ${res.status}: ${path}`)
  return res.json()
}

export const api = {
  stats:          ()           => get('/stats'),
  health:         ()           => get('/health'),
  metrics:        ()           => get('/metrics'),
  sources:        ()           => get('/sources'),
  threats:        (page = 1)   => get(`/threats?page=${page}&page_size=20`),
  lookupByValue:  (value)      => get(`/indicators/${encodeURIComponent(value)}`),
  indicators:     (params = {}) => {
    const q = new URLSearchParams()
    Object.entries(params).forEach(([k, v]) => {
      if (v !== '' && v !== null && v !== undefined) q.append(k, v)
    })
    return get(`/indicators?${q.toString()}`)
  },
}
