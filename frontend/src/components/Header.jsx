import { useState, useEffect } from 'react'
import { DIMENSION_COLORS, DIMENSION_LABELS } from '../utils/colors.js'

const DIM_SHORT = {
  geopolitica: 'GEO',
  terrorismo:  'TER',
  cyber:       'CYB',
  eversione:   'EVE',
  militare:    'MIL',
  sociale:     'SOC',
}

function LiveClock() {
  const [time, setTime] = useState(() => new Date())
  useEffect(() => {
    const t = setInterval(() => setTime(new Date()), 1000)
    return () => clearInterval(t)
  }, [])
  return (
    <span className="tabular-nums text-gray-400">
      {time.toLocaleTimeString('it-IT', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
    </span>
  )
}

export default function Header({ lastUpdate, score, dimensions, sourcesOk, sourcesTotal }) {
  return (
    <header className="border-b border-term-border bg-term-surface sticky top-0 z-50">

      {/* Riga 1 — status bar */}
      <div className="border-b border-term-muted px-3 sm:px-4 py-1.5 flex items-center justify-between text-xs text-gray-500">
        <div className="flex items-center gap-2 sm:gap-4">
          <span className="text-gray-300 font-semibold tracking-widest text-[10px] sm:text-xs">VIGILUS//ICB</span>
          <span className="text-term-dim hidden sm:inline">ITALY CRISIS BOARD v1.0</span>
        </div>
        <div className="flex items-center gap-2 sm:gap-4">
          {sourcesTotal > 0 && (
            <span className={`hidden xs:inline ${sourcesOk === sourcesTotal ? 'text-calmo' : 'text-elevato'}`}>
              SRC {sourcesOk}/{sourcesTotal}
            </span>
          )}
          {lastUpdate && (
            <span className="hidden sm:inline">UPD {new Date(lastUpdate).toLocaleTimeString('it-IT', { hour: '2-digit', minute: '2-digit' })}</span>
          )}
          <span className="flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-calmo animate-pulse inline-block" />
            <LiveClock />
          </span>
        </div>
      </div>

      {/* Riga 2 — ticker dimensioni */}
      {dimensions?.length > 0 && (
        <div className="px-3 sm:px-4 py-1.5 flex items-center gap-0 overflow-x-auto text-[10px] sm:text-xs border-b border-term-muted scrollbar-none">
          {['geopolitica','terrorismo','cyber','eversione','militare','sociale'].map((dim, i) => {
            const d = dimensions.find(x => x.dimension === dim)
            if (!d) return null
            const trend = d.trend ?? 0
            const color = DIMENSION_COLORS[dim]
            const arrow = trend > 2 ? '▲' : trend < -2 ? '▼' : '─'
            const trendColor = trend > 2 ? '#ef4444' : trend < -2 ? '#00c48c' : '#4a5568'
            return (
              <span key={dim} className="flex items-center shrink-0">
                {i > 0 && <span className="mx-3 text-term-dim">│</span>}
                <span style={{ color }} className="font-semibold">{DIM_SHORT[dim]}</span>
                <span className="text-gray-200 ml-1.5 tabular-nums">{Math.round(d.score)}</span>
                <span style={{ color: trendColor }} className="ml-0.5 text-[10px]">{arrow}</span>
                {trend !== 0 && (
                  <span style={{ color: trendColor }} className="ml-0.5 tabular-nums text-[10px]">
                    {trend > 0 ? '+' : ''}{Math.round(trend)}
                  </span>
                )}
              </span>
            )
          })}
          {score != null && (
            <>
              <span className="mx-3 text-term-dim">║</span>
              <span className="text-gray-400">INDICE</span>
              <span className="text-gray-100 ml-1.5 font-bold tabular-nums">{score.toFixed(1)}</span>
            </>
          )}
        </div>
      )}

      {/* Riga 3 — disclaimer */}
      <div className="px-3 sm:px-4 py-1 bg-yellow-950/20 border-b border-yellow-900/20">
        <p className="text-[9px] sm:text-[10px] text-yellow-600/70 tracking-wide">
          [!] NON è un livello di allerta ufficiale. Anomalie statistiche su dati pubblici.
        </p>
      </div>

    </header>
  )
}
