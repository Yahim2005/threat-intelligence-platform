// src/api/client.js
const BASE = import.meta.env.VITE_API_BASE_URL
  ? `${import.meta.env.VITE_API_BASE_URL}`
  : '/api'

const TOKEN_STORAGE_KEY = 'tip-auth-token'

// Le token JWT est gardé en mémoire + localStorage. AuthContext appelle
// setAuthToken() au login/logout ; le client n'a pas besoin de React.
let authToken = localStorage.getItem(TOKEN_STORAGE_KEY) || null

export function setAuthToken(token) {
  authToken = token
  if (token) localStorage.setItem(TOKEN_STORAGE_KEY, token)
  else localStorage.removeItem(TOKEN_STORAGE_KEY)
}

export function getAuthToken() {
  return authToken
}

function authHeaders() {
  const headers = {}
  if (authToken) headers['Authorization'] = `Bearer ${authToken}`
  return headers
}

async function get(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, { headers: authHeaders(), ...options })
  if (!res.ok) throw new Error(`API error ${res.status}: ${path}`)
  return res.json()
}

async function send(method, path, body) {
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify(body),
  })
  const data = await res.json().catch(() => null)
  if (!res.ok) {
    const message = data?.detail ?? `API error ${res.status}: ${path}`
    throw new Error(typeof message === 'string' ? message : JSON.stringify(message))
  }
  return data
}

export const api = {
  stats:          ()           => get('/stats'),
  cameroonOverview: ()         => get('/cameroon/overview'),
  exposedAssets:  (params={})  => get(`/exposed-assets?${new URLSearchParams(params)}`),
  monitoredAssets: (params={}) => get(`/monitored-assets?${new URLSearchParams(params)}`),
  createMonitoredAsset: (payload) => send('POST', '/monitored-assets', payload),
  updateMonitoredAsset: (id, payload) => send('PATCH', `/monitored-assets/${id}`, payload),
  listAdminJobs: () => get('/admin/jobs'),
  runAdminJob: (jobName) => send('POST', `/admin/jobs/${jobName}/run`, {}),
  listApiClients: () => get('/admin/api-clients'),
  createApiClient: (payload) => send('POST', '/admin/api-clients', payload),
  revokeApiClient: (id) => send('POST', `/admin/api-clients/${id}/revoke`, {}),
  regenerateApiClient: (id) => send('POST', `/admin/api-clients/${id}/regenerate`, {}),
  listEmailRecipients: () => get('/admin/email-recipients'),
  createEmailRecipient: (payload) => send('POST', '/admin/email-recipients', payload),
  revokeEmailRecipient: (id) => send('POST', `/admin/email-recipients/${id}/revoke`, {}),
  emailDigestStatus: () => get('/admin/email-digest/status'),
  sendEmailDigestNow: () => send('POST', '/admin/email-digest/send-now', {}),
  cameroonTimeline: (days=30) => get(`/cameroon/timeline?days=${days}`),
  institutionsRanked: () => get('/cameroon/institutions/ranked'),
  vulnSeverity: () => get('/cameroon/vuln-severity'),
  reportFalsePositive: (payload) => send('POST', '/cameroon/report-false-positive', payload),
  sectorBreakdown: () => get('/cameroon/sector-breakdown'),
  topPorts: (limit=10) => get(`/cameroon/top-ports?limit=${limit}`),
  related:        (value)      => get(`/indicators/${encodeURIComponent(value)}/related`),
  timeline:       (value, days = 30) => get(`/indicators/${encodeURIComponent(value)}/timeline?days=${days}`),
  alerts: (threshold = 75, hours = 168, cameroonOnly = false) => get(`/alerts?threshold=${threshold}&hours=${hours}${cameroonOnly ? '&cameroon_only=true' : ''}`),
  trends:         (days = 30)  => get(`/stats/trends?days=${days}`),
  health:         ()           => get('/health'),
  metrics:        ()           => get('/metrics'),
  sources:        ()           => get('/sources'),
  collectionRuns: (limit = 50) => get(`/collection-runs?limit=${limit}`),
  topSources:             (limit = 10) => get(`/analytics/top-sources?limit=${limit}`),
  topTags:                (limit = 10) => get(`/analytics/top-tags?limit=${limit}`),
  confidenceDistribution: ()           => get(`/analytics/confidence-distribution`),
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
  submitIndicator: (payload) => send('POST', '/indicators', payload),
  register: (payload) => send('POST', '/auth/register', payload),
  login:    (payload) => send('POST', '/auth/login', payload),
  me:       ()        => get('/auth/me'),
}
