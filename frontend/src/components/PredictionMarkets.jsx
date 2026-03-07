import { useState, useEffect } from 'react'
import { Zap } from 'lucide-react'
import { apiUrl } from '../utils/api.js'

const CATEGORY_COLORS = {
  geopolitica: 'text-indigo-400',
  cyber: 'text-cyan-400',
  militare: 'text-slate-300',
  sociale: 'text-green-400',
  eversione: 'text-amber-400',
  terrorismo: 'text-red-400',
}

export default function PredictionMarkets() {
  const [predictions, setPredictions] = useState([])

  useEffect(() => {
    fetch(apiUrl('/api/predictions')).then(r => r.json()).then(setPredictions).catch(() => {})
  }, [])

  if (!predictions.length) return null

  return (
    <div className="card">
      <div className="flex items-center gap-2 mb-3">
        <Zap className="w-4 h-4 text-purple-400" />
        <h3 className="term-label">PREDICTION MARKETS</h3>
      </div>

      <div className="space-y-1.5">
        {predictions.map((p, i) => {
          const pct = Math.round(p.probability * 100)
          const color = pct >= 50 ? 'bg-red-500' : pct >= 25 ? 'bg-yellow-500' : 'bg-green-500'
          return (
            <div key={i} className="py-1.5 border-b border-gray-800/50 last:border-0">
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs text-gray-300 leading-snug flex-1 pr-2">{p.question}</span>
                <span className={`text-sm font-bold tabular-nums ${pct >= 50 ? 'text-red-400' : pct >= 25 ? 'text-yellow-400' : 'text-green-400'}`}>
                  {pct}%
                </span>
              </div>
              <div className="flex items-center gap-2">
                <div className="flex-1 h-1 bg-gray-800 rounded-full overflow-hidden">
                  <div className={`h-full rounded-full ${color} opacity-60`} style={{ width: `${pct}%` }} />
                </div>
                <span className={`text-[9px] ${CATEGORY_COLORS[p.category] || 'text-gray-500'}`}>{p.category}</span>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
