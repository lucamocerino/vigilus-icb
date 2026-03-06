import { useState, useEffect } from 'react'
import { MapPin, ChevronRight } from 'lucide-react'
import { DIMENSION_COLORS } from '../utils/colors.js'

const REGIONS = [
  'lombardia','lazio','campania','sicilia','veneto','piemonte',
  'emilia-romagna','toscana','puglia','calabria','sardegna',
  'liguria','friuli','trentino',
]

export default function RegionBrief() {
  const [selected, setSelected] = useState(null)
  const [brief, setBrief] = useState(null)
  const [loading, setLoading] = useState(false)

  async function loadRegion(name) {
    setSelected(name)
    setLoading(true)
    try {
      const resp = await fetch(`/api/region/${name}`)
      const data = await resp.json()
      setBrief(data)
    } catch { setBrief(null) }
    setLoading(false)
  }

  return (
    <div className="card">
      <div className="flex items-center gap-2 mb-3">
        <MapPin className="w-4 h-4 text-indigo-400" />
        <h3 className="term-label">DOSSIER REGIONALE</h3>
      </div>

      {/* Region selector */}
      <div className="flex flex-wrap gap-1 mb-3">
        {REGIONS.map(r => (
          <button
            key={r}
            onClick={() => loadRegion(r)}
            className={`text-[10px] px-2 py-0.5 rounded-full transition-colors capitalize ${
              selected === r
                ? 'bg-indigo-600/30 text-indigo-400 border border-indigo-500/30'
                : 'text-gray-500 hover:text-gray-300 border border-transparent'
            }`}
          >
            {r}
          </button>
        ))}
      </div>

      {/* Brief content */}
      {loading ? (
        <p className="text-[10px] text-gray-600 text-center py-3">Caricamento...</p>
      ) : brief && !brief.error ? (
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-sm font-bold text-gray-200 capitalize">{brief.region}</span>
            <span className="text-[10px] text-gray-500">{brief.events_7d} eventi (7gg)</span>
          </div>

          {/* Dimension breakdown */}
          {Object.keys(brief.by_dimension || {}).length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {Object.entries(brief.by_dimension).sort((a,b) => b[1]-a[1]).map(([dim, count]) => (
                <span key={dim} className="text-[10px] px-2 py-0.5 rounded" style={{
                  backgroundColor: (DIMENSION_COLORS[dim] || '#6366f1') + '22',
                  color: DIMENSION_COLORS[dim] || '#6366f1',
                }}>
                  {dim} ({count})
                </span>
              ))}
            </div>
          )}

          {/* Top events */}
          {brief.top_events?.length > 0 && (
            <div className="space-y-1 max-h-32 overflow-y-auto">
              {brief.top_events.slice(0, 5).map((e, i) => (
                <div key={i} className="flex gap-2 text-[10px] py-0.5">
                  <div className="w-1 rounded-full flex-shrink-0" style={{ backgroundColor: DIMENSION_COLORS[e.dimension] || '#6366f1' }} />
                  <span className="text-gray-400 truncate">{e.title}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      ) : brief?.error ? (
        <p className="text-[10px] text-red-400">{brief.error}</p>
      ) : (
        <p className="text-[10px] text-gray-600 text-center py-2">Seleziona una regione per il dossier</p>
      )}
    </div>
  )
}
