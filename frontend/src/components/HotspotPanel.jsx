import { useState, useEffect } from 'react'
import { Activity, AlertTriangle, TrendingUp } from 'lucide-react'
import { apiUrl } from '../utils/api.js'

const LEVEL_STYLE = {
  critico: 'bg-red-500/15 text-red-400 border-red-500/30',
  alto:    'bg-orange-500/15 text-orange-400 border-orange-500/30',
  medio:   'bg-yellow-500/15 text-yellow-400 border-yellow-500/30',
}

export default function HotspotPanel() {
  const [hotspots, setHotspots] = useState([])
  const [correlations, setCorrelations] = useState(null)

  useEffect(() => {
    fetch(apiUrl('/api/hotspots')).then(r => r.json()).then(setHotspots).catch(() => {})
    fetch(apiUrl('/api/score/correlations?hours=48')).then(r => r.json()).then(setCorrelations).catch(() => {})
  }, [])

  return (
    <div className="card">
      <div className="flex items-center gap-2 mb-3">
        <Activity className="w-4 h-4 text-orange-400" />
        <h3 className="term-label">HOTSPOT & CORRELAZIONI</h3>
      </div>

      {/* Hotspots */}
      {hotspots.length > 0 && (
        <div className="space-y-1.5 mb-3">
          {hotspots.map((h, i) => (
            <div key={i} className={`flex items-center justify-between px-2 py-1.5 rounded border ${LEVEL_STYLE[h.level] || LEVEL_STYLE.medio}`}>
              <div className="flex items-center gap-2">
                <AlertTriangle className="w-3 h-3 flex-shrink-0" />
                <span className="text-xs font-medium capitalize">{h.dimension}</span>
              </div>
              <div className="flex items-center gap-3 text-[10px]">
                <span>score {h.score}</span>
                <span className={h.delta_48h > 0 ? 'text-red-400' : 'text-green-400'}>
                  Δ48h {h.delta_48h > 0 ? '+' : ''}{h.delta_48h}
                </span>
                <span>{h.event_count} eventi</span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Correlazioni */}
      {correlations?.correlations?.length > 0 && (
        <div className="border-t border-term-border pt-2">
          <p className="text-[10px] text-gray-600 uppercase mb-1">Correlazioni ({correlations.period_hours}h)</p>
          {correlations.correlations.slice(0, 5).map((c, i) => (
            <div key={i} className="flex items-center gap-2 text-[10px] py-0.5">
              <span className="text-gray-400">{c.dim1}</span>
              <span className={c.correlation > 0 ? 'text-red-400' : 'text-cyan-400'}>
                {c.direction === 'positiva' ? '↗↗' : '↗↙'}
              </span>
              <span className="text-gray-400">{c.dim2}</span>
              <span className="text-gray-600 ml-auto">r={c.correlation}</span>
              <span className={`px-1 rounded ${c.strength === 'forte' ? 'bg-red-500/10 text-red-400' : 'bg-yellow-500/10 text-yellow-400'}`}>
                {c.strength}
              </span>
            </div>
          ))}
        </div>
      )}

      {/* Alerts */}
      {correlations?.alerts?.length > 0 && (
        <div className="mt-2 p-2 bg-red-500/10 border border-red-500/20 rounded">
          {correlations.alerts.map((a, i) => (
            <p key={i} className="text-[10px] text-red-400 font-medium">⚠ {a.message}</p>
          ))}
        </div>
      )}

      {hotspots.length === 0 && !correlations?.correlations?.length && (
        <p className="text-[10px] text-gray-600 text-center py-2">Nessun hotspot attivo</p>
      )}
    </div>
  )
}
