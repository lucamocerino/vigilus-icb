import { useState, useEffect } from 'react'
import { FileText, TrendingUp, AlertTriangle } from 'lucide-react'

export default function DailyDigest() {
  const [digest, setDigest] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch('/api/digest/daily')
      .then(r => r.json())
      .then(setDigest)
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="card"><p className="text-gray-600 text-xs text-center py-4">Caricamento digest...</p></div>
  if (!digest) return null

  const s = digest.score || {}
  const deltaColor = s.delta > 3 ? 'text-red-400' : s.delta < -3 ? 'text-green-400' : 'text-gray-500'

  return (
    <div className="card">
      <div className="flex items-center gap-2 mb-3">
        <FileText className="w-4 h-4 text-indigo-400" />
        <h3 className="term-label">DAILY DIGEST — 24H</h3>
      </div>

      {/* Score summary */}
      <div className="flex items-center gap-4 mb-3 pb-3 border-b border-term-border">
        <div>
          <span className="text-2xl font-bold text-gray-200">{s.current?.toFixed(1) ?? '—'}</span>
          <span className="text-xs text-gray-500 ml-1">/100</span>
        </div>
        {s.delta != null && (
          <span className={`text-sm font-bold ${deltaColor}`}>
            {s.delta > 0 ? '▲' : s.delta < 0 ? '▼' : '─'} {s.delta > 0 ? '+' : ''}{s.delta}
          </span>
        )}
        <span className="text-[10px] text-gray-600 uppercase">{s.direction}</span>
      </div>

      {/* Dimension changes */}
      {digest.dimensions?.filter(d => d.delta && Math.abs(d.delta) > 1).length > 0 && (
        <div className="mb-3">
          <p className="text-[10px] text-gray-600 uppercase mb-1">Variazioni dimensioni</p>
          <div className="flex flex-wrap gap-1.5">
            {digest.dimensions.filter(d => d.delta && Math.abs(d.delta) > 1).map(d => (
              <span key={d.dimension} className={`text-[10px] px-2 py-0.5 rounded ${
                d.delta > 3 ? 'bg-red-500/10 text-red-400' : d.delta < -3 ? 'bg-green-500/10 text-green-400' : 'bg-gray-500/10 text-gray-500'
              }`}>
                {d.dimension} {d.delta > 0 ? '+' : ''}{d.delta}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Anomalies */}
      {digest.anomalies?.length > 0 && (
        <div className="mb-3">
          <p className="text-[10px] text-gray-600 uppercase mb-1 flex items-center gap-1">
            <AlertTriangle className="w-3 h-3 text-yellow-500" /> Anomalie
          </p>
          {digest.anomalies.slice(0, 3).map((a, i) => (
            <p key={i} className="text-[10px] text-gray-400">
              ⚠ {a.dimension}/{a.proxy}: z={a.z_score}σ ({a.direction})
            </p>
          ))}
        </div>
      )}

      {/* Summary text */}
      <p className="text-xs text-gray-400 leading-relaxed italic">{digest.summary}</p>

      {/* Event count */}
      {digest.events?.total > 0 && (
        <p className="text-[10px] text-gray-600 mt-2">
          {digest.events.total} eventi nelle ultime 24h
        </p>
      )}
    </div>
  )
}
