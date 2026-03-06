import { useState, useEffect } from 'react'
import { Bell, Plus, X, AlertTriangle } from 'lucide-react'

export default function KeywordMonitor() {
  const [keywords, setKeywords] = useState(() => {
    try { return JSON.parse(localStorage.getItem('vigilus_monitors') || '[]') } catch { return [] }
  })
  const [input, setInput] = useState('')
  const [headlines, setHeadlines] = useState([])
  const [matches, setMatches] = useState([])
  const [showAdd, setShowAdd] = useState(false)

  // Salva in localStorage
  useEffect(() => {
    localStorage.setItem('vigilus_monitors', JSON.stringify(keywords))
  }, [keywords])

  // Fetch headlines e cerca match
  useEffect(() => {
    if (!keywords.length) return
    fetch('/api/headlines')
      .then(r => r.json())
      .then(data => {
        setHeadlines(data)
        const found = []
        for (const h of data) {
          const text = h.title.toLowerCase()
          for (const kw of keywords) {
            if (text.includes(kw.toLowerCase())) {
              found.push({ ...h, matchedKeyword: kw })
              break
            }
          }
        }
        setMatches(found)
      })
      .catch(() => {})
  }, [keywords])

  function addKeyword() {
    const kw = input.trim()
    if (kw && !keywords.includes(kw)) {
      setKeywords(prev => [...prev, kw])
    }
    setInput('')
    setShowAdd(false)
  }

  function removeKeyword(kw) {
    setKeywords(prev => prev.filter(k => k !== kw))
  }

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Bell className="w-4 h-4 text-indigo-400" />
          <h3 className="term-label">KEYWORD MONITOR</h3>
          {matches.length > 0 && (
            <span className="flex items-center gap-1 text-[10px] text-red-400 bg-red-500/10 px-1.5 py-0.5 rounded-full">
              <AlertTriangle className="w-3 h-3" /> {matches.length} match
            </span>
          )}
        </div>
        <button
          onClick={() => setShowAdd(!showAdd)}
          className="text-gray-500 hover:text-indigo-400 transition-colors"
        >
          <Plus className="w-4 h-4" />
        </button>
      </div>

      {/* Input aggiunta */}
      {showAdd && (
        <div className="flex gap-2 mb-3">
          <input
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && addKeyword()}
            placeholder="es. terrorismo, nato, cyber..."
            className="flex-1 bg-gray-800 border border-gray-700 rounded px-2 py-1 text-xs text-gray-200 outline-none focus:border-indigo-500"
            autoFocus
          />
          <button onClick={addKeyword} className="px-2 py-1 bg-indigo-600 rounded text-xs text-white hover:bg-indigo-500">
            Aggiungi
          </button>
        </div>
      )}

      {/* Keyword attive */}
      {keywords.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mb-3">
          {keywords.map(kw => {
            const hasMatch = matches.some(m => m.matchedKeyword === kw)
            return (
              <span
                key={kw}
                className={`inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full border ${
                  hasMatch
                    ? 'border-red-500/50 bg-red-500/10 text-red-400'
                    : 'border-gray-700 text-gray-500'
                }`}
              >
                {hasMatch && <span className="w-1.5 h-1.5 rounded-full bg-red-400 animate-pulse" />}
                {kw}
                <button onClick={() => removeKeyword(kw)} className="hover:text-white ml-0.5">
                  <X className="w-3 h-3" />
                </button>
              </span>
            )
          })}
        </div>
      )}

      {/* Match trovati */}
      {matches.length > 0 ? (
        <div className="space-y-1.5 max-h-40 overflow-y-auto">
          {matches.slice(0, 8).map((m, i) => (
            <div key={i} className="flex gap-2 text-xs">
              <span className="text-red-400 flex-shrink-0">▸</span>
              <span className="text-gray-400 truncate">{m.title}</span>
              <span className="text-gray-600 flex-shrink-0 text-[10px]">{m.source}</span>
            </div>
          ))}
        </div>
      ) : keywords.length > 0 ? (
        <p className="text-gray-600 text-[10px]">Nessuna corrispondenza nei titoli correnti</p>
      ) : (
        <p className="text-gray-600 text-[10px]">Aggiungi keyword per monitorare i titoli in tempo reale</p>
      )}
    </div>
  )
}
