import { useState, useEffect } from 'react'
import { AlertTriangle, TrendingUp, TrendingDown } from 'lucide-react'
import { DIMENSION_COLORS, DIMENSION_LABELS } from '../utils/colors.js'
import { apiUrl } from '../utils/api.js'

const PROXY_LABELS = {
  article_count:        'Volume articoli',
  tone_mean:            'Tone medio',
  tone_negative_ratio:  'Rapporto negativi',
  military_articles:    'Articoli militari',
  trends_mean:          'Google Trends',
  gdelt_articles:       'Articoli GDELT',
  bulletin_count:       'Bollettini CSIRT',
  critical_count:       'Bollettini critici',
  total_cve:            'CVE',
  infra_affected:       'Infrastrutture',
  acled_protests:       'Proteste ACLED',
  acled_riots:          'Riot ACLED',
  rss_articles:         'Articoli RSS',
  total_flights:        'Voli militari',
}

function ZBar({ z }) {
  const abs = Math.min(Math.abs(z), 3)
  const pct = (abs / 3) * 100
  const color = abs >= 2.5 ? '#ef4444' : abs >= 2 ? '#f97316' : '#eab308'
  return (
    <div className="flex items-center gap-2 flex-1">
      <div className="h-1.5 bg-gray-800 rounded-full flex-1 overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{ width: `${pct}%`, backgroundColor: color }}
        />
      </div>
      <span className="text-xs font-mono w-10 text-right" style={{ color }}>
        {z > 0 ? '+' : ''}{z.toFixed(1)}σ
      </span>
    </div>
  )
}

export default function AnomaliesPanel() {
  const [anomalies, setAnomalies] = useState([])
  const [loading, setLoading]     = useState(true)

  useEffect(() => {
    fetch(apiUrl('/api/score/anomalies'))
      .then(r => r.json())
      .then(data => { setAnomalies(data); setLoading(false) })
      .catch(() => setLoading(false))
  }, [])

  return (
    <div className="card">
      <div className="flex items-center gap-2 mb-4">
        <AlertTriangle className="w-4 h-4 text-yellow-500" />
        <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider">
          Anomalie rilevate
        </h2>
        {!loading && (
          <span className="ml-auto text-xs px-2 py-0.5 rounded-full bg-gray-800 text-gray-500">
            {anomalies.length} proxy {'>'} 1.5σ
          </span>
        )}
      </div>

      {loading ? (
        <p className="text-gray-600 text-sm">Calcolo anomalie...</p>
      ) : anomalies.length === 0 ? (
        <div className="flex flex-col items-center py-6 gap-2 text-gray-600">
          <div className="w-8 h-8 rounded-full bg-green-500/10 flex items-center justify-center">
            <span className="text-green-500 text-lg">✓</span>
          </div>
          <p className="text-sm">Nessuna anomalia significativa</p>
          <p className="text-xs text-gray-700">Tutti i proxy entro 1.5 deviazioni standard dalla baseline</p>
        </div>
      ) : (
        <div className="space-y-2">
          {anomalies.map((a, i) => {
            const color = DIMENSION_COLORS[a.dimension] ?? '#6b7280'
            return (
              <div
                key={i}
                className="flex items-center gap-3 py-2 border-b border-gray-800/50 last:border-0"
              >
                {/* Dimensione badge */}
                <span
                  className="text-xs px-2 py-0.5 rounded-full font-medium flex-shrink-0 w-24 text-center"
                  style={{ backgroundColor: color + '22', color }}
                >
                  {DIMENSION_LABELS[a.dimension]?.slice(0, 8) ?? a.dimension}
                </span>

                {/* Proxy + barra */}
                <div className="flex-1 min-w-0 space-y-0.5">
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-xs text-gray-300 truncate">
                      {PROXY_LABELS[a.proxy] ?? a.proxy.replace(/_/g, ' ')}
                    </span>
                    <div className="flex items-center gap-1 flex-shrink-0">
                      {a.direction === 'alto'
                        ? <TrendingUp  className="w-3 h-3 text-red-400" />
                        : <TrendingDown className="w-3 h-3 text-green-400" />
                      }
                      <span className="text-xs font-mono text-gray-400">
                        {typeof a.value === 'number' ? a.value.toFixed(2) : a.value}
                        <span className="text-gray-600"> (μ={a.mean})</span>
                      </span>
                    </div>
                  </div>
                  <ZBar z={a.z_score} />
                </div>
              </div>
            )
          })}
        </div>
      )}

      <p className="text-xs text-gray-700 mt-3 pt-3 border-t border-gray-800">
        Soglia: 1.5σ dalla baseline rolling 90gg. Valori di default usati se DB {'<'} 7 giorni.
      </p>
    </div>
  )
}
