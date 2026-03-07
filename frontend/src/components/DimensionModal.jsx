import { useState, useEffect } from 'react'
import { X, ExternalLink, TrendingUp, TrendingDown, Minus } from 'lucide-react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { DIMENSION_COLORS, DIMENSION_LABELS, getLevel } from '../utils/colors.js'
import { formatDate, formatDateShort } from '../utils/format.js'
import { apiUrl } from '../utils/api.js'

const PROXY_LABELS = {
  article_count:        'Volume articoli',
  tone_mean:            'Tone medio',
  tone_negative_ratio:  'Rapporto articoli negativi',
  military_articles:    'Articoli tema militare',
  trends_mean:          'Interesse Google Trends',
  gdelt_articles:       'Articoli GDELT',
  bulletin_count:       'Bollettini CSIRT',
  critical_count:       'Bollettini critici',
  total_cve:            'CVE menzionate',
  infra_affected:       'Infrastrutture coinvolte',
  acled_protests:       'Proteste ACLED',
  acled_riots:          'Riot ACLED',
  rss_articles:         'Articoli RSS',
  total_flights:        'Voli militari rilevati',
}

function TrendIcon({ value }) {
  if (value > 2)  return <TrendingUp  className="w-4 h-4 text-red-400" />
  if (value < -2) return <TrendingDown className="w-4 h-4 text-green-400" />
  return <Minus className="w-4 h-4 text-gray-500" />
}

export default function DimensionModal({ dimension, score, trend, rawValues, onClose }) {
  const [articles, setArticles]   = useState([])
  const [history, setHistory]     = useState([])
  const [loading, setLoading]     = useState(true)

  const color = DIMENSION_COLORS[dimension] ?? '#6b7280'
  const label = DIMENSION_LABELS[dimension] ?? dimension
  const level = getLevel(score ?? 0)

  useEffect(() => {
    Promise.all([
      fetch(apiUrl(`/api/events/latest?dimension=${dimension}&limit=5`)).then(r => r.json()).catch(() => []),
      fetch(apiUrl(`/api/dimension/${dimension}/history?days=30`)).then(r => r.json()).catch(() => []),
    ]).then(([arts, hist]) => {
      setArticles(arts)
      setHistory(hist.map(h => ({ date: formatDateShort(h.timestamp), score: Math.round(h.score) })))
      setLoading(false)
    })
  }, [dimension])

  // Chiudi con Escape
  useEffect(() => {
    const handler = (e) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onClose])

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      onClick={onClose}
    >
      <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" />
      <div
        className="relative bg-gray-900 border border-gray-700 rounded-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto"
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div
          className="sticky top-0 flex items-center justify-between px-6 py-4 border-b border-gray-800 rounded-t-2xl"
          style={{ background: `linear-gradient(135deg, ${color}18, transparent)` }}
        >
          <div className="flex items-center gap-3">
            <div className="w-3 h-3 rounded-full" style={{ backgroundColor: color }} />
            <h2 className="text-lg font-bold" style={{ color }}>{label}</h2>
            <span
              className="text-xs px-2 py-0.5 rounded-full font-medium"
              style={{ backgroundColor: level.color + '22', color: level.color }}
            >
              {level.label}
            </span>
          </div>
          <div className="flex items-center gap-3">
            <div className="text-right">
              <span className="text-3xl font-black tabular-nums" style={{ color }}>
                {score != null ? Math.round(score) : '—'}
              </span>
              <span className="text-xs text-gray-500">/100</span>
            </div>
            <div className="flex items-center gap-1 text-sm">
              <TrendIcon value={trend} />
              <span className={`font-medium ${trend > 2 ? 'text-red-400' : trend < -2 ? 'text-green-400' : 'text-gray-500'}`}>
                {trend > 0 ? '+' : ''}{trend != null ? Math.round(trend) : '—'}
              </span>
            </div>
            <button onClick={onClose} className="text-gray-500 hover:text-white p-1">
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        <div className="p-6 space-y-6">
          {/* Mini timeline */}
          {history.length > 1 && (
            <div>
              <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
                Andamento ultimi 30 giorni
              </h3>
              <ResponsiveContainer width="100%" height={100}>
                <LineChart data={history} margin={{ top: 5, right: 5, bottom: 0, left: -20 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
                  <XAxis dataKey="date" tick={{ fill: '#4b5563', fontSize: 10 }} interval="preserveStartEnd" />
                  <YAxis domain={[0, 100]} tick={{ fill: '#4b5563', fontSize: 10 }} />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#111827', border: `1px solid ${color}44` }}
                    formatter={(v) => [`${v}/100`, label]}
                  />
                  <Line type="monotone" dataKey="score" stroke={color} strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Proxy grezzi */}
          {rawValues && Object.keys(rawValues).length > 0 && (
            <div>
              <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
                Proxy misurati
              </h3>
              <div className="space-y-2">
                {Object.entries(rawValues).map(([key, val]) => {
                  const displayVal = typeof val === 'number' ? (Number.isInteger(val) ? val : val.toFixed(3)) : val
                  return (
                    <div key={key} className="flex items-center justify-between py-1.5 border-b border-gray-800/50 last:border-0">
                      <span className="text-sm text-gray-400">
                        {PROXY_LABELS[key] ?? key.replace(/_/g, ' ')}
                      </span>
                      <span className="font-mono text-sm font-medium" style={{ color }}>
                        {displayVal}
                      </span>
                    </div>
                  )
                })}
              </div>
            </div>
          )}

          {/* Ultimi articoli */}
          <div>
            <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">
              Ultimi eventi rilevati
            </h3>
            {loading ? (
              <p className="text-gray-600 text-sm">Caricamento...</p>
            ) : articles.length === 0 ? (
              <p className="text-gray-600 text-sm">Nessun evento classificato in questa dimensione.</p>
            ) : (
              <div className="space-y-2">
                {articles.map(a => (
                  <div key={a.id} className="flex gap-3 py-2 border-b border-gray-800/40 last:border-0">
                    <div className="w-1 rounded-full flex-shrink-0 mt-1" style={{ backgroundColor: color }} />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-start justify-between gap-2">
                        <p className="text-sm text-gray-300 leading-snug">{a.title}</p>
                        {a.url && (
                          <a href={a.url} target="_blank" rel="noopener noreferrer"
                            className="flex-shrink-0 text-gray-600 hover:text-gray-400">
                            <ExternalLink className="w-3 h-3" />
                          </a>
                        )}
                      </div>
                      <p className="text-xs text-gray-600 mt-0.5">{formatDate(a.event_date)}</p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
