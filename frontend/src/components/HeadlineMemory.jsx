import { useState, useEffect, useRef, useCallback } from 'react'
import { Search, Database, Trash2, Brain } from 'lucide-react'
import { searchMemory, storeHeadlines, getMemoryStats, clearMemory } from '../services/headlineMemory.js'
import { DIMENSION_COLORS } from '../utils/colors.js'

export default function HeadlineMemory() {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState([])
  const [stats, setStats] = useState({ total: 0, max: 5000 })
  const [searching, setSearching] = useState(false)
  const [ingesting, setIngesting] = useState(false)
  const debounceRef = useRef(null)

  // Load stats on mount and ingest current headlines
  useEffect(() => {
    getMemoryStats().then(setStats)
    ingestHeadlines()
  }, [])

  async function ingestHeadlines() {
    setIngesting(true)
    try {
      const resp = await fetch('/api/headlines')
      const headlines = await resp.json()
      if (headlines?.length) {
        await storeHeadlines(headlines)
        const s = await getMemoryStats()
        setStats(s)
      }
    } catch {}
    setIngesting(false)
  }

  const doSearch = useCallback(async (q) => {
    if (!q.trim()) { setResults([]); return }
    setSearching(true)
    try {
      const r = await searchMemory(q, 15)
      setResults(r)
    } catch { setResults([]) }
    setSearching(false)
  }, [])

  function handleInput(e) {
    const val = e.target.value
    setQuery(val)
    clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => doSearch(val), 300)
  }

  async function handleClear() {
    if (!confirm('Cancellare tutta la memoria headline?')) return
    await clearMemory()
    setResults([])
    setStats({ total: 0, max: 5000 })
  }

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Brain className="w-4 h-4 text-purple-400" />
          <h3 className="term-label">HEADLINE MEMORY</h3>
          <span className="text-[10px] text-gray-600">
            {stats.total.toLocaleString()} / {stats.max.toLocaleString()} headline indicizzate
          </span>
        </div>
        <div className="flex items-center gap-1">
          {ingesting && <span className="text-[10px] text-purple-400 animate-pulse">indicizzazione...</span>}
          <button onClick={handleClear} className="text-gray-600 hover:text-red-400 transition-colors p-1" title="Cancella memoria">
            <Trash2 className="w-3 h-3" />
          </button>
        </div>
      </div>

      {/* Search input */}
      <div className="flex items-center gap-2 bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 mb-3 focus-within:border-purple-500 transition-colors">
        <Search className="w-3.5 h-3.5 text-gray-500" />
        <input
          value={query}
          onChange={handleInput}
          placeholder="Cerca nella memoria... es. 'iran nucleare', 'cyber attacco', 'nato esercitazione'"
          className="flex-1 bg-transparent text-xs text-gray-200 outline-none placeholder-gray-600"
        />
        {searching && <span className="text-[10px] text-purple-400 animate-pulse">...</span>}
      </div>

      {/* Results */}
      {results.length > 0 ? (
        <div className="space-y-1.5 max-h-64 overflow-y-auto">
          {results.map((r, i) => (
            <div key={i} className="flex items-start gap-2 py-1.5 border-b border-gray-800/50 last:border-0">
              <div
                className="w-1 h-4 rounded-full flex-shrink-0 mt-0.5"
                style={{ backgroundColor: DIMENSION_COLORS[r.dimension] || '#6366f1' }}
              />
              <div className="flex-1 min-w-0">
                <p className="text-xs text-gray-300 leading-snug truncate">{r.title}</p>
                <div className="flex items-center gap-2 mt-0.5">
                  <span className="text-[10px] text-gray-600">{r.source}</span>
                  <span className="text-[10px] text-purple-400">{r.relevance}% match</span>
                  <span className="text-[10px] text-gray-700">
                    {new Date(r.timestamp).toLocaleDateString('it-IT')}
                  </span>
                </div>
              </div>
              {r.url && (
                <a href={r.url} target="_blank" rel="noopener noreferrer" className="text-[10px] text-indigo-500 hover:text-indigo-400 flex-shrink-0">
                  →
                </a>
              )}
            </div>
          ))}
        </div>
      ) : query ? (
        <p className="text-center text-gray-600 text-[10px] py-3">Nessun risultato per "{query}"</p>
      ) : (
        <p className="text-center text-gray-700 text-[10px] py-2">
          Cerca tra le headline storiche indicizzate nel browser
        </p>
      )}
    </div>
  )
}
