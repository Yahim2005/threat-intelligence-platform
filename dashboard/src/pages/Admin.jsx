// src/pages/Admin.jsx
// Interface d'administration du referentiel institutionnel (monitored_assets),
// pour permettre a une equipe non technique de gerer les institutions
// surveillees sans passer par des scripts Python en ligne de commande.
import { useEffect, useState, useMemo } from 'react'
import { Plus, X, Search, ChevronLeft, ChevronRight, Trash2, Copy, AlertTriangle, RefreshCw, Send, Play } from 'lucide-react'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'
import TechInfoPanel from '../components/TechInfoPanel'

const CATEGORY_LABELS = {
  ministry: 'Ministère',
  bank: 'Banque',
  telecom: 'Télécom / ISP',
  public_company: 'Société publique',
  institution: 'Institution',
}
const DOMAIN_STATUS_LABELS = {
  confirmed: 'Confirmé',
  unconfirmed: 'À confirmer',
  not_found: 'Non retenu',
}
const PAGE_SIZE = 20

function AccessDenied() {
  return (
    <div className="flex flex-col items-center justify-center py-24 text-center gap-2">
      <p className="text-lg font-semibold text-[#2c1810]" style={{ fontFamily: 'Space Grotesk, sans-serif' }}>
        Accès réservé aux administrateurs
      </p>
      <p className="text-sm text-gray-400">
        Connectez-vous avec un compte admin pour gérer le référentiel.
      </p>
    </div>
  )
}

function StatusPill({ status }) {
  const styles = {
    confirmed: 'bg-emerald-50 text-emerald-600 border-emerald-200',
    unconfirmed: 'bg-amber-50 text-amber-600 border-amber-200',
    not_found: 'bg-red-50 text-red-500 border-red-200',
  }
  return (
    <span className={`text-[10px] px-2 py-0.5 rounded-full border font-medium ${styles[status] || styles.unconfirmed}`}>
      {DOMAIN_STATUS_LABELS[status] || status}
    </span>
  )
}

const EMPTY_FORM = {
  name: '', acronym: '', category: 'institution', domain: '',
  domain_status: 'unconfirmed', asn: '', known_aliases: [], verification_note: '',
  active: true,
}

