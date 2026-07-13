// src/context/AuthContext.jsx
import { createContext, useContext, useState, useEffect } from 'react'
import { api, setAuthToken, getAuthToken } from '../api/client'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  // Au chargement de l'app : si un token existe déjà (localStorage), on
  // vérifie qu'il est toujours valide en interrogeant /auth/me.
  useEffect(() => {
    async function restoreSession() {
      if (!getAuthToken()) {
        setLoading(false)
        return
      }
      try {
        const me = await api.me()
        setUser(me)
      } catch {
        setAuthToken(null)
      } finally {
        setLoading(false)
      }
    }
    restoreSession()
  }, [])

  async function login(identifier, password) {
    const data = await api.login({ identifier, password })
    setAuthToken(data.access_token)
    setUser(data.user)
    return data.user
  }

  async function register(email, password, fullName) {
    const data = await api.register({ email, password, full_name: fullName || undefined })
    setAuthToken(data.access_token)
    setUser(data.user)
    return data.user
  }

  function logout() {
    setAuthToken(null)
    setUser(null)
  }

  const value = {
    user,
    loading,
    isAuthenticated: !!user,
    isAdmin: user?.role === 'admin',
    login,
    register,
    logout,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth doit être utilisé à l\'intérieur de <AuthProvider>')
  return ctx
}
