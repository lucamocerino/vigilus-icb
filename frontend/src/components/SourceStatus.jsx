import { useState, useEffect } from 'react'
import { formatDate } from '../utils/format.js'
import { apiUrl } from '../utils/api.js'

export default function SourceStatus() {
  const [sources, setSources] = useState([])

  useEffect(() => {
    fetch(apiUrl('/api/sources/status'))
      .then(r => r.json())
      .then(setSources)
      .catch(() => {})
  }, [])

  return (
    <div className="card relative overflow-hidden">
      <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-indigo-500/30 to-transparent" />
      <div className="term-label mb-3">// STATO FONTI</div>

      <div className="space-y-1">
        {sources.length === 0 && (
          <p className="text-gray-700 text-xs">── NESSUNA FONTE REGISTRATA ──</p>
        )}
        {sources.map(s => (
          <div key={s.name} className="flex items-center justify-between text-xs py-1 border-b border-term-border last:border-0">
            <div className="flex items-center gap-2">
              <div className={`w-1.5 h-1.5 ${s.is_healthy ? 'bg-calmo' : 'bg-critico'}`}
                style={s.is_healthy ? { boxShadow: '0 0 4px #00c48c' } : {}} />
              <span className={s.is_healthy ? 'text-gray-300' : 'text-gray-600 line-through'}>
                {s.display_name.toUpperCase()}
              </span>
            </div>
            <div className="text-right tabular-nums">
              <p className="text-gray-600 text-[10px]">
                {s.last_success ? formatDate(s.last_success) : 'NEVER'}
              </p>
              {s.records_last_run > 0 && (
                <p className="text-term-dim text-[10px]">{s.records_last_run} rec</p>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
