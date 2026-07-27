// src/App.jsx
import { useState } from 'react'
import Navbar          from './components/Navbar'
import Overview        from './pages/Overview'
import Indicators      from './pages/Indicators'
import Threats         from './pages/Threats'
import Sources         from './pages/Sources'
import Health          from './pages/Health'
import Admin           from './pages/Admin'
import Lookup          from './pages/Lookup'
import IndicatorDetail from './pages/IndicatorDetail'
import Login           from './pages/Login'
import ThreatDetail    from './pages/ThreatDetail'
import Analytics       from './pages/Analytics'
import Cameroon        from './pages/Cameroon'
import CameroonInstitutionsRank from './pages/CameroonInstitutionsRank'
import CameroonTyposquat        from './pages/CameroonTyposquat'
import CameroonExposed          from './pages/CameroonExposed'
import CameroonInstitutions     from './pages/CameroonInstitutions'
import SubmitIOC       from './components/SubmitIOC'
import SplashScreen    from './components/SplashScreen'
import { useDarkMode } from './hooks/useDarkMode'
import { Menu, Search, LogOut, LogIn, Moon, Sun, MapPin } from 'lucide-react'
import { useAuth } from './context/AuthContext'

export default function App() {
  const [page,        setPage]        = useState('overview')
  const [sidebarOpen, setSidebar]     = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [detailValue, setDetailValue] = useState(null)
  const [threatId,    setThreatId]    = useState(null)
  const [showSplash,  setShowSplash]  = useState(false)
  const [dark, setDark] = useDarkMode()
  const { user, isAdmin, loading: authLoading, logout } = useAuth()

  function navigate(id) {
    setPage(id)
    setDetailValue(null)
    setSidebar(false)
  }

  function openDetail(value) {
    setDetailValue(value)
    setPage('detail')
    setSidebar(false)
  }

  function openThreat(id) {
    setThreatId(id)
    setPage('threat-detail')
    setSidebar(false)
  }

  function globalSearch(e) {
    if (e.key === 'Enter' && searchQuery.trim()) {
      setPage('lookup')
      setSidebar(false)
    }
  }

  // Appelé par Login après un login réussi
  function handleLoginSuccess() {
    setShowSplash(true)
  }

  // Appelé par SplashScreen quand l'animation est terminée
  function handleSplashDone() {
    setShowSplash(false)
    navigate('overview')
  }

  function renderPage() {
    if (page === 'detail')        return <IndicatorDetail value={detailValue} onBack={() => navigate('indicators')} />
    if (page === 'lookup')        return <Lookup initialQuery={searchQuery} onOpenDetail={openDetail} />
    if (page === 'overview')      return <Overview onOpenDetail={openDetail} onNavigate={navigate} />
    if (page === 'indicators')    return <Indicators onOpenDetail={openDetail} />
    if (page === 'threats')       return <Threats onOpenThreat={openThreat} />
    if (page === 'sources')       return <Sources />
    if (page === 'health')        return isAdmin ? <Health /> : <AccessDenied />
    if (page === 'admin')         return <Admin />
    if (page === 'analytics')     return <Analytics />
    if (page === 'cameroon')      return <Cameroon onOpenDetail={openDetail} onNavigate={navigate} />
    if (page === 'cameroon-institutions-rank') return <CameroonInstitutionsRank onBack={() => navigate('cameroon')} />
    if (page === 'cameroon-typosquat')         return <CameroonTyposquat onBack={() => navigate('cameroon')} onOpenDetail={openDetail} />
    if (page === 'cameroon-exposed')           return <CameroonExposed onBack={() => navigate('cameroon')} />
    if (page === 'cameroon-institutions')      return <CameroonInstitutions onBack={() => navigate('cameroon')} onNavigate={navigate} />
    if (page === 'threat-detail') return <ThreatDetail threatId={threatId} onBack={() => navigate('threats')} onOpenDetail={openDetail} />
    return null
  }

  // Chargement initial de la session (restauration token)
  if (authLoading) {
    return <div className="min-h-screen bg-[#faf8f5]" />
  }

  // Cinématique post-login
  if (showSplash) {
    return <SplashScreen onDone={handleSplashDone} dataReady={true} />
  }

  // Page de login
  if (!user || page === 'login') {
    return <Login onSuccess={handleLoginSuccess} />
  }

  return (
    <div className="flex min-h-screen bg-gray-50 font-sans">
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/40 z-20 lg:hidden"
          onClick={() => setSidebar(false)}
        />
      )}

      {/* Sidebar */}
      <div className={`
        fixed inset-y-0 left-0 z-30 w-56 transform transition-transform duration-200
        lg:relative lg:translate-x-0 lg:flex lg:flex-col
        ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}
      `}>
        <Navbar current={page} onChange={navigate} isAdmin={isAdmin} />
      </div>

      {/* Contenu principal */}
      <div className="flex-1 flex flex-col min-w-0">
        <header className="flex items-center gap-3 px-4 lg:px-8 py-3 bg-white border-b border-gray-100 shadow-sm sticky top-0 z-10">
          <button
            onClick={() => setSidebar(true)}
            className="lg:hidden p-1.5 rounded-lg text-gray-600 hover:bg-gray-100"
          >
            <Menu size={20} />
          </button>

          {/* Barre de recherche */}
          <div className="relative flex-1 max-w-lg">
            <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              onKeyDown={globalSearch}
              placeholder="Rechercher un IOC : IP, domaine, email, hash… (Entrée)"
              className="w-full pl-9 pr-4 py-2 text-sm border border-gray-200 rounded-xl bg-gray-50 focus:outline-none focus:ring-2 focus:ring-[#c4a882]/40 focus:bg-white transition-colors"
            />
          </div>

          <button
            onClick={() => { if (searchQuery.trim()) setPage('lookup') }}
            disabled={!searchQuery.trim()}
            className="hidden sm:flex items-center gap-1.5 px-4 py-2 bg-[#c4a882] text-white text-sm rounded-xl hover:bg-[#8b7355] disabled:opacity-40 transition-colors"
          >
            <Search size={13} /> Lookup
          </button>

          {/* Groupe droit : toujours plaqué à droite grâce à ml-auto,
              indépendamment de la largeur de la barre de recherche */}
          <div className="flex items-center gap-2 ml-auto">
            {/* Accès rapide Surveillance nationale */}
            <button
              onClick={() => navigate('cameroon')}
              className="hidden md:flex items-center gap-1.5 px-4 py-2 bg-[#2c1810] text-[#e8d5b7] text-sm rounded-xl hover:bg-[#3d2418] transition-colors"
              title="Surveillance nationale"
            >
              <MapPin size={14} /> Surveillance nationale
            </button>

            {/* Toggle dark mode */}
            <button
              onClick={() => setDark(d => !d)}
              className="p-2 rounded-xl text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-700 dark:text-gray-300 transition-colors"
              title={dark ? 'Mode clair' : 'Mode sombre'}
            >
              {dark ? <Sun size={16} /> : <Moon size={16} />}
            </button>

            {/* Bouton SubmitIOC réservé aux admins */}
            {isAdmin && <SubmitIOC onSuccess={() => {}} />}

            {/* Connexion / Déconnexion */}
            {user ? (
              <button
                onClick={logout}
                title={user.email}
                className="flex items-center gap-1.5 px-3 py-2 text-sm text-gray-500 rounded-xl hover:bg-gray-100 dark:hover:bg-gray-700 dark:text-gray-300 transition-colors"
              >
                <LogOut size={14} />
                <span className="hidden sm:inline">Déconnexion</span>
              </button>
            ) : (
              <button
                onClick={() => navigate('login')}
                className="flex items-center gap-1.5 px-4 py-2 bg-[#8b7355] text-white text-sm rounded-xl hover:bg-[#c4a882] transition-colors"
              >
                <LogIn size={14} /> Connexion
              </button>
            )}
          </div>
        </header>

        <main className="flex-1 p-4 lg:p-8 overflow-auto">
          {renderPage()}
        </main>
      </div>
    </div>
  )
}

function AccessDenied() {
  return (
    <div className="flex flex-col items-center justify-center py-24 text-center gap-2">
      <p
        className="text-lg font-semibold text-[#2c1810]"
        style={{ fontFamily: 'Space Grotesk, sans-serif' }}
      >
        Accès réservé aux administrateurs
      </p>
      <p className="text-sm text-gray-400">
        Connectez-vous avec un compte admin pour consulter cette page.
      </p>
    </div>
  )
}