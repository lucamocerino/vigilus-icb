import { useState, useEffect } from 'react'
import { ExternalLink } from 'lucide-react'
import { DIMENSION_COLORS, DIMENSION_LABELS } from '../utils/colors.js'
import { formatDate } from '../utils/format.js'
import { apiUrl } from '../utils/api.js'

const DIMENSIONS = ['geopolitica', 'terrorismo', 'cyber', 'eversione', 'militare', 'sociale']

export default function EventFeed() {
  const [events, setEvents] = useState([])
  const [filter, setFilter] = useState(null)

  useEffect(() => {
    const url = filter
      ? apiUrl(`/api/events/latest?dimension=${filter}&limit=20`)
      : apiUrl('/api/events/latest?limit=20')
    fetch(url)
      .then(r => r.json())
      .then(setEvents)
      .catch(() => {})
  }, [filter])

  return (
    <div className="card relative overflow-hidden">
      <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-cyan-500/20 to-transparent" />
      <div className="flex items-center justify-between mb-3">
        <div className="term-label">
          // ULTIMI EVENTI
        </div>
        <div className="flex gap-1 flex-wrap">
          <button
            onClick={() => setFilter(null)}
            className={`text-xs px-2 py-0.5 rounded-full transition-colors ${
              !filter ? 'bg-gray-700 text-white' : 'text-gray-500 hover:text-gray-300'
            }`}
          >
            Tutti
          </button>
          {DIMENSIONS.map(d => (
            <button
              key={d}
              onClick={() => setFilter(d === filter ? null : d)}
              className="text-xs px-2 py-0.5 rounded-full transition-colors"
              style={{
                backgroundColor: filter === d ? DIMENSION_COLORS[d] + '33' : undefined,
                color: filter === d ? DIMENSION_COLORS[d] : '#6b7280',
                border: `1px solid ${filter === d ? DIMENSION_COLORS[d] + '66' : 'transparent'}`,
              }}
            >
              {DIMENSION_LABELS[d]}
            </button>
          ))}
        </div>
      </div>

      <div className="space-y-2 max-h-96 overflow-y-auto pr-1">
        {events.length === 0 && (
          <p className="text-gray-600 text-sm text-center py-8">
            Nessun evento disponibile
          </p>
        )}
        {events.map(e => (
          <div key={e.id} className="flex gap-3 py-2 border-b border-gray-800/50 last:border-0">
            <div
              className="w-1 rounded-full flex-shrink-0 mt-1"
              style={{ backgroundColor: DIMENSION_COLORS[e.dimension] ?? '#6b7280' }}
            />
            <div className="flex-1 min-w-0">
              <div className="flex items-start justify-between gap-2">
                <p className="text-sm text-gray-300 leading-snug line-clamp-2">
                  {e.title}
                </p>
                {e.url && (
                  <a
                    href={e.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex-shrink-0 text-gray-600 hover:text-gray-400"
                  >
                    <ExternalLink className="w-3 h-3" />
                  </a>
                )}
              </div>
              <div className="flex gap-2 mt-1">
                <span
                  className="text-xs px-1.5 py-0.5 rounded"
                  style={{
                    backgroundColor: (DIMENSION_COLORS[e.dimension] ?? '#6b7280') + '22',
                    color: DIMENSION_COLORS[e.dimension] ?? '#6b7280',
                  }}
                >
                  {DIMENSION_LABELS[e.dimension] ?? e.dimension}
                </span>
                <span className="text-xs text-gray-600">{formatDate(e.event_date)}</span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
