import { getLevel } from '../utils/colors.js'

export default function ScoreGauge({ score, level, color, sourcesOk, sourcesTotal }) {
  const lvl          = getLevel(score ?? 0)
  const displayColor = color ?? lvl.color
  const displayLevel = level ?? lvl.label

  const radius        = 70
  const stroke        = 8
  const cx = 90, cy = 90
  const circumference = Math.PI * radius
  const dashOffset    = circumference * (1 - (score ?? 0) / 100)

  return (
    <div className="card flex flex-col items-center gap-3 relative overflow-hidden">
      {/* Corner decorators */}
      <div className="absolute top-0 left-0 w-3 h-3 border-t border-l border-term-dim" />
      <div className="absolute top-0 right-0 w-3 h-3 border-t border-r border-term-dim" />
      <div className="absolute bottom-0 left-0 w-3 h-3 border-b border-l border-term-dim" />
      <div className="absolute bottom-0 right-0 w-3 h-3 border-b border-r border-term-dim" />

      <div className="term-label">// INDICE COMPOSITO</div>

      <div className="relative">
        <svg width="180" height="105" viewBox="0 0 180 105">
          {/* Track */}
          <path
            d={`M ${cx - radius} ${cy} A ${radius} ${radius} 0 0 1 ${cx + radius} ${cy}`}
            fill="none" stroke="#0f1829" strokeWidth={stroke} strokeLinecap="butt"
          />
          {/* Tick marks */}
          {[0,0.25,0.5,0.75,1].map(t => {
            const angle = Math.PI * (1 - t)
            const ix = cx + (radius + 6) * Math.cos(Math.PI - angle)
            const iy = cy - (radius + 6) * Math.sin(Math.PI - angle)
            const ox = cx + (radius + 12) * Math.cos(Math.PI - angle)
            const oy = cy - (radius + 12) * Math.sin(Math.PI - angle)
            return <line key={t} x1={ix} y1={iy} x2={ox} y2={oy} stroke="#1a2540" strokeWidth="1" />
          })}
          {/* Score arc */}
          <path
            d={`M ${cx - radius} ${cy} A ${radius} ${radius} 0 0 1 ${cx + radius} ${cy}`}
            fill="none" stroke={displayColor} strokeWidth={stroke} strokeLinecap="butt"
            strokeDasharray={circumference} strokeDashoffset={dashOffset}
            style={{ transition: 'stroke-dashoffset 1s ease, stroke 0.4s ease', filter: `drop-shadow(0 0 6px ${displayColor}88)` }}
          />
        </svg>

        <div className="absolute inset-0 flex flex-col items-center justify-end pb-1">
          <span className="text-4xl font-bold tabular-nums" style={{ color: displayColor, textShadow: `0 0 20px ${displayColor}66` }}>
            {score != null ? Math.round(score) : '──'}
          </span>
          <span className="text-[10px] text-gray-700">/100</span>
        </div>
      </div>

      {/* Level */}
      <div
        className="w-full text-center py-1 text-sm font-bold tracking-[0.25em] border-y"
        style={{ color: displayColor, borderColor: displayColor + '33', backgroundColor: displayColor + '0d', textShadow: `0 0 12px ${displayColor}44` }}
      >
        {displayLevel}
      </div>

      {/* Confidence dots */}
      {sourcesTotal > 0 && (
        <div className="flex items-center gap-2 text-[10px]">
          <span className="text-gray-600">SRC</span>
          <div className="flex gap-1">
            {Array.from({ length: sourcesTotal }).map((_, i) => (
              <div key={i} className="w-1.5 h-1.5" style={{ backgroundColor: i < sourcesOk ? '#00c48c' : '#1a2540' }} />
            ))}
          </div>
          <span className="text-gray-600">{sourcesOk}/{sourcesTotal} OK</span>
        </div>
      )}

      {/* Scale */}
      <div className="flex gap-1 text-[9px] w-full justify-between px-1 tracking-widest">
        {['CALMO','NORM','ATTN','ELEV','CRIT'].map((l, i) => {
          const colors = ['#00c48c','#3b82f6','#f59f00','#f97316','#ef4444']
          const active = displayLevel.startsWith(l.substring(0,4)) || (l === 'NORM' && displayLevel === 'NORMALE') || (l === 'ATTN' && displayLevel === 'ATTENZIONE') || (l === 'ELEV' && displayLevel === 'ELEVATO') || (l === 'CRIT' && displayLevel === 'CRITICO') || (l === 'CALMO' && displayLevel === 'CALMO')
          return (
            <span key={l} style={{ color: active ? colors[i] : '#1a2540' }}>{l}</span>
          )
        })}
      </div>
    </div>
  )
}
