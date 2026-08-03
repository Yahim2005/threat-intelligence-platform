// src/pages/Login.jsx
import { useState } from 'react'
import { AlertCircle } from 'lucide-react'
import { useAuth } from '../context/AuthContext'

export default function Login({ onSuccess }) {
  const { login } = useAuth()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [form, setForm] = useState({ identifier: '', password: '' })

  async function submit(e) {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      await login(form.identifier.trim(), form.password)
      if (onSuccess) onSuccess()
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const inputClass =
    'w-full text-sm rounded-lg px-3.5 py-2.5 bg-[#faf8f5] ' +
    'border border-[#e5ddd3] text-[#2c1810] ' +
    'placeholder:text-gray-400 focus:outline-none focus:border-[#c4a882] ' +
    'focus:ring-2 focus:ring-[#c4a882]/40 transition-colors'

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#faf8f5] px-4">
      <div className="w-full max-w-sm">
        {/* En-tête */}
        <div className="flex flex-col items-center text-center gap-3 mb-6">
          <img
            src="/Logo-Antic.png"
            alt="ANTIC"
            className="w-16 h-16 object-contain"
          />
          <div>
            <p className="text-[11px] uppercase tracking-[0.15em] text-[#a8988a] mb-1">
              Threat Intelligence Platform
            </p>
            <h1
              className="text-xl font-semibold text-[#2c1810]"
              style={{ fontFamily: 'Space Grotesk, sans-serif' }}
            >
              Connexion
            </h1>
          </div>
        </div>

        {/* Carte */}
        <div className="bg-white rounded-2xl shadow-xl border border-[#ede8e3] p-6">
          {/* Formulaire */}
          <form onSubmit={submit} className="space-y-4">
            <div>
              <label className="text-xs font-medium text-[#6b5d4f] mb-1.5 block">
                Email ou téléphone
              </label>
              <input
                type="text"
                required
                value={form.identifier}
                onChange={e => setForm(f => ({ ...f, identifier: e.target.value }))}
                placeholder="vous@exemple.com"
                className={inputClass}
                autoFocus
              />
            </div>

            <div>
              <label className="text-xs font-medium text-[#6b5d4f] mb-1.5 block">
                Mot de passe
              </label>
              <input
                type="password"
                required
                minLength={8}
                value={form.password}
                onChange={e => setForm(f => ({ ...f, password: e.target.value }))}
                placeholder="••••••••"
                className={inputClass}
              />
            </div>

            {error && (
              <div className="flex items-start gap-2 p-3 rounded-lg text-sm bg-red-50 text-red-700">
                <AlertCircle size={15} className="shrink-0 mt-0.5" />
                <span>{error}</span>
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full py-2.5 text-sm font-medium bg-[#8b7355] text-white rounded-lg hover:bg-[#7a6349] focus:outline-none focus:ring-2 focus:ring-[#c4a882]/50 focus:ring-offset-2 focus:ring-offset-white disabled:opacity-60 transition-colors"
            >
              {loading ? 'Veuillez patienter…' : 'Se connecter'}
            </button>
          </form>
        </div>

        {/* Aide contextuelle sous la carte */}
        <p className="text-center text-xs text-gray-400 mt-5">
          Les comptes sont créés par un administrateur ANTIC/CIRT.
        </p>
      </div>
    </div>
  )
}
