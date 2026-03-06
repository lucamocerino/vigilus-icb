import { useState } from 'react'
import { Search, X } from 'lucide-react'
import { DIMENSION_COLORS, DIMENSION_LABELS } from '../utils/colors.js'
import { formatDate } from '../utils/format.js'

export default function EventSearch() {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(false)
  const [searched, setSearched] = useState(false)

  async function doSearch(e) {
    e?.preventDefault()
    if (!query.trim()) return
    setLoading(true)
    setSearched(true)
    try {
      const resp = await fetch(`/api/events/search?q=${encodeURIComponent(query)}&days=30&limit=30`)
      const data = await resp.json()
      setResults(data)
    } catch {
      setResults([])
    }
    setLoading(false)
  }

  return (
    <div className="card">
      <div className="flex items-center gap-2 mb-3">
        <Search className="w-4 h-4 text-indigo-400" />
        <h3 className="term-label">RICERCA EVENTI</h3>
      </div>

      <form onSubmit={doSearch} className="flex gap-2 mb-3">
        <div className="flex-1 flex items-center gap-2 bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 focus-within:border-indigo-500 transition-colors">
          <Search className="w-3 h-3 text-gray-500 flex-shrink-0" />
          <input
            value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder="ransomware, nato, protesta..."
            className="flex-1 bg-transparent text-xs text-gray-200 outline-none placeholder-gray-600"
          />
          {query && (
            <button type="button" onClick={() => { setQuery(''); setResults([]); setSearched(false) }} className="text-gray-600 hover:text-gray-400">
              <X className="w-3 h-3" />
            </button>
          )}
        </div>
        <button type="submit" disabled={loading || !query.trim()} className="px-3 py-1.5 bg-indigo-600 rounded-lg text-xs text-white hover:bg-indigo-500 disabled:opacity-40 transition-colors">
          {loading ? '...' : 'Cerca'}
        </button>
      </form>

      {results.length > 0 ? (
        <div className="space-y-1.5 max-h-64 overflow-y-auto">
          {results.map((e, i) => (
            <div key={i} className="flex gap-2 py-1.5 border-b border-gray-800/50 last:border-0">
              <div className="w-1 rounded-full flex-shrink-0 mt-1" style={{ backgroundColor: DIMENSION_COLORS[e.dimension] || '#6366f1' }} />
              <div className="flex-1 min-w-0">
                <p className="text-xs text-gray-300 leading-snug line-clamp-2">{e.title}</p>
                <div className="flex gap-2 mt-0.5">
                  <span className="text-[10px] px-1.5 py-0.5 rounded" style={{
                    backgroundColor: (DIMENSION_COLORS[e.dimension] || '#6366f1') + '22',
                    color: DIMENSION_COLORS[e.dimension] || '#6366f1',
                  }}>
                    {DIMENSION_LABELS[e.dimension] || e.dimension}
                  </span>
                  <span className="text-[10px] text-gray-600">{e.source}</span>
                  <span className="text-[10px] text-gray-700">{formatDate(e.event_date)}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : searched && !loading ? (
        <p className="text-[10px] text-gray-600 text-center py-3">Nessun risultato per "{query}"</p>
      ) : null}
    </div>
  )
}
