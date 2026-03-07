import { useState, useEffect, useRef, useCallback } from 'react'
import { Search, X } from 'lucide-react'
import { DIMENSION_COLORS, DIMENSION_LABELS } from '../utils/colors.js'
import { apiUrl } from '../utils/api.js'

const DIMENSIONS = ['geopolitica', 'terrorismo', 'cyber', 'eversione', 'militare', 'sociale']

const COMMANDS = [
  // Navigazione
  { id: 'nav-dashboard',   label: 'Dashboard',         category: 'Navigazione', action: 'navigate', value: 'dashboard' },
  { id: 'nav-compare',     label: 'Confronto periodi', category: 'Navigazione', action: 'navigate', value: 'compare' },
  { id: 'nav-methodology', label: 'Metodologia',       category: 'Navigazione', action: 'navigate', value: 'methodology' },
  // Dimensioni
  ...DIMENSIONS.map(d => ({
    id: `dim-${d}`, label: `Dimensione: ${DIMENSION_LABELS[d]}`, category: 'Dimensioni',
    action: 'dimension', value: d, color: DIMENSION_COLORS[d],
  })),
  // Azioni
  { id: 'act-export-csv',   label: 'Esporta CSV (30gg)',     category: 'Azioni', action: 'url', value: '/api/export/csv?days=30' },
  { id: 'act-export-report', label: 'Scarica Report',        category: 'Azioni', action: 'url', value: '/api/export/report' },
  { id: 'act-trigger',      label: 'Forza aggiornamento',    category: 'Azioni', action: 'trigger' },
  { id: 'act-share',        label: 'Condividi su Twitter',   category: 'Azioni', action: 'share', value: 'twitter' },
  // Fonti
  { id: 'src-gdelt',   label: 'GDELT Project',    category: 'Fonti', action: 'link', value: 'https://www.gdeltproject.org' },
  { id: 'src-csirt',   label: 'CSIRT Italia',     category: 'Fonti', action: 'link', value: 'https://www.csirt.gov.it' },
  { id: 'src-acled',   label: 'ACLED Data',       category: 'Fonti', action: 'link', value: 'https://acleddata.com' },
  { id: 'src-opensky', label: 'OpenSky Network',  category: 'Fonti', action: 'link', value: 'https://opensky-network.org' },
  { id: 'src-ansa',    label: 'ANSA',             category: 'Fonti', action: 'link', value: 'https://www.ansa.it' },
]

function fuzzyMatch(query, text) {
  const q = query.toLowerCase()
  const t = text.toLowerCase()
  if (t.includes(q)) return true
  let qi = 0
  for (let i = 0; i < t.length && qi < q.length; i++) {
    if (t[i] === q[qi]) qi++
  }
  return qi === q.length
}

export default function CommandPalette({ onNavigate, onDimension }) {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const [selected, setSelected] = useState(0)
  const inputRef = useRef(null)

  const toggle = useCallback(() => {
    setOpen(prev => !prev)
    setQuery('')
    setSelected(0)
  }, [])

  // Cmd+K / Ctrl+K
  useEffect(() => {
    function handler(e) {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault()
        toggle()
      }
      if (e.key === 'Escape' && open) {
        setOpen(false)
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [open, toggle])

  useEffect(() => {
    if (open) inputRef.current?.focus()
  }, [open])

  const filtered = query
    ? COMMANDS.filter(c => fuzzyMatch(query, c.label) || fuzzyMatch(query, c.category))
    : COMMANDS

  const grouped = {}
  for (const cmd of filtered) {
    if (!grouped[cmd.category]) grouped[cmd.category] = []
    grouped[cmd.category].push(cmd)
  }

  function execute(cmd) {
    setOpen(false)
    switch (cmd.action) {
      case 'navigate': onNavigate?.(cmd.value); break
      case 'dimension': onDimension?.(cmd.value); break
      case 'url': window.open(cmd.value, '_blank'); break
      case 'link': window.open(cmd.value, '_blank'); break
      case 'trigger': fetch(apiUrl('/api/score/trigger'), { method: 'POST' }); break
      case 'share': {
        const text = `🛡️ Sentinella Italia — Dashboard OSINT sicurezza nazionale`
        window.open(`https://twitter.com/intent/tweet?text=${encodeURIComponent(text)}`, '_blank')
        break
      }
    }
  }

  function handleKeyDown(e) {
    const items = filtered
    if (e.key === 'ArrowDown') { e.preventDefault(); setSelected(s => Math.min(s + 1, items.length - 1)) }
    if (e.key === 'ArrowUp') { e.preventDefault(); setSelected(s => Math.max(s - 1, 0)) }
    if (e.key === 'Enter' && items[selected]) { execute(items[selected]) }
  }

  if (!open) return null

  return (
    <div className="fixed inset-0 z-[100] flex items-start justify-center pt-[15vh]" onClick={() => setOpen(false)}>
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" />
      <div
        className="relative w-full max-w-lg bg-term-surface border border-term-border rounded-xl shadow-2xl overflow-hidden"
        onClick={e => e.stopPropagation()}
      >
        {/* Input */}
        <div className="flex items-center gap-3 px-4 py-3 border-b border-term-border">
          <Search className="w-4 h-4 text-gray-500 flex-shrink-0" />
          <input
            ref={inputRef}
            value={query}
            onChange={e => { setQuery(e.target.value); setSelected(0) }}
            onKeyDown={handleKeyDown}
            placeholder="Cerca comandi, dimensioni, fonti..."
            className="flex-1 bg-transparent text-sm text-gray-200 outline-none placeholder-gray-600"
          />
          <kbd className="text-[10px] text-gray-600 bg-gray-800 px-1.5 py-0.5 rounded">ESC</kbd>
        </div>

        {/* Risultati */}
        <div className="max-h-80 overflow-y-auto py-2">
          {Object.entries(grouped).map(([cat, cmds]) => (
            <div key={cat}>
              <p className="px-4 py-1 text-[10px] text-gray-600 uppercase tracking-widest">{cat}</p>
              {cmds.map((cmd) => {
                const idx = filtered.indexOf(cmd)
                return (
                  <button
                    key={cmd.id}
                    onClick={() => execute(cmd)}
                    onMouseEnter={() => setSelected(idx)}
                    className={`w-full text-left px-4 py-2 text-sm flex items-center gap-3 transition-colors ${
                      idx === selected ? 'bg-indigo-600/20 text-white' : 'text-gray-400 hover:bg-gray-800/50'
                    }`}
                  >
                    {cmd.color && <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ backgroundColor: cmd.color }} />}
                    {cmd.label}
                  </button>
                )
              })}
            </div>
          ))}
          {filtered.length === 0 && (
            <p className="px-4 py-6 text-center text-gray-600 text-sm">Nessun risultato per "{query}"</p>
          )}
        </div>

        <div className="border-t border-term-border px-4 py-2 flex items-center justify-between text-[10px] text-gray-600">
          <span>↑↓ naviga · ↵ seleziona · esc chiudi</span>
          <span>⌘K per aprire</span>
        </div>
      </div>
    </div>
  )
}
