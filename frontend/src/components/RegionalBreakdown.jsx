import { useState, useEffect } from 'react'
import { MapPin } from 'lucide-react'

const REGION_COLORS = {
  high:   'bg-red-500/20 border-red-500/40 text-red-400',
  medium: 'bg-yellow-500/20 border-yellow-500/40 text-yellow-400',
  low:    'bg-green-500/20 border-green-500/40 text-green-400',
  none:   'bg-gray-500/10 border-gray-500/20 text-gray-600',
}

function getColorClass(intensity) {
  if (intensity >= 70) return REGION_COLORS.high
  if (intensity >= 40) return REGION_COLORS.medium
  if (intensity > 0) return REGION_COLORS.low
  return REGION_COLORS.none
}

const DIM_COLORS = {
  geopolitica: 'bg-indigo-500',
  terrorismo: 'bg-red-500',
  cyber: 'bg-cyan-500',
  eversione: 'bg-amber-500',
  militare: 'bg-slate-400',
  sociale: 'bg-green-500',
}

export default function RegionalBreakdown() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch('/api/map/regional')
      .then(r => r.json())
      .then(d => setData(d))
      .catch(() => setData(null))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="card"><p className="text-gray-600 text-xs text-center py-4">Caricamento dati regionali...</p></div>
  if (!data) return null

  return (
    <div className="card">
      <div className="flex items-center gap-2 mb-4">
        <MapPin className="w-4 h-4 text-indigo-400" />
        <h3 className="term-label">BREAKDOWN REGIONALE</h3>
        <span className="text-[10px] text-gray-600 ml-auto">{data.total_events} eventi totali</span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        {data.regions?.map(region => (
          <div
            key={region.name}
            className={`rounded-lg border p-3 transition-colors ${getColorClass(region.intensity)}`}
          >
            <div className="flex items-center justify-between mb-2">
              <h4 className="font-bold text-sm">{region.name}</h4>
              <span className="text-xs font-mono">{region.event_count} eventi</span>
            </div>

            {/* Barra dimensioni */}
            {Object.keys(region.by_dimension || {}).length > 0 ? (
              <div className="space-y-1 mb-2">
                {Object.entries(region.by_dimension).sort((a, b) => b[1] - a[1]).map(([dim, count]) => (
                  <div key={dim} className="flex items-center gap-2 text-[10px]">
                    <div className={`w-2 h-2 rounded-full ${DIM_COLORS[dim] || 'bg-gray-500'}`} />
                    <span className="text-gray-400 w-16 truncate">{dim}</span>
                    <div className="flex-1 bg-gray-800 rounded-full h-1.5">
                      <div
                        className={`h-1.5 rounded-full ${DIM_COLORS[dim] || 'bg-gray-500'} opacity-60`}
                        style={{ width: `${Math.min(100, (count / Math.max(region.event_count, 1)) * 100)}%` }}
                      />
                    </div>
                    <span className="text-gray-500 w-4 text-right">{count}</span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-[10px] text-gray-600 mb-2">Nessun evento geo-taggato</p>
            )}

            {/* Eventi recenti */}
            {region.recent_events?.length > 0 && (
              <div className="border-t border-gray-700/50 pt-2 mt-2">
                {region.recent_events.slice(0, 3).map((ev, i) => (
                  <p key={i} className="text-[10px] text-gray-500 truncate leading-relaxed">
                    › {ev.title}
                  </p>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