function EditModal({ asset, onClose, onSaved }) {
  const isNew = !asset?.id
  const [form, setForm] = useState(asset ? {
    name: asset.name || '',
    acronym: asset.acronym || '',
    category: asset.category || 'institution',
    domain: asset.domain || '',
    domain_status: asset.domain_status || 'unconfirmed',
    asn: asset.asn || '',
    known_aliases: asset.known_aliases || [],
    verification_note: asset.verification_note || '',
    active: asset.active !== false,
  } : EMPTY_FORM)
  const [aliasInput, setAliasInput] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)

  function addAlias() {
    const v = aliasInput.trim().toLowerCase()
    if (!v || form.known_aliases.includes(v)) return
    setForm(f => ({ ...f, known_aliases: [...f.known_aliases, v] }))
    setAliasInput('')
  }
  function removeAlias(alias) {
    setForm(f => ({ ...f, known_aliases: f.known_aliases.filter(a => a !== alias) }))
  }

  async function save() {
    if (!form.name.trim()) {
      setError('Le nom est obligatoire.')
      return
    }
    setSaving(true)
    setError(null)
    try {
      const payload = {
        ...form,
        asn: form.asn ? parseInt(form.asn, 10) : null,
        domain: form.domain.trim() || null,
        acronym: form.acronym.trim() || null,
        verification_note: form.verification_note.trim() || null,
      }
      if (isNew) {
        await api.createMonitoredAsset(payload)
      } else {
        await api.updateMonitoredAsset(asset.id, payload)
      }
      onSaved()
    } catch (e) {
      setError(e.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onClick={onClose}>
      <div
        className="bg-white rounded-2xl shadow-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto"
        onClick={e => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-6 py-4 border-b border-[#ede8e3] sticky top-0 bg-white">
          <h2 className="text-base font-bold text-gray-900" style={{ fontFamily: 'Space Grotesk, sans-serif' }}>
            {isNew ? 'Nouvelle institution' : asset.name}
          </h2>
          <button onClick={onClose} className="p-1.5 rounded-lg text-gray-400 hover:bg-gray-50">
            <X size={16} />
          </button>
        </div>

        <div className="px-6 py-5 space-y-4">
          <div>
            <label className="text-xs text-gray-500 mb-1 block">Nom complet *</label>
            <input
              type="text" value={form.name}
              onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
              className="w-full text-sm border border-[#ede8e3] rounded-lg px-3 py-2 bg-[#faf8f5] focus:outline-none focus:border-[#c4a882]"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-gray-500 mb-1 block">Sigle</label>
              <input
                type="text" value={form.acronym}
                onChange={e => setForm(f => ({ ...f, acronym: e.target.value }))}
                className="w-full text-sm border border-[#ede8e3] rounded-lg px-3 py-2 bg-[#faf8f5] focus:outline-none focus:border-[#c4a882]"
              />
            </div>
            <div>
              <label className="text-xs text-gray-500 mb-1 block">Catégorie</label>
              <select
                value={form.category}
                onChange={e => setForm(f => ({ ...f, category: e.target.value }))}
                className="w-full text-sm border border-[#ede8e3] rounded-lg px-3 py-2 bg-[#faf8f5] focus:outline-none focus:border-[#c4a882]"
              >
                {Object.entries(CATEGORY_LABELS).map(([v, l]) => (
                  <option key={v} value={v}>{l}</option>
                ))}
              </select>
            </div>
          </div>

          <div>
            <label className="text-xs text-gray-500 mb-1 block">Domaine officiel</label>
            <input
              type="text" value={form.domain} placeholder="ex: minfi.gov.cm"
              onChange={e => setForm(f => ({ ...f, domain: e.target.value }))}
              className="w-full text-sm font-mono border border-[#ede8e3] rounded-lg px-3 py-2 bg-[#faf8f5] focus:outline-none focus:border-[#c4a882]"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-gray-500 mb-1 block">Statut de vérification</label>
              <select
                value={form.domain_status}
                onChange={e => setForm(f => ({ ...f, domain_status: e.target.value }))}
                className="w-full text-sm border border-[#ede8e3] rounded-lg px-3 py-2 bg-[#faf8f5] focus:outline-none focus:border-[#c4a882]"
              >
                {Object.entries(DOMAIN_STATUS_LABELS).map(([v, l]) => (
                  <option key={v} value={v}>{l}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-500 mb-1 block">ASN (télécom uniquement)</label>
              <input
                type="number" value={form.asn}
                onChange={e => setForm(f => ({ ...f, asn: e.target.value }))}
                className="w-full text-sm border border-[#ede8e3] rounded-lg px-3 py-2 bg-[#faf8f5] focus:outline-none focus:border-[#c4a882]"
              />
            </div>
          </div>

          <div>
            <label className="text-xs text-gray-500 mb-1 block">
              Alias de domaines légitimes <span className="text-gray-400">(exclus automatiquement du typosquatting)</span>
            </label>
            <div className="flex gap-2 mb-2">
              <input
                type="text" value={aliasInput}
                onChange={e => setAliasInput(e.target.value)}
                onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); addAlias() } }}
                placeholder="ex: minfi.cm"
                className="flex-1 text-sm font-mono border border-[#ede8e3] rounded-lg px-3 py-2 bg-[#faf8f5] focus:outline-none focus:border-[#c4a882]"
              />
              <button onClick={addAlias} className="px-3 py-2 bg-[#8b7355] text-white text-xs rounded-lg hover:bg-[#6b5740]">
                Ajouter
              </button>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {form.known_aliases.map(alias => (
                <span key={alias} className="flex items-center gap-1 text-xs font-mono px-2 py-1 bg-[#f5f0eb] text-[#8b7355] rounded-lg">
                  {alias}
                  <button onClick={() => removeAlias(alias)} className="hover:text-red-500">
                    <X size={11} />
                  </button>
                </span>
              ))}
            </div>
          </div>

          <div>
            <label className="text-xs text-gray-500 mb-1 block">Note de vérification</label>
            <textarea
              value={form.verification_note}
              onChange={e => setForm(f => ({ ...f, verification_note: e.target.value }))}
              rows={3}
              className="w-full text-sm border border-[#ede8e3] rounded-lg px-3 py-2 bg-[#faf8f5] focus:outline-none focus:border-[#c4a882] resize-none"
            />
          </div>

          <label className="flex items-center gap-2 text-sm text-gray-600 cursor-pointer">
            <input
              type="checkbox" checked={form.active}
              onChange={e => setForm(f => ({ ...f, active: e.target.checked }))}
              className="rounded border-[#ede8e3]"
            />
            Institution active (visible dans les scans et le dashboard)
          </label>

          {error && (
            <div className="px-3 py-2 bg-red-50 text-red-600 text-xs rounded-lg">{error}</div>
          )}

          <div className="flex justify-end gap-2 pt-2">
            <button onClick={onClose} className="px-4 py-2 text-sm text-gray-500 border border-[#ede8e3] rounded-lg hover:bg-gray-50">
              Annuler
            </button>
            <button
              onClick={save} disabled={saving}
              className="px-4 py-2 text-sm bg-[#8b7355] text-white rounded-lg hover:bg-[#6b5740] disabled:opacity-60"
            >
              {saving ? 'Enregistrement…' : isNew ? 'Créer' : 'Enregistrer'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

const JOB_GROUPS = [
  {
    label: 'Sources généralistes',
    jobs: [
      { name: 'urlhaus', label: 'URLhaus' },
      { name: 'feodo', label: 'Feodo Tracker' },
      { name: 'threatfox', label: 'ThreatFox' },
      { name: 'spamhaus', label: 'Spamhaus DROP' },
      { name: 'cisa_kev', label: 'CISA KEV' },
      { name: 'tor_exit', label: 'Tor Exit Nodes' },
      { name: 'otx', label: 'AlienVault OTX' },
      { name: 'otx_africa', label: 'AlienVault OTX Africa' },
      { name: 'openphish', label: 'OpenPhish' },
      { name: 'malwarebazaar', label: 'MalwareBazaar' },
      { name: 'nvd', label: 'NVD (CVE)' },
    ],
  },
  {
    label: 'Surveillance nationale',
    jobs: [
      { name: 'typosquat_monitor', label: 'Typosquat Monitor' },
      { name: 'nrd_monitor', label: 'Domaines nouvellement enregistrés' },
      { name: 'ct_monitor', label: 'Certificate Transparency (crt.sh)' },
    ],
  },
  {
    label: 'Post-traitement',
    jobs: [
      { name: 'run_correlation', label: 'Corrélation (relations entre IOCs)' },
      { name: 'run_clustering', label: 'Clustering (clusters de menaces)' },
      { name: 'recalculate_scores', label: 'Recalcul des scores de confiance' },
    ],
  },
]

function timeAgo(iso) {
  if (!iso) return null
  const diffMs = Date.now() - new Date(iso + 'Z').getTime()
  const mins = Math.round(diffMs / 60000)
  if (mins < 1) return 'à l\'instant'
  if (mins < 60) return `il y a ${mins} min`
  const hours = Math.round(mins / 60)
  if (hours < 24) return `il y a ${hours}h`
  return `il y a ${Math.round(hours / 24)}j`
}

function JobRow({ job, jobsByName, onRun, running }) {
  const info = jobsByName[job.name]
  const lastRun = info?.last_run
  const isRunning = running === job.name

  let statusBadge = <span className="text-xs text-gray-300 italic">jamais lancé</span>
  if (lastRun) {
    const styles = {
      success: 'bg-emerald-50 text-emerald-600',
      partial: 'bg-amber-50 text-amber-600',
      failed: 'bg-red-50 text-red-500',
      running: 'bg-blue-50 text-blue-500',
    }
    const labels = { success: 'succès', partial: 'partiel', failed: 'échec', running: 'en cours' }
    statusBadge = (
      <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${styles[lastRun.status] || styles.running}`}>
        {labels[lastRun.status] || lastRun.status} · {timeAgo(lastRun.started_at)}
      </span>
    )
  }

  return (
    <div className="flex items-center justify-between gap-3 py-2.5 border-b border-[#faf8f5] last:border-0">
      <div className="min-w-0">
        <p className="text-sm text-gray-700">{job.label}</p>
        <div className="mt-0.5">{statusBadge}</div>
      </div>
      <button
        onClick={() => onRun(job.name)}
        disabled={isRunning}
        className="shrink-0 px-3 py-1.5 text-xs font-medium bg-[#8b7355] text-white rounded-lg hover:bg-[#6b5740] disabled:opacity-50 transition-colors"
      >
        {isRunning ? 'Lancé…' : 'Lancer'}
      </button>
    </div>
  )
}

function RunAllCard({ jobsByName, onRun, running }) {
  const info = jobsByName['run_all']
  const lastRun = info?.last_run
  const isRunning = running === 'run_all' || lastRun?.status === 'running'

  let statusBadge = <span className="text-xs text-white/40 italic">jamais lancé</span>
  if (lastRun) {
    const styles = {
      success: 'bg-emerald-500/20 text-emerald-300',
      failed: 'bg-red-500/20 text-red-300',
      running: 'bg-blue-500/20 text-blue-300',
    }
    const labels = { success: 'succès', failed: 'échec', running: 'en cours' }
    statusBadge = (
      <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${styles[lastRun.status] || styles.running}`}>
        {labels[lastRun.status] || lastRun.status} · {timeAgo(lastRun.started_at)}
      </span>
    )
  }

  function handleClick() {
    if (!window.confirm(
      "Lancer TOUS les collecteurs, les 3 modules de surveillance nationale, puis la corrélation, " +
      "le clustering et le recalcul des scores, dans cet ordre ? Cette opération peut prendre " +
      "plusieurs dizaines de minutes (jusqu'à ~40 min rien que pour le typosquat monitor)."
    )) return
    onRun('run_all')
  }

  return (
    <div className="bg-[#2c1810] rounded-2xl p-5 text-white">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div className="min-w-0">
          <h3 className="text-sm font-semibold" style={{ fontFamily: 'Space Grotesk, sans-serif' }}>
            Lancer tout
          </h3>
          <p className="text-xs text-white/60 mt-1 max-w-xl">
            Enchaîne, dans l'ordre, tous les collecteurs généralistes, les 3 modules de surveillance
            nationale, puis corrélation → clustering → recalcul des scores (chaque étape attend la
            fin de la précédente). Peut prendre <strong>plusieurs dizaines de minutes</strong> —
            jusqu'à ~40 min rien que pour le typosquat monitor.
          </p>
          <div className="mt-2 flex items-center gap-2">
            {statusBadge}
            {lastRun?.detail && <span className="text-xs text-white/50 font-mono">{lastRun.detail}</span>}
          </div>
        </div>
        <button
          onClick={handleClick}
          disabled={isRunning}
          className="shrink-0 flex items-center gap-1.5 px-4 py-2 bg-white text-[#2c1810] text-sm font-medium rounded-xl hover:opacity-90 disabled:opacity-50 transition-colors"
        >
          <Play size={14} /> {isRunning ? 'En cours…' : 'Lancer tout'}
        </button>
      </div>
    </div>
  )
}

function JobsPanel() {
  const [jobs, setJobs] = useState([])
  const [running, setRunning] = useState(null)
  const [message, setMessage] = useState(null)

  function load() {
    api.listAdminJobs().then(setJobs).catch(console.error)
  }

  useEffect(() => { load() }, [])

  const jobsByName = useMemo(() => Object.fromEntries(jobs.map(j => [j.job_name, j])), [jobs])

  async function handleRun(name) {
    setRunning(name)
    setMessage(null)
    try {
      await api.runAdminJob(name)
      setMessage({ type: 'ok', text: `Job "${name}" lancé en arrière-plan.` })
      setTimeout(load, 3000)
    } catch (e) {
      setMessage({ type: 'error', text: e.message })
    } finally {
      setTimeout(() => setRunning(null), 1500)
    }
  }

  return (
    <div className="space-y-4">
      {message && (
        <div className={`px-4 py-2.5 rounded-xl text-sm ${message.type === 'ok' ? 'bg-emerald-50 text-emerald-600' : 'bg-red-50 text-red-600'}`}>
          {message.text}
        </div>
      )}
      <p className="text-xs text-gray-400 -mt-1">
        Les collecteurs tournent en arrière-plan (de quelques secondes à ~40 min pour le typosquat monitor).
        Le statut se met à jour automatiquement une fois terminé — rafraîchissez la page pour vérifier.
      </p>
      <RunAllCard jobsByName={jobsByName} onRun={handleRun} running={running} />
      {JOB_GROUPS.map(group => (
        <div key={group.label} className="bg-white rounded-2xl border border-[#ede8e3] p-4">
          <h3 className="text-xs font-semibold text-[#8b7355] uppercase mb-2">{group.label}</h3>
          {group.jobs.map(job => (
            <JobRow key={job.name} job={job} jobsByName={jobsByName} onRun={handleRun} running={running} />
          ))}
        </div>
      ))}
    </div>
  )
}

function NewApiClientModal({ onClose, onCreated }) {
  const [name, setName] = useState('')
  const [contact, setContact] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)

  async function submit() {
    if (!name.trim()) {
      setError('Le nom de l\'organisme est obligatoire.')
      return
    }
    setSaving(true)
    setError(null)
    try {
      const result = await api.createApiClient({ name: name.trim(), contact_email: contact.trim() || null })
      onCreated(result)
    } catch (e) {
      setError(e.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onClick={onClose}>
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between px-6 py-4 border-b border-[#ede8e3]">
          <h2 className="text-base font-bold text-gray-900" style={{ fontFamily: 'Space Grotesk, sans-serif' }}>
            Nouveau partenaire API
          </h2>
          <button onClick={onClose} className="p-1.5 rounded-lg text-gray-400 hover:bg-gray-50">
            <X size={16} />
          </button>
        </div>
        <div className="px-6 py-5 space-y-4">
          <div>
            <label className="text-xs text-gray-500 mb-1 block">Nom de l'organisme *</label>
            <input
              type="text" value={name} placeholder="ex: CIRT Sénégal"
              onChange={e => setName(e.target.value)}
              className="w-full text-sm border border-[#ede8e3] rounded-lg px-3 py-2 bg-[#faf8f5] focus:outline-none focus:border-[#c4a882]"
            />
          </div>
          <div>
            <label className="text-xs text-gray-500 mb-1 block">Email de contact</label>
            <input
              type="email" value={contact} placeholder="soc@organisme.example"
              onChange={e => setContact(e.target.value)}
              className="w-full text-sm border border-[#ede8e3] rounded-lg px-3 py-2 bg-[#faf8f5] focus:outline-none focus:border-[#c4a882]"
            />
          </div>
          {error && (
            <div className="px-3 py-2 bg-red-50 text-red-600 text-xs rounded-lg">{error}</div>
          )}
          <div className="flex justify-end gap-2 pt-2">
            <button onClick={onClose} className="px-4 py-2 text-sm text-gray-500 border border-[#ede8e3] rounded-lg hover:bg-gray-50">
              Annuler
            </button>
            <button
              onClick={submit} disabled={saving}
              className="px-4 py-2 text-sm bg-[#8b7355] text-white rounded-lg hover:bg-[#6b5740] disabled:opacity-60"
            >
              {saving ? 'Création…' : 'Créer'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

function ApiKeyRevealModal({ client, onClose, title }) {
  const [copied, setCopied] = useState(false)

  function copy() {
    navigator.clipboard.writeText(client.api_key).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }

  // Pas de fermeture au clic sur le fond : la clé ne sera plus jamais
  // affichée, on évite qu'un clic accidentel la fasse disparaître avant copie.
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg">
        <div className="px-6 py-4 border-b border-[#ede8e3]">
          <h2 className="text-base font-bold text-gray-900" style={{ fontFamily: 'Space Grotesk, sans-serif' }}>
            {title || `Partenaire créé : ${client.name}`}
          </h2>
        </div>
        <div className="px-6 py-5 space-y-4">
          <div className="flex items-start gap-2 px-3 py-2.5 bg-amber-50 text-amber-700 text-xs rounded-lg">
            <AlertTriangle size={14} className="shrink-0 mt-0.5" />
            <span>
              Cette clé ne sera <strong>plus jamais affichée</strong>. Copiez-la maintenant
              et transmettez-la au partenaire par un canal sécurisé.
            </span>
          </div>
          <div className="flex items-center gap-2">
            <code className="flex-1 text-xs font-mono px-3 py-2.5 bg-[#faf8f5] border border-[#ede8e3] rounded-lg break-all">
              {client.api_key}
            </code>
            <button
              onClick={copy}
              className="shrink-0 flex items-center gap-1.5 px-3 py-2.5 bg-[#8b7355] text-white text-xs rounded-lg hover:bg-[#6b5740] transition-colors"
            >
              <Copy size={13} /> {copied ? 'Copié !' : 'Copier'}
            </button>
          </div>
          <div className="flex justify-end pt-2">
            <button onClick={onClose} className="px-4 py-2 text-sm bg-[#2c1810] text-white rounded-lg hover:opacity-90">
              J'ai copié la clé, fermer
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

function ApiClientRow({ client, onRevoke, onRegenerate, revoking, regenerating }) {
  const isRevoking = revoking === client.id
  const isRegenerating = regenerating === client.id
  return (
    <tr className="border-b border-[#faf8f5] last:border-0">
      <td className="px-4 py-3">
        <p className="font-medium text-gray-800">{client.name}</p>
        <p className="text-xs text-gray-400">{client.contact_email || 'sans contact'}</p>
      </td>
      <td className="px-4 py-3">
        <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${
          client.is_active ? 'bg-emerald-50 text-emerald-600' : 'bg-red-50 text-red-500'
        }`}>
          {client.is_active ? 'actif' : 'révoqué'}
        </span>
      </td>
      <td className="px-4 py-3 text-xs text-gray-500">
        {client.last_used_at ? timeAgo(client.last_used_at) : <span className="italic text-gray-300">jamais utilisée</span>}
      </td>
      <td className="px-4 py-3 text-xs text-gray-400">{timeAgo(client.created_at)}</td>
      <td className="px-4 py-3 text-right">
        {client.is_active && (
          <div className="flex justify-end gap-2">
            <button
              onClick={() => onRegenerate(client)}
              disabled={isRegenerating || isRevoking}
              className="flex items-center gap-1 px-2.5 py-1 text-xs text-[#8b7355] border border-[#ede8e3] rounded-lg hover:bg-[#faf8f5] disabled:opacity-50 transition-colors"
            >
              <RefreshCw size={12} /> {isRegenerating ? 'Régénération…' : 'Régénérer'}
            </button>
            <button
              onClick={() => onRevoke(client)}
              disabled={isRevoking || isRegenerating}
              className="flex items-center gap-1 px-2.5 py-1 text-xs text-red-500 border border-red-200 rounded-lg hover:bg-red-50 disabled:opacity-50 transition-colors"
            >
              <Trash2 size={12} /> {isRevoking ? 'Révocation…' : 'Révoquer'}
            </button>
          </div>
        )}
      </td>
    </tr>
  )
}

// ── Documentation d'intégration TAXII/export (voir docs/taxii_integration.md) ──

function CodeBlock({ code }) {
  const [copied, setCopied] = useState(false)

  function copy() {
    navigator.clipboard.writeText(code).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }

  return (
    <div className="relative group">
      <button
        onClick={copy}
        className="absolute top-2.5 right-2.5 flex items-center gap-1.5 px-2.5 py-1 bg-white/10 text-white/70 text-xs rounded-lg hover:bg-white/20 hover:text-white transition-colors"
      >
        <Copy size={11} /> {copied ? 'Copié !' : 'Copier'}
      </button>
      <pre className="bg-[#2c1810] text-[#e8d5b7] rounded-xl p-4 pr-20 overflow-x-auto text-xs leading-relaxed font-mono">
        <code>{code}</code>
      </pre>
    </div>
  )
}

const RATE_LIMITS = [
  { endpoint: '/export/stix, /export/csv, /export/blocklist', limit: '20 / minute' },
  { endpoint: '/taxii2/, /taxii2/api, /taxii2/api/collections(/{id})', limit: '30 / minute' },
  { endpoint: '/taxii2/api/collections/{id}/objects, /manifest', limit: '120 / minute' },
]

const TAXII_ERRORS = [
  {
    code: '403',
    cause: 'Clé API absente, invalide ou révoquée',
    action: 'Vérifier le header X-API-Key, contacter l\'admin si la clé devrait être active',
  },
  {
    code: '400',
    cause: 'added_after ou next mal formé (sur /objects ou /manifest)',
    action: 'added_after doit être ISO 8601 ; next doit être copié tel quel depuis la réponse précédente, jamais construit à la main',
  },
  {
    code: '404',
    cause: 'UUID de collection incorrect (/collections/{id})',
    action: 'Utiliser l\'UUID renvoyé par GET /taxii2/api/collections, ne pas le coder en dur sans vérifier',
  },
]

const PY_SYNC_SCRIPT = `#!/usr/bin/env python3
"""Synchronise les IOCs actifs de la TIP ANTIC/CIRT Cameroun en continu."""
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import requests

BASE_URL = os.environ["TIP_BASE_URL"]         # ex: https://tip.antic.cm
API_KEY = os.environ["TIP_API_KEY"]           # clé fournie par l'admin de la TIP
COLLECTION_ID = "365fed99-08fa-4fcd-a1b3-fb247eb41d01"
STATE_FILE = Path("tip_sync_state.json")      # mémorise le dernier point de synchro

HEADERS = {"X-API-Key": API_KEY}


def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"added_after": None}  # premier lancement : tout récupérer


def save_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state))


def fetch_all_new_objects(added_after: str | None) -> list[dict]:
    objects = []
    params = {"limit": 500}
    if added_after:
        params["added_after"] = added_after

    url = f"{BASE_URL}/taxii2/api/collections/{COLLECTION_ID}/objects"
    while True:
        resp = requests.get(url, headers=HEADERS, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        objects.extend(data["objects"])

        if not data.get("more"):
            break
        params = {"next": data["next"], "limit": 500}  # 'next' remplace added_after

    return objects


def main() -> None:
    state = load_state()
    sync_start = datetime.now(timezone.utc).isoformat()

    new_objects = fetch_all_new_objects(state["added_after"])
    print(f"{len(new_objects)} nouveaux indicateurs récupérés.")

    for obj in new_objects:
        # TODO : brancher ici votre ingestion (SIEM, pare-feu, MISP...)
        print(f"  - {obj['id']}  {obj.get('pattern', '')}")

    state["added_after"] = sync_start
    save_state(state)


if __name__ == "__main__":
    main()`

function IntegrationDocs() {
  return (
    <TechInfoPanel title="Documentation d'intégration">
      <p>
        Ce document explique comment un organisme externe (autre CIRT régional, SIEM, pare-feu)
        se connecte à cette plateforme pour récupérer nos indicateurs de compromission (IOCs).
        Deux façons de les consommer :
      </p>

      <div className="overflow-x-auto">
        <table className="w-full text-xs border-collapse">
          <thead>
            <tr className="bg-[#faf8f5]">
              <th className="text-left px-3 py-2 font-semibold text-[#8b7355] uppercase border-b border-[#ede8e3]">Besoin</th>
              <th className="text-left px-3 py-2 font-semibold text-[#8b7355] uppercase border-b border-[#ede8e3]">Endpoint</th>
              <th className="text-left px-3 py-2 font-semibold text-[#8b7355] uppercase border-b border-[#ede8e3]">Usage</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td className="px-3 py-2 border-b border-[#faf8f5] align-top">Un export ponctuel (script cron simple, import manuel)</td>
              <td className="px-3 py-2 border-b border-[#faf8f5] align-top font-mono text-[#8b7355]">GET /export/stix, /export/csv, /export/blocklist</td>
              <td className="px-3 py-2 border-b border-[#faf8f5] align-top">Un seul appel, snapshot complet trié par confiance</td>
            </tr>
            <tr>
              <td className="px-3 py-2 align-top">Une synchronisation continue (SIEM, MISP, OpenCTI...)</td>
              <td className="px-3 py-2 align-top font-mono text-[#8b7355]">GET /taxii2/...</td>
              <td className="px-3 py-2 align-top">Protocole standard TAXII 2.1, pagination incrémentale</td>
            </tr>
          </tbody>
        </table>
      </div>

      <p>
        Ce guide couvre le second cas (TAXII), le plus pertinent pour une intégration durable
        entre deux plateformes.
      </p>

      <h3 className="text-sm font-semibold text-[#2c1810] pt-2" style={{ fontFamily: 'Space Grotesk, sans-serif' }}>
        1. Obtenir une clé API
      </h3>
      <p>
        Chaque organisme partenaire a sa propre clé, révocable indépendamment (voir aussi
        scripts/manage_api_keys.py). Créez-la ci-dessous avec « Nouveau partenaire », ou en CLI :
      </p>
      <CodeBlock code={`python -m scripts.manage_api_keys create --name "Nom de votre organisme" --contact "contact@votre-domaine"`} />
      <p>
        Vous recevrez une clé au format <code className="font-mono text-[#8b7355]">tip_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx</code>,
        affichée <strong>une seule fois</strong> à la création. Elle se fournit dans chaque appel via
        le header <code className="font-mono text-[#8b7355]">X-API-Key</code>.
      </p>

      <h3 className="text-sm font-semibold text-[#2c1810] pt-2" style={{ fontFamily: 'Space Grotesk, sans-serif' }}>
        2. Parcours TAXII standard (curl)
      </h3>
      <p>
        Un client TAXII 2.1 se connecte toujours dans cet ordre : Discovery → API Root →
        Collections → Objects.
      </p>
      <CodeBlock code={`KEY="tip_votre_cle_ici"
BASE="https://<votre-domaine-tip>"   # http://localhost:8001 en local

# 1. Discovery — liste les API roots disponibles
curl -s -H "X-API-Key: $KEY" "$BASE/taxii2/"

# 2. API Root — capacités de cet API root
curl -s -H "X-API-Key: $KEY" "$BASE/taxii2/api"

# 3. Lister les collections disponibles
curl -s -H "X-API-Key: $KEY" "$BASE/taxii2/api/collections"
# -> une seule collection : "365fed99-08fa-4fcd-a1b3-fb247eb41d01" (Indicateurs actifs)

# 4. Récupérer les objets STIX de la collection
curl -s -H "X-API-Key: $KEY" \\
  "$BASE/taxii2/api/collections/365fed99-08fa-4fcd-a1b3-fb247eb41d01/objects?limit=100"`} />

      <h3 className="text-sm font-semibold text-[#2c1810] pt-2" style={{ fontFamily: 'Space Grotesk, sans-serif' }}>
        3. Pagination (synchronisation incrémentale)
      </h3>
      <p>/objects et /manifest acceptent :</p>
      <ul className="list-disc pl-5 space-y-1">
        <li>
          <code className="font-mono text-[#8b7355]">added_after</code> (ISO 8601, ex.
          2026-07-01T00:00:00Z) : ne renvoie que les IOCs créés après cette date — à utiliser pour
          le <strong>premier</strong> appel d'une synchro.
        </li>
        <li>
          <code className="font-mono text-[#8b7355]">next</code> : curseur opaque renvoyé dans le
          champ next de la réponse précédente — à repasser tel quel pour la page suivante.
        </li>
        <li><code className="font-mono text-[#8b7355]">limit</code> (défaut 500, max 2000).</li>
      </ul>
      <p>
        La réponse contient toujours <code className="font-mono text-[#8b7355]">more</code> (bool)
        et, si more est true, <code className="font-mono text-[#8b7355]">next</code> (string). Une
        page peut contenir moins de limit objets si certaines lignes ne se convertissent pas en
        objet STIX (ex. les CVE) — ce n'est pas une anomalie : continuez à suivre next tant que
        more vaut true.
      </p>
      <CodeBlock code={`# Première page depuis une date donnée
curl -s -H "X-API-Key: $KEY" \\
  "$BASE/taxii2/api/collections/365fed99-08fa-4fcd-a1b3-fb247eb41d01/objects?added_after=2026-07-01T00:00:00Z&limit=100"

# Page suivante (le "next" vient de la réponse précédente)
curl -s -H "X-API-Key: $KEY" \\
  "$BASE/taxii2/api/collections/365fed99-08fa-4fcd-a1b3-fb247eb41d01/objects?next=<valeur_next>&limit=100"`} />

      <h3 className="text-sm font-semibold text-[#2c1810] pt-2" style={{ fontFamily: 'Space Grotesk, sans-serif' }}>
        Limites de débit (rate limiting)
      </h3>
      <p>Par organisme (clé API), pas par IP :</p>
      <div className="overflow-x-auto">
        <table className="w-full text-xs border-collapse">
          <thead>
            <tr className="bg-[#faf8f5]">
              <th className="text-left px-3 py-2 font-semibold text-[#8b7355] uppercase border-b border-[#ede8e3]">Endpoint(s)</th>
              <th className="text-left px-3 py-2 font-semibold text-[#8b7355] uppercase border-b border-[#ede8e3]">Limite</th>
            </tr>
          </thead>
          <tbody>
            {RATE_LIMITS.map(r => (
              <tr key={r.endpoint}>
                <td className="px-3 py-2 border-b border-[#faf8f5] last:border-0 font-mono text-[#8b7355]">{r.endpoint}</td>
                <td className="px-3 py-2 border-b border-[#faf8f5] last:border-0">{r.limit}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <h3 className="text-sm font-semibold text-[#2c1810] pt-2" style={{ fontFamily: 'Space Grotesk, sans-serif' }}>
        4. Script Python — synchronisation en continu
      </h3>
      <p>
        Boucle minimale : récupère tout ce qui est nouveau depuis le dernier passage, en suivant
        next jusqu'à épuisement, puis mémorise la date pour la prochaine exécution (à lancer par
        exemple via cron toutes les heures).
      </p>
      <CodeBlock code={PY_SYNC_SCRIPT} />
      <p>Variables d'environnement attendues :</p>
      <CodeBlock code={`export TIP_BASE_URL="https://tip.antic.cm"
export TIP_API_KEY="tip_votre_cle_ici"
python3 sync_tip.py`} />

      <h3 className="text-sm font-semibold text-[#2c1810] pt-2" style={{ fontFamily: 'Space Grotesk, sans-serif' }}>
        5. Erreurs courantes
      </h3>
      <div className="overflow-x-auto">
        <table className="w-full text-xs border-collapse">
          <thead>
            <tr className="bg-[#faf8f5]">
              <th className="text-left px-3 py-2 font-semibold text-[#8b7355] uppercase border-b border-[#ede8e3]">Code</th>
              <th className="text-left px-3 py-2 font-semibold text-[#8b7355] uppercase border-b border-[#ede8e3]">Cause</th>
              <th className="text-left px-3 py-2 font-semibold text-[#8b7355] uppercase border-b border-[#ede8e3]">Action</th>
            </tr>
          </thead>
          <tbody>
            {TAXII_ERRORS.map(e => (
              <tr key={e.code}>
                <td className="px-3 py-2 border-b border-[#faf8f5] last:border-0 align-top">
                  <span className="px-2 py-0.5 bg-red-50 text-red-600 rounded-full font-mono text-[11px]">{e.code}</span>
                </td>
                <td className="px-3 py-2 border-b border-[#faf8f5] last:border-0 align-top">{e.cause}</td>
                <td className="px-3 py-2 border-b border-[#faf8f5] last:border-0 align-top">{e.action}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <h3 className="text-sm font-semibold text-[#2c1810] pt-2" style={{ fontFamily: 'Space Grotesk, sans-serif' }}>
        6. Alternative : export ponctuel
      </h3>
      <p>
        Pour un import manuel ou un script cron simple (sans état à maintenir), /export/stix,
        /export/csv et /export/blocklist restent disponibles et protégés par la même clé API :
      </p>
      <CodeBlock code={`curl -s -H "X-API-Key: $KEY" "$BASE/export/stix?confidence_min=70" -o iocs.json
curl -s -H "X-API-Key: $KEY" "$BASE/export/blocklist?confidence_min=70" -o blocklist.txt`} />
      <p>
        Contrairement à /taxii2/*, ces endpoints n'ont pas de mécanisme de reprise incrémentale
        (added_after/next) — chaque appel renvoie l'état complet actuel au-dessus du seuil de
        confiance demandé.
      </p>
    </TechInfoPanel>
  )
}

function ApiClientsPanel() {
  const [clients, setClients] = useState([])
  const [loading, setLoading] = useState(true)
  const [creating, setCreating] = useState(false)
  const [newKeyResult, setNewKeyResult] = useState(null)
  const [newKeyTitle, setNewKeyTitle] = useState(null)
  const [revoking, setRevoking] = useState(null)
  const [regenerating, setRegenerating] = useState(null)
  const [message, setMessage] = useState(null)

  function load() {
    setLoading(true)
    api.listApiClients().then(setClients).catch(console.error).finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  function handleCreated(result) {
    setCreating(false)
    setNewKeyResult(result)
    setNewKeyTitle(null)
    load()
  }

  async function handleRevoke(client) {
    if (!window.confirm(`Révoquer l'accès de "${client.name}" ? Cette action est irréversible : le partenaire ne pourra plus interroger l'API avec cette clé.`)) return
    setRevoking(client.id)
    setMessage(null)
    try {
      await api.revokeApiClient(client.id)
      setMessage({ type: 'ok', text: `Accès révoqué pour ${client.name}.` })
      load()
    } catch (e) {
      setMessage({ type: 'error', text: e.message })
    } finally {
      setRevoking(null)
    }
  }

  async function handleRegenerate(client) {
    if (!window.confirm(`Régénérer la clé de "${client.name}" ? L'ancienne clé cessera de fonctionner immédiatement -- action irréversible.`)) return
    setRegenerating(client.id)
    setMessage(null)
    try {
      const result = await api.regenerateApiClient(client.id)
      setNewKeyResult(result)
      setNewKeyTitle(`Nouvelle clé pour : ${client.name}`)
      load()
    } catch (e) {
      setMessage({ type: 'error', text: e.message })
    } finally {
      setRegenerating(null)
    }
  }

  return (
    <div className="space-y-4">
      <IntegrationDocs />

      <div className="flex items-center justify-between gap-3">
        <p className="text-xs text-gray-400">
          Chaque organisme partenaire (CIRT régional, SIEM, pare-feu) reçoit sa propre clé pour
          interroger /export/* et /taxii2/*, révocable indépendamment sans affecter les autres.
        </p>
        <button
          onClick={() => setCreating(true)}
          className="shrink-0 flex items-center gap-1.5 px-4 py-2 bg-[#8b7355] text-white text-sm rounded-xl hover:bg-[#6b5740] transition-colors"
        >
          <Plus size={14} /> Nouveau partenaire
        </button>
      </div>

      {message && (
        <div className={`px-4 py-2.5 rounded-xl text-sm ${message.type === 'ok' ? 'bg-emerald-50 text-emerald-600' : 'bg-red-50 text-red-600'}`}>
          {message.text}
        </div>
      )}

      <div className="bg-white rounded-2xl border border-[#ede8e3] overflow-hidden">
        {loading ? (
          <div className="flex justify-center py-12">
            <div className="w-6 h-6 border-2 border-[#c4a882] border-t-transparent rounded-full animate-spin" />
          </div>
        ) : clients.length === 0 ? (
          <p className="text-sm text-gray-400 italic py-12 text-center">Aucun partenaire enregistré.</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[#f5f0eb] bg-[#faf8f5]">
                <th className="text-left px-4 py-3 text-xs font-semibold text-[#8b7355] uppercase">Organisme</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-[#8b7355] uppercase">Statut</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-[#8b7355] uppercase">Dernière utilisation</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-[#8b7355] uppercase">Créé</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody>
              {clients.map(c => (
                <ApiClientRow
                  key={c.id} client={c}
                  onRevoke={handleRevoke} revoking={revoking}
                  onRegenerate={handleRegenerate} regenerating={regenerating}
                />
              ))}
            </tbody>
          </table>
        )}
      </div>

      {creating && (
        <NewApiClientModal onClose={() => setCreating(false)} onCreated={handleCreated} />
      )}
      {newKeyResult && (
        <ApiKeyRevealModal
          client={newKeyResult}
          title={newKeyTitle}
          onClose={() => { setNewKeyResult(null); setNewKeyTitle(null) }}
        />
      )}
    </div>
  )
}

function NewEmailRecipientModal({ onClose, onCreated }) {
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)

  async function submit() {
    if (!name.trim()) {
      setError('Le nom du destinataire est obligatoire.')
      return
    }
    if (!email.trim() || !email.includes('@')) {
      setError('Adresse email invalide.')
      return
    }
    setSaving(true)
    setError(null)
    try {
      await api.createEmailRecipient({ name: name.trim(), email: email.trim() })
      onCreated()
    } catch (e) {
      setError(e.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onClick={onClose}>
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between px-6 py-4 border-b border-[#ede8e3]">
          <h2 className="text-base font-bold text-gray-900" style={{ fontFamily: 'Space Grotesk, sans-serif' }}>
            Nouveau destinataire
          </h2>
          <button onClick={onClose} className="p-1.5 rounded-lg text-gray-400 hover:bg-gray-50">
            <X size={16} />
          </button>
        </div>
        <div className="px-6 py-5 space-y-4">
          <div>
            <label className="text-xs text-gray-500 mb-1 block">Nom *</label>
            <input
              type="text" value={name} placeholder="ex: Équipe CIRT"
              onChange={e => setName(e.target.value)}
              className="w-full text-sm border border-[#ede8e3] rounded-lg px-3 py-2 bg-[#faf8f5] focus:outline-none focus:border-[#c4a882]"
            />
          </div>
          <div>
            <label className="text-xs text-gray-500 mb-1 block">Email *</label>
            <input
              type="email" value={email} placeholder="contact@antic.cm"
              onChange={e => setEmail(e.target.value)}
              className="w-full text-sm border border-[#ede8e3] rounded-lg px-3 py-2 bg-[#faf8f5] focus:outline-none focus:border-[#c4a882]"
            />
          </div>
          {error && (
            <div className="px-3 py-2 bg-red-50 text-red-600 text-xs rounded-lg">{error}</div>
          )}
          <div className="flex justify-end gap-2 pt-2">
            <button onClick={onClose} className="px-4 py-2 text-sm text-gray-500 border border-[#ede8e3] rounded-lg hover:bg-gray-50">
              Annuler
            </button>
            <button
              onClick={submit} disabled={saving}
              className="px-4 py-2 text-sm bg-[#8b7355] text-white rounded-lg hover:bg-[#6b5740] disabled:opacity-60"
            >
              {saving ? 'Création…' : 'Créer'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

function EmailRecipientRow({ recipient, onRevoke, revoking }) {
  const isRevoking = revoking === recipient.id
  return (
    <tr className="border-b border-[#faf8f5] last:border-0">
      <td className="px-4 py-3">
        <p className="font-medium text-gray-800">{recipient.name}</p>
        <p className="text-xs text-gray-400">{recipient.email}</p>
      </td>
      <td className="px-4 py-3">
        <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${
          recipient.is_active ? 'bg-emerald-50 text-emerald-600' : 'bg-red-50 text-red-500'
        }`}>
          {recipient.is_active ? 'actif' : 'désactivé'}
        </span>
      </td>
      <td className="px-4 py-3 text-xs text-gray-400">{timeAgo(recipient.created_at)}</td>
      <td className="px-4 py-3 text-right">
        {recipient.is_active && (
          <button
            onClick={() => onRevoke(recipient)}
            disabled={isRevoking}
            className="ml-auto flex items-center gap-1 px-2.5 py-1 text-xs text-red-500 border border-red-200 rounded-lg hover:bg-red-50 disabled:opacity-50 transition-colors"
          >
            <Trash2 size={12} /> {isRevoking ? 'Désactivation…' : 'Désactiver'}
          </button>
        )}
      </td>
    </tr>
  )
}

function EmailRecipientsPanel() {
  const [recipients, setRecipients] = useState([])
  const [loading, setLoading] = useState(true)
  const [creating, setCreating] = useState(false)
  const [revoking, setRevoking] = useState(null)
  const [message, setMessage] = useState(null)
  const [digestStatus, setDigestStatus] = useState(null)
  const [sending, setSending] = useState(false)

  function load() {
    setLoading(true)
    api.listEmailRecipients().then(setRecipients).catch(console.error).finally(() => setLoading(false))
  }

  function loadDigestStatus() {
    api.emailDigestStatus().then(setDigestStatus).catch(console.error)
  }

  useEffect(() => { load(); loadDigestStatus() }, [])

  function handleCreated() {
    setCreating(false)
    setMessage({ type: 'ok', text: 'Destinataire ajouté.' })
    load()
  }

  async function handleRevoke(recipient) {
    if (!window.confirm(`Retirer "${recipient.name}" (${recipient.email}) de la liste des destinataires du digest ?`)) return
    setRevoking(recipient.id)
    setMessage(null)
    try {
      await api.revokeEmailRecipient(recipient.id)
      setMessage({ type: 'ok', text: `${recipient.name} désactivé.` })
      load()
    } catch (e) {
      setMessage({ type: 'error', text: e.message })
    } finally {
      setRevoking(null)
    }
  }

  async function handleSendNow() {
    const activeCount = recipients.filter(r => r.is_active).length
    if (!window.confirm(`Envoyer le digest maintenant à ${activeCount} destinataire(s) actif(s) ? Cet envoi immédiat est indépendant du cycle automatique de 3 jours.`)) return
    setSending(true)
    setMessage(null)
    try {
      await api.sendEmailDigestNow()
      setMessage({ type: 'ok', text: 'Envoi du digest lancé en arrière-plan.' })
      setTimeout(loadDigestStatus, 4000)
    } catch (e) {
      setMessage({ type: 'error', text: e.message })
    } finally {
      setSending(false)
    }
  }

  return (
    <div className="space-y-4">
      <div className="bg-white rounded-2xl border border-[#ede8e3] p-5 flex items-center justify-between gap-4 flex-wrap">
        <div>
          <p className="text-xs text-[#8b7355] uppercase tracking-wider font-medium mb-1">Prochain digest</p>
          {digestStatus ? (
            <>
              <p className="text-2xl font-bold text-gray-900" style={{ fontFamily: 'Space Grotesk, sans-serif' }}>
                {digestStatus.eligible_count} <span className="text-sm font-normal text-gray-400">IOC(s) éligible(s)</span>
              </p>
              <p className="text-xs text-gray-400 mt-1">
                {digestStatus.last_sent_at
                  ? `Dernier envoi réussi : ${timeAgo(digestStatus.last_sent_at)}`
                  : "Aucun envoi réussi pour l'instant"}
              </p>
            </>
          ) : (
            <p className="text-sm text-gray-400">Chargement…</p>
          )}
        </div>
        <button
          onClick={handleSendNow}
          disabled={sending}
          className="shrink-0 flex items-center gap-1.5 px-4 py-2 bg-[#2c1810] text-white text-sm rounded-xl hover:opacity-90 disabled:opacity-50 transition-colors"
        >
          <Send size={14} /> {sending ? 'Envoi en cours…' : 'Envoyer maintenant'}
        </button>
      </div>

      <div className="flex items-center justify-between gap-3">
        <p className="text-xs text-gray-400">
          Destinataires du digest IOC Cameroun, envoyé tous les 3 jours par email.
          Désactiver un destinataire l'exclut du prochain envoi sans le supprimer.
        </p>
        <button
          onClick={() => setCreating(true)}
          className="shrink-0 flex items-center gap-1.5 px-4 py-2 bg-[#8b7355] text-white text-sm rounded-xl hover:bg-[#6b5740] transition-colors"
        >
          <Plus size={14} /> Ajouter
        </button>
      </div>

      {message && (
        <div className={`px-4 py-2.5 rounded-xl text-sm ${message.type === 'ok' ? 'bg-emerald-50 text-emerald-600' : 'bg-red-50 text-red-600'}`}>
          {message.text}
        </div>
      )}

      <div className="bg-white rounded-2xl border border-[#ede8e3] overflow-hidden">
        {loading ? (
          <div className="flex justify-center py-12">
            <div className="w-6 h-6 border-2 border-[#c4a882] border-t-transparent rounded-full animate-spin" />
          </div>
        ) : recipients.length === 0 ? (
          <p className="text-sm text-gray-400 italic py-12 text-center">Aucun destinataire enregistré.</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[#f5f0eb] bg-[#faf8f5]">
                <th className="text-left px-4 py-3 text-xs font-semibold text-[#8b7355] uppercase">Destinataire</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-[#8b7355] uppercase">Statut</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-[#8b7355] uppercase">Ajouté</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody>
              {recipients.map(r => (
                <EmailRecipientRow key={r.id} recipient={r} onRevoke={handleRevoke} revoking={revoking} />
              ))}
            </tbody>
          </table>
        )}
      </div>

      {creating && (
        <NewEmailRecipientModal onClose={() => setCreating(false)} onCreated={handleCreated} />
      )}
    </div>
  )
}

export default function Admin() {
  const { isAdmin } = useAuth()
  const [assets, setAssets] = useState([])
  const [loading, setLoading] = useState(true)
  const [categoryFilter, setCategoryFilter] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [editing, setEditing] = useState(null) // null | 'new' | asset object
  const [tab, setTab] = useState('institutions') // 'institutions' | 'jobs'

  function load() {
    setLoading(true)
    api.monitoredAssets().then(setAssets).catch(console.error).finally(() => setLoading(false))
  }

  useEffect(() => {
    if (isAdmin) load()
  }, [isAdmin])

  const filtered = useMemo(() => {
    return assets.filter(a => {
      if (categoryFilter && a.category !== categoryFilter) return false
      if (statusFilter && a.domain_status !== statusFilter) return false
      if (search) {
        const q = search.toLowerCase()
        if (!a.name.toLowerCase().includes(q) && !(a.acronym || '').toLowerCase().includes(q)) return false
      }
      return true
    })
  }, [assets, categoryFilter, statusFilter, search])

  const totalPages = Math.max(Math.ceil(filtered.length / PAGE_SIZE), 1)
  const pageItems = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE)

  if (!isAdmin) return <AccessDenied />

  return (
    <div className="space-y-5" style={{ fontFamily: 'Inter, sans-serif' }}>
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900" style={{ fontFamily: 'Space Grotesk, sans-serif' }}>
            Administration du référentiel
          </h1>
          <p className="text-sm text-gray-400 mt-0.5">
            {assets.length} institutions au total, {assets.filter(a => a.active !== false).length} actives
          </p>
        </div>
        {tab === 'institutions' && (
          <button
            onClick={() => setEditing('new')}
            className="flex items-center gap-1.5 px-4 py-2 bg-[#8b7355] text-white text-sm rounded-xl hover:bg-[#6b5740] transition-colors"
          >
            <Plus size={14} /> Nouvelle institution
          </button>
        )}
      </div>

      <TechInfoPanel>
        <p>
          Interface d'administration réservée aux administrateurs : gestion du référentiel des
          institutions (création, édition, statut de domaine), déclenchement manuel des
          collecteurs et des tâches de post-traitement (corrélation, clustering, recalcul des
          scores), gestion des clés API des partenaires externes, et gestion des destinataires du
          digest email automatique.
        </p>
      </TechInfoPanel>

      <div className="flex gap-2">
        {[{ v: 'institutions', l: 'Référentiel' }, { v: 'jobs', l: 'Collecte & traitement' }, { v: 'api-clients', l: 'Partenaires API' }, { v: 'email-recipients', l: 'Destinataires email' }].map(({ v, l }) => (
          <button
            key={v}
            onClick={() => setTab(v)}
            className={`px-4 py-2 rounded-xl text-sm font-medium transition-all ${
              tab === v ? 'bg-[#2c1810] text-white' : 'bg-white text-gray-500 border border-[#ede8e3] hover:border-[#c4a882]'
            }`}
          >
            {l}
          </button>
        ))}
      </div>

      {tab === 'jobs' && <JobsPanel />}

      {tab === 'api-clients' && <ApiClientsPanel />}

      {tab === 'email-recipients' && <EmailRecipientsPanel />}

      {tab === 'institutions' && (
      <>
      <div className="bg-white rounded-2xl border border-[#ede8e3] p-4 space-y-3">
        <div className="relative">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text" value={search}
            onChange={e => { setSearch(e.target.value); setPage(1) }}
            placeholder="Rechercher par nom ou sigle…"
            className="w-full pl-9 pr-4 py-2 text-sm border border-[#ede8e3] rounded-xl bg-[#faf8f5] focus:outline-none focus:border-[#c4a882]"
          />
        </div>
        <div className="flex gap-2 flex-wrap">
          {[{ v: '', l: 'Toutes catégories' }, ...Object.entries(CATEGORY_LABELS).map(([v, l]) => ({ v, l }))].map(({ v, l }) => (
            <button
              key={v}
              onClick={() => { setCategoryFilter(v); setPage(1) }}
              className={`px-3 py-1.5 rounded-full text-xs font-medium border transition-all ${
                categoryFilter === v ? 'bg-[#8b7355] text-white border-[#8b7355]' : 'bg-white text-gray-500 border-[#ede8e3] hover:border-[#c4a882]'
              }`}
            >
              {l}
            </button>
          ))}
        </div>
        <div className="flex gap-2 flex-wrap">
          {[{ v: '', l: 'Tous statuts' }, ...Object.entries(DOMAIN_STATUS_LABELS).map(([v, l]) => ({ v, l }))].map(({ v, l }) => (
            <button
              key={v}
              onClick={() => { setStatusFilter(v); setPage(1) }}
              className={`px-3 py-1.5 rounded-full text-xs font-medium border transition-all ${
                statusFilter === v ? 'bg-[#2c1810] text-white border-[#2c1810]' : 'bg-white text-gray-500 border-[#ede8e3] hover:border-[#c4a882]'
              }`}
            >
              {l}
            </button>
          ))}
        </div>
      </div>

      <div className="bg-white rounded-2xl border border-[#ede8e3] overflow-hidden">
        {loading ? (
          <div className="flex justify-center py-12">
            <div className="w-6 h-6 border-2 border-[#c4a882] border-t-transparent rounded-full animate-spin" />
          </div>
        ) : pageItems.length === 0 ? (
          <p className="text-sm text-gray-400 italic py-12 text-center">Aucun résultat.</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[#f5f0eb] bg-[#faf8f5]">
                <th className="text-left px-4 py-3 text-xs font-semibold text-[#8b7355] uppercase">Institution</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-[#8b7355] uppercase">Catégorie</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-[#8b7355] uppercase">Domaine</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-[#8b7355] uppercase">Statut</th>
              </tr>
            </thead>
            <tbody>
              {pageItems.map(a => (
                <tr
                  key={a.id}
                  onClick={() => setEditing(a)}
                  className="border-b border-[#faf8f5] hover:bg-[#faf8f5] cursor-pointer transition-colors"
                >
                  <td className="px-4 py-3">
                    <p className="font-medium text-gray-800">{a.name}</p>
                    <p className="text-xs text-gray-400">{a.acronym || 'sans sigle'}</p>
                  </td>
                  <td className="px-4 py-3 text-xs text-gray-500">{CATEGORY_LABELS[a.category]}</td>
                  <td className="px-4 py-3 text-xs font-mono text-gray-500">{a.domain || '—'}</td>
                  <td className="px-4 py-3"><StatusPill status={a.domain_status} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}
            className="flex items-center gap-1.5 px-4 py-2 text-sm text-[#8b7355] border border-[#ede8e3] rounded-xl bg-white hover:border-[#c4a882] disabled:opacity-30">
            <ChevronLeft size={14} /> Précédent
          </button>
          <span className="text-sm text-gray-400">Page {page} / {totalPages}</span>
          <button onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page === totalPages}
            className="flex items-center gap-1.5 px-4 py-2 text-sm text-[#8b7355] border border-[#ede8e3] rounded-xl bg-white hover:border-[#c4a882] disabled:opacity-30">
            Suivant <ChevronRight size={14} />
          </button>
        </div>
      )}
      </>
      )}

      {editing && (
        <EditModal
          asset={editing === 'new' ? null : editing}
          onClose={() => setEditing(null)}
          onSaved={() => { setEditing(null); load() }}
        />
      )}
    </div>
  )
}
