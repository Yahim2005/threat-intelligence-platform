// src/pages/Admin.jsx
// Interface d'administration du referentiel institutionnel (monitored_assets),
// pour permettre a une equipe non technique de gerer les institutions
// surveillees sans passer par des scripts Python en ligne de commande.
import { useEffect, useState, useMemo } from 'react'
import { Plus, X, Search, ChevronLeft, ChevronRight, Trash2 } from 'lucide-react'
import { api } from '../api/client'
import { useAuth } from '../context/AuthContext'

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

export default function Admin() {
  const { isAdmin } = useAuth()
  const [assets, setAssets] = useState([])
  const [loading, setLoading] = useState(true)
  const [categoryFilter, setCategoryFilter] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [editing, setEditing] = useState(null) // null | 'new' | asset object

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
        <button
          onClick={() => setEditing('new')}
          className="flex items-center gap-1.5 px-4 py-2 bg-[#8b7355] text-white text-sm rounded-xl hover:bg-[#6b5740] transition-colors"
        >
          <Plus size={14} /> Nouvelle institution
        </button>
      </div>

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
