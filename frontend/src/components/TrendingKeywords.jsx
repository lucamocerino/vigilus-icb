import { useState, useEffect } from 'react'
import { TrendingUp, AlertTriangle, Zap } from 'lucide-react'
import { DIMENSION_COLORS } from '../utils/colors.js'

const DIRECTION_STYLE = {
  spike:  { icon: '⚡', color: 'text-red-400',    bg: 'bg-red-500/10' },
  rising: { icon: '↑',  color: 'text-yellow-400', bg: 'bg-yellow-500/10' },
  active: { icon: '●',  color: 'text-gray-400',   bg: 'bg-gray-500/10' },
}

export default function TrendingKeywords() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    function load() {
      fetch('/api/trending')
        .then(r => r.json())
        .then(d => setData(d))
        .catch(() => {})
        .finally(() => setLoading(false))
    }
    load()
    const interval = setInterval(load, 3 * 60 * 1000)
    return () => clearInterval(interval)
  }, [])

  if (loading) return <div className="card"><p className="text-gray-600 text-xs text-center py-4">Analisi keywords...</p></div>
  if (!data?.keywords?.length) return null

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <TrendingUp className="w-4 h-4 text-indigo-400" />
          <h3 className="term-label">TRENDING KEYWORDS</h3>
        </div>
        <div className="flex items-center gap-3 text-[10px]">
          {data.spike_count > 0 && (
            <span className="flex items-center gap-1 text-red-400">
              <Zap className="w-3 h-3" /> {data.spike_count} spike
            </span>
          )}
          <span className="text-gray-600">{data.total_headlines} titoli analizzati</span>
        </div>
      </div>

      <div className="space-y-1.5">
        {data.keywords.slice(0, 15).map((kw, i) => {
          const style = DIRECTION_STYLE[kw.direction] || DIRECTION_STYLE.active
          const maxZ = Math.max(...data.keywords.map(k => Math.abs(k.z_score)), 1)
          const barWidth = Math.min(100, (Math.abs(kw.z_score) / maxZ) * 100)

          return (
            <div key={kw.keyword} className="flex items-center gap-2 group">
              <span className={`text-[10px] w-5 text-center ${style.color}`}>
                {style.icon}
              </span>

              <span className="text-xs text-gray-300 font-medium w-28 truncate">
                {kw.keyword}
              </span>

              <div className="flex-1 h-3 bg-gray-800/50 rounded-full overflow-hidden">
                <div
                  className="h-full rounded-full transition-all duration-500"
                  style={{
                    width: `${barWidth}%`,
                    backgroundColor: kw.is_security
                      ? '#ef4444'
                      : (DIMENSION_COLORS[kw.dimension] || '#6366f1'),
                    opacity: 0.6,
                  }}
                />
              </div>

              <span className="text-[10px] text-gray-500 tabular-nums w-8 text-right">
                {kw.count}×
              </span>

              <span className={`text-[10px] tabular-nums w-10 text-right font-medium ${
                kw.z_score >= 2 ? 'text-red-400' : kw.z_score >= 1 ? 'text-yellow-400' : 'text-gray-500'
              }`}>
                {kw.z_score > 0 ? '+' : ''}{kw.z_score}σ
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}
