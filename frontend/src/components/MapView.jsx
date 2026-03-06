import { useEffect, useState, useRef } from 'react'
import { MapContainer, TileLayer, CircleMarker, Marker, Popup, useMap } from 'react-leaflet'
import { DIMENSION_COLORS, DIMENSION_LABELS } from '../utils/colors.js'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

// Force Leaflet to recalculate size when container resizes
function ResizeHandler() {
  const map = useMap()
  useEffect(() => {
    const observer = new ResizeObserver(() => map.invalidateSize())
    observer.observe(map.getContainer())
    // Also invalidate after a short delay for initial render
    const timer = setTimeout(() => map.invalidateSize(), 200)
    return () => { observer.disconnect(); clearTimeout(timer) }
  }, [map])
  return null
}

const LAYER_CONFIG = {
  events:         { label: 'Eventi',         color: '#6366f1' },
  military:       { label: 'Basi NATO',      color: '#ef4444' },
  infrastructure: { label: 'Infrastrutture', color: '#f59e0b' },
  earthquakes:    { label: 'Terremoti',      color: '#f97316' },
  flights:        { label: 'Voli Mil.',      color: '#22d3ee' },
  convergence:    { label: 'Convergenza',    color: '#a855f7' },
}

const INFRA_ICONS = {
  port:            '⚓',
  airport:         '✈',
  energy:          '⚡',
  pipeline:        '🔴',
  submarine_cable: '🔵',
  nato:            '★',
  army:            '⬟',
  navy:            '▲',
}

function makeIcon(emoji, color) {
  return L.divIcon({
    className: '',
    html: `<div style="font-size:16px;text-shadow:0 0 6px ${color};filter:drop-shadow(0 0 2px ${color})">${emoji}</div>`,
    iconSize: [20, 20],
    iconAnchor: [10, 10],
  })
}

