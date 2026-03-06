import { DIMENSION_COLORS, DIMENSION_LABELS, getLevel } from '../utils/colors.js'

const DIM_SHORT = {
  geopolitica: 'GEOPOLIT',
  terrorismo:  'TERRORISM',
  cyber:       'CYBER   ',
  eversione:   'EVERSIONE',
  militare:    'MILITARE ',
  sociale:     'SOCIALE  ',
}

export default function DimensionCard({ dimension, score, trend, onClick }) {
  const color = DIMENSION_COLORS[dimension] ?? '#6b7280'
  const level = getLevel(score ?? 0)
  const pct   = Math.round(score ?? 0)

  const trendSign  = trend == null ? null : trend > 2 ? '▲' : trend < -2 ? '▼' : '─'
  const trendColor = trend > 2 ? '#ef4444' : trend < -2 ? '#00c48c' : '#4a5568'

  const barFilled  = Math.round(pct / 10)

  return (
    <button
      onClick={onClick}
      className="card text-left w-full hover:border-term-dim transition-colors cursor-pointer group relative overflow-hidden"
    >
      {/* accent line top */}
      <div className="absolute top-0 left-0 right-0 h-px" style={{ backgroundColor: color + '66' }} />

      <div className="term-label mb-1" style={{ color: color + 'cc' }}>
        {DIM_SHORT[dimension] ?? dimension.toUpperCase()}
      </div>

      {/* Score principale */}
      <div className="flex items-end gap-1.5 mb-2">
        <span className="text-2xl font-bold tabular-nums" style={{ color }}>
          {score != null ? Math.round(score) : '──'}
        </span>
        <span className="text-xs text-gray-700 mb-0.5">/100</span>
        {trendSign && (
          <span className="text-xs font-semibold mb-0.5 tabular-nums" style={{ color: trendColor }}>
            {trendSign}{trend != null && Math.abs(trend) > 0.5 ? Math.round(Math.abs(trend)) : ''}
          </span>
        )}
      </div>

      {/* Bar ASCII-style */}
      <div className="text-[9px] text-gray-700 font-mono tracking-tighter mb-1.5" aria-hidden>
        {'█'.repeat(barFilled)}{'░'.repeat(10 - barFilled)}
      </div>

      {/* Level */}
      <div className="text-[10px] font-semibold tracking-widest" style={{ color: level.color }}>
        {level.label}
      </div>
    </button>
  )
}
