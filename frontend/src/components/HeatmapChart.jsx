import { useScoreHistory } from '../hooks/useScore.js'
import { getLevel } from '../utils/colors.js'

// Slot orari ufficiali del scheduler
const TIME_SLOTS = ['02:00', '06:00', '10:00', '14:00', '18:00', '22:00']
const SLOT_HOURS = [2, 6, 10, 14, 18, 22]

function slotIndex(date) {
  const h = new Date(date).getHours()
  // Trova lo slot più vicino
  let best = 0
  let bestDist = Infinity
  SLOT_HOURS.forEach((sh, i) => {
    const dist = Math.abs(h - sh)
    if (dist < bestDist) { bestDist = dist; best = i }
  })
  return best
}

function buildGrid(history) {
  // Ultimi 7 giorni
  const today = new Date()
  const days = Array.from({ length: 7 }, (_, i) => {
    const d = new Date(today)
    d.setDate(d.getDate() - (6 - i))
    return d.toISOString().slice(0, 10)
  })

  // Mappa: { "YYYY-MM-DD": { slotIdx: { score, level, color, timestamp } } }
  const map = {}
  days.forEach(d => { map[d] = {} })

  history.forEach(h => {
    const dateKey = new Date(h.timestamp).toISOString().slice(0, 10)
    if (!map[dateKey]) return
    const slot = slotIndex(h.timestamp)
    // Tieni l'ultimo se ci sono collisioni
    map[dateKey][slot] = h
  })

  return { days, map }
}

function dayLabel(isoDate) {
  const d = new Date(isoDate + 'T12:00:00')
  const today = new Date().toISOString().slice(0, 10)
  const yesterday = new Date(Date.now() - 86400000).toISOString().slice(0, 10)
  if (isoDate === today) return 'Oggi'
  if (isoDate === yesterday) return 'Ieri'
  return d.toLocaleDateString('it-IT', { weekday: 'short', day: '2-digit', month: '2-digit' })
}

function Cell({ entry }) {
  if (!entry) {
    return <div className="w-full h-8 rounded bg-gray-800/40" title="Nessun dato" />
  }
  const level = getLevel(entry.score)
  const score = Math.round(entry.score)
  return (
    <div
      className="w-full h-8 rounded flex items-center justify-center text-xs font-bold cursor-default transition-transform hover:scale-105"
      style={{ backgroundColor: level.color + '33', color: level.color, border: `1px solid ${level.color}44` }}
      title={`${entry.timestamp ? new Date(entry.timestamp).toLocaleString('it-IT') : ''} — Score: ${score} (${level.label})`}
    >
      {score}
    </div>
  )
}

export default function HeatmapChart() {
  const { history, loading } = useScoreHistory(7)

  if (loading) {
    return (
      <div className="card flex items-center justify-center h-40 text-gray-600 text-sm">
        Caricamento heatmap...
      </div>
    )
  }

  if (history.length === 0) {
    return (
      <div className="card flex items-center justify-center h-40 text-gray-600 text-sm">
        Nessun dato storico disponibile
      </div>
    )
  }

  const { days, map } = buildGrid(history)

  return (
    <div className="card">
      <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-4">
        Heatmap Score — Ultimi 7 giorni
      </h2>

      <div className="overflow-x-auto">
        <div style={{ minWidth: 420 }}>
          {/* Header slot orari */}
          <div className="grid gap-1.5 mb-1.5" style={{ gridTemplateColumns: '80px repeat(6, 1fr)' }}>
            <div />
            {TIME_SLOTS.map(s => (
              <div key={s} className="text-center text-xs text-gray-600 font-mono">{s}</div>
            ))}
          </div>

          {/* Righe giorni */}
          {days.map(day => (
            <div
              key={day}
              className="grid gap-1.5 mb-1.5 items-center"
              style={{ gridTemplateColumns: '80px repeat(6, 1fr)' }}
            >
              <div className="text-xs text-gray-500 pr-2 text-right">{dayLabel(day)}</div>
              {SLOT_HOURS.map((_, slotIdx) => (
                <Cell key={slotIdx} entry={map[day]?.[slotIdx] ?? null} />
              ))}
            </div>
          ))}
        </div>
      </div>

      {/* Legenda */}
      <div className="flex flex-wrap gap-3 mt-4 pt-3 border-t border-gray-800">
        {[
          { label: 'Calmo', color: '#22c55e' },
          { label: 'Normale', color: '#3b82f6' },
          { label: 'Attenzione', color: '#eab308' },
          { label: 'Elevato', color: '#f97316' },
          { label: 'Critico', color: '#ef4444' },
        ].map(l => (
          <div key={l.label} className="flex items-center gap-1.5 text-xs text-gray-500">
            <div className="w-3 h-3 rounded" style={{ backgroundColor: l.color + '55', border: `1px solid ${l.color}88` }} />
            {l.label}
          </div>
        ))}
        <div className="flex items-center gap-1.5 text-xs text-gray-500">
          <div className="w-3 h-3 rounded bg-gray-800/40" />
          Nessun dato
        </div>
      </div>
    </div>
  )
}