export default function MapView() {
  const [events, setEvents] = useState([])
  const [layers, setLayers] = useState({ events: true, military: true, infrastructure: false, earthquakes: true, flights: false, convergence: false })
  const [militaryData, setMilitaryData] = useState(null)
  const [infraData, setInfraData] = useState(null)
  const [quakeData, setQuakeData] = useState(null)
  const [flightData, setFlightData] = useState(null)
  const [convergenceData, setConvergenceData] = useState(null)

  useEffect(() => {
    fetch('/api/map/events').then(r => r.json()).then(setEvents).catch(() => {})
    fetch('/api/layers/all').then(r => r.json()).then(data => {
      setMilitaryData(data.military)
      setInfraData(data.infrastructure)
    }).catch(() => {})
    fetch('/api/earthquakes').then(r => r.json()).then(setQuakeData).catch(() => {})
    fetch('/api/flights').then(r => r.json()).then(setFlightData).catch(() => {})
    fetch('/api/map/convergence').then(r => r.json()).then(setConvergenceData).catch(() => {})
  }, [])

  const toggleLayer = (key) => setLayers(prev => ({ ...prev, [key]: !prev[key] }))

  return (
    <div className="h-full flex flex-col">
      <div className="flex items-center justify-between mb-0 px-2 py-1.5 bg-term-surface border-b border-term-border flex-shrink-0">
        <h2 className="term-label">MAPPA OPERATIVA</h2>
        <div className="flex gap-1.5">
          {Object.entries(LAYER_CONFIG).map(([key, cfg]) => (
            <button
              key={key}
              onClick={() => toggleLayer(key)}
              className={`text-[10px] px-2 py-1 rounded-full border transition-all ${
                layers[key]
                  ? 'border-current opacity-100'
                  : 'border-gray-700 opacity-40 hover:opacity-70'
              }`}
              style={{ color: cfg.color }}
            >
              {cfg.label}
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 min-h-0" style={{ minHeight: '300px' }}>
        <MapContainer
          center={[41.87, 12.57]}
          zoom={6}
          style={{ height: '100%', width: '100%' }}
          scrollWheelZoom={true}
        >
          <ResizeHandler />
          <TileLayer
            url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
            attribution='&copy; <a href="https://carto.com/">CARTO</a>'
          />

          {/* Layer: Eventi RSS */}
          {layers.events && events.map((ev, i) => (
            <CircleMarker
              key={`ev-${i}`}
              center={[ev.lat, ev.lon]}
              radius={6}
              pathOptions={{
                color: DIMENSION_COLORS[ev.dimension] ?? '#6366f1',
                fillColor: DIMENSION_COLORS[ev.dimension] ?? '#6366f1',
                fillOpacity: 0.7, weight: 1,
              }}
            >
              <Popup>
                <div style={{ maxWidth: 220 }}>
                  <span style={{ fontSize: 10, fontWeight: 600, color: DIMENSION_COLORS[ev.dimension], textTransform: 'uppercase' }}>
                    {DIMENSION_LABELS[ev.dimension] ?? ev.dimension}
                  </span>
                  <p style={{ margin: '4px 0', fontSize: 12, lineHeight: 1.4 }}>{ev.title}</p>
                  <p style={{ fontSize: 10, color: '#9ca3af' }}>{ev.location}</p>
                </div>
              </Popup>
            </CircleMarker>
          ))}

          {/* Layer: Basi militari */}
          {layers.military && militaryData?.features?.map((f, i) => (
            <Marker
              key={`mil-${i}`}
              position={[f.geometry.coordinates[1], f.geometry.coordinates[0]]}
              icon={makeIcon(INFRA_ICONS[f.properties.type] || '★', '#ef4444')}
            >
              <Popup>
                <div style={{ maxWidth: 200 }}>
                  <p style={{ fontWeight: 700, fontSize: 12 }}>{f.properties.name}</p>
                  <p style={{ fontSize: 10, color: '#9ca3af' }}>
                    {f.properties.nation} — {f.properties.aircraft}
                  </p>
                </div>
              </Popup>
            </Marker>
          ))}

          {/* Layer: Infrastrutture critiche */}
          {layers.infrastructure && infraData?.features?.map((f, i) => (
            <Marker
              key={`infra-${i}`}
              position={[f.geometry.coordinates[1], f.geometry.coordinates[0]]}
              icon={makeIcon(INFRA_ICONS[f.properties.type] || '●', '#f59e0b')}
            >
              <Popup>
                <div style={{ maxWidth: 200 }}>
                  <p style={{ fontWeight: 700, fontSize: 12 }}>{f.properties.name}</p>
                  <p style={{ fontSize: 10, color: '#9ca3af' }}>
                    {f.properties.type} — importanza {f.properties.importance}
                  </p>
                </div>
              </Popup>
            </Marker>
          ))}

          {/* Layer: Terremoti INGV */}
          {layers.earthquakes && quakeData?.earthquakes?.map((eq, i) => (
            <CircleMarker
              key={`eq-${i}`}
              center={[eq.lat, eq.lon]}
              radius={Math.max(4, eq.mag * 3)}
              pathOptions={{
                color: eq.mag >= 4 ? '#ef4444' : eq.mag >= 3 ? '#f97316' : '#eab308',
                fillColor: eq.mag >= 4 ? '#ef4444' : eq.mag >= 3 ? '#f97316' : '#eab308',
                fillOpacity: 0.5, weight: 1,
              }}
            >
              <Popup>
                <div style={{ maxWidth: 200 }}>
                  <p style={{ fontWeight: 700, fontSize: 12 }}>M{eq.mag} {eq.magType}</p>
                  <p style={{ fontSize: 10, color: '#9ca3af' }}>{eq.place}</p>
                  <p style={{ fontSize: 10, color: '#9ca3af' }}>Prof. {eq.depth?.toFixed(1)}km</p>
                </div>
              </Popup>
            </CircleMarker>
          ))}

          {/* Layer: Voli militari ADS-B */}
          {layers.flights && flightData?.bases && Object.entries(flightData.bases).map(([base, data]) =>
            data.flights?.map((f, i) => (
              <Marker
                key={`fl-${base}-${i}`}
                position={[
                  {aviano:46.03,sigonella:37.40,ghedi:45.43,amendola:41.54,trapani_birgi:37.91}[base] || 42,
                  {aviano:12.60,sigonella:14.92,ghedi:10.27,amendola:15.72,trapani_birgi:12.50}[base] || 12,
                ]}
                icon={makeIcon('✈', '#22d3ee')}
              >
                <Popup>
                  <div style={{ maxWidth: 180 }}>
                    <p style={{ fontWeight: 700, fontSize: 11 }}>{f.callsign || f.icao24}</p>
                    <p style={{ fontSize: 10, color: '#9ca3af' }}>Base: {base}</p>
                  </div>
                </Popup>
              </Marker>
            ))
          )}

          {/* Layer: Convergenza geografica */}
          {layers.convergence && convergenceData?.zones?.map((z, i) => (
            <CircleMarker
              key={`conv-${i}`}
              center={[z.lat, z.lon]}
              radius={z.dimension_count * 8}
              pathOptions={{
                color: z.severity === 'alta' ? '#a855f7' : '#8b5cf6',
                fillColor: '#a855f7',
                fillOpacity: 0.2, weight: 2, dashArray: '4 4',
              }}
            >
              <Popup>
                <div style={{ maxWidth: 200 }}>
                  <p style={{ fontWeight: 700, fontSize: 12 }}>Convergenza: {z.dimension_count} dimensioni</p>
                  <p style={{ fontSize: 10, color: '#9ca3af' }}>{z.dimensions.join(', ')}</p>
                  <p style={{ fontSize: 10, color: '#9ca3af' }}>{z.event_count} eventi</p>
                </div>
              </Popup>
            </CircleMarker>
          ))}
        </MapContainer>
      </div>
    </div>
  )
}
