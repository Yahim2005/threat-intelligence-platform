// src/App.jsx
import { useState } from 'react'
import Navbar          from './components/Navbar'
import Overview        from './pages/Overview'
import Indicators      from './pages/Indicators'
import Threats         from './pages/Threats'
import Sources         from './pages/Sources'
import Health          from './pages/Health'
import Lookup          from './pages/Lookup'
import IndicatorDetail from './pages/IndicatorDetail'
import { Menu, Search } from 'lucide-react'

export default function App() {
  const [page,        setPage]        = useState('overview')
  const [sidebarOpen, setSidebar]     = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [detailValue, setDetailValue] = useState(null)   // valeur IOC sélectionnée

  function navigate(id) {
    setPage(id)
    setDetailValue(null)   // reset du détail à chaque changement de page
    setSidebar(false)
  }

  function openDetail(value) {
    setDetailValue(value)
    setPage('detail')
    setSidebar(false)
  }

  function globalSearch(e) {
    if (e.key === 'Enter' && searchQuery.trim()) {
      setPage('lookup')
      setSidebar(false)
    }
  }

  function renderPage() {
    if (page === 'detail')     return <IndicatorDetail value={detailValue} onBack={() => navigate('indicators')} />
    if (page === 'lookup')     return <Lookup initialQuery={searchQuery} onOpenDetail={openDetail} />
    if (page === 'overview')   return <Overview onOpenDetail={openDetail} />
    if (page === 'indicators') return <Indicators onOpenDetail={openDetail} />
    if (page === 'threats')    return <Threats />
    if (page === 'sources')    return <Sources />
    if (page === 'health')     return <Health />
    return null
  }

  return (
    <div className="flex min-h-screen bg-gray-50 font-sans">
      {sidebarOpen && (
        <div className="fixed inset-0 bg-black/40 z-20 lg:hidden" onClick={() => setSidebar(false)} />
      )}
      <div className={`
        fixed inset-y-0 left-0 z-30 w-56 transform transition-transform duration-200
        lg:relative lg:translate-x-0 lg:flex lg:flex-col
        ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}
      `}>
        <Navbar current={page} onChange={navigate} />
      </div>
      <div className="flex-1 flex flex-col min-w-0">
        <header className="flex items-center gap-3 px-4 lg:px-8 py-3 bg-white border-b border-gray-100 shadow-sm sticky top-0 z-10">
          <button onClick={() => setSidebar(true)} className="lg:hidden p-1.5 rounded-lg text-gray-600 hover:bg-gray-100">
            <Menu size={20} />
          </button>
          <div className="relative flex-1 max-w-lg">
            <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              onKeyDown={globalSearch}
              placeholder="Rechercher un IOC : IP, domaine, email, hash… (Entrée)"
              className="w-full pl-9 pr-4 py-2 text-sm border border-gray-200 rounded-xl bg-gray-50 focus:outline-none focus:ring-2 focus:ring-indigo-300 focus:bg-white transition-colors"
            />
          </div>
          <button
            onClick={() => { if (searchQuery.trim()) setPage('lookup') }}
            disabled={!searchQuery.trim()}
            className="hidden sm:flex items-center gap-1.5 px-4 py-2 bg-indigo-600 text-white text-sm rounded-xl hover:bg-indigo-700 disabled:opacity-40 transition-colors"
          >
            <Search size={13} /> Lookup
          </button>
        </header>
        <main className="flex-1 p-4 lg:p-8 overflow-auto">
          {renderPage()}
        </main>
      </div>
    </div>
  )
}