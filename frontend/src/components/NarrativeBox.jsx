import { useState, useEffect } from 'react'
import { RefreshCw, Sparkles } from 'lucide-react'
import { DIMENSION_LABELS, DIMENSION_COLORS, getLevel } from '../utils/colors.js'

const DIMENSION_ORDER = ['geopolitica', 'terrorismo', 'cyber', 'eversione', 'militare', 'sociale']

export default function NarrativeBox({ score, scoreTrend, dimensions }) {
  const [narrative, setNarrative] = useState(null)
  const [loading, setLoading]     = useState(false)

  const level = getLevel(score ?? 0)

  // Controlla se esiste già un testo in cache — senza generarne uno nuovo
  useEffect(() => {
    if (score == null) return
    fetch('/api/score/narrative')
      .then(r => r.json())
      .then(data => {
        // Mostra solo se già esistente (cached o API key configurata e già chiamata)
        if (data.text) setNarrative(data)
      })
      .catch(() => {})
  }, [score])

  async function generate() {
    setLoading(true)
    try {
      const r = await fetch('/api/score/narrative')
      const data = await r.json()
      setNarrative(data)
    } catch {
      setNarrative({ error: 'Errore di connessione' })
    } finally {
      setLoading(false)
    }
  }

  const elevated = DIMENSION_ORDER
    .map(k => (dimensions ?? []).find(d => d.dimension === k))
    .filter(Boolean)
    .filter(d => d.score > 50)
    .sort((a, b) => b.score - a.score)

  const displayLevel = getLevel(score ?? 0)
  const borderColor  = displayLevel.color + '44'
  const bgGradient   = `linear-gradient(135deg, ${displayLevel.color}08, transparent)`

  return (
    <div className="card" style={{ borderColor, background: bgGradient }}>
      <div className="flex items-start gap-3">
        <div className="flex-shrink-0 w-2 rounded-full self-stretch" style={{ backgroundColor: displayLevel.color }} />

        <div className="flex-1 min-w-0">
          {/* Header */}
          <div className="flex items-center justify-between gap-2 mb-3">
            <div className="flex items-center gap-2">
              <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-wider">
                Lettura della situazione
              </h2>
              <span
                className="text-xs px-2 py-0.5 rounded-full font-bold"
                style={{ backgroundColor: displayLevel.color + '22', color: displayLevel.color }}
              >
                {displayLevel.label}
              </span>
              {narrative?.text && <Sparkles className="w-3 h-3 text-indigo-400" title="Generato da Claude AI" />}
              {narrative?.cached && <span className="text-xs text-gray-600">(cache)</span>}
            </div>
            {/* Pulsante genera — esplicito, non automatico */}
            <button
              onClick={generate}
              disabled={loading}
              className="flex items-center gap-1.5 text-xs text-gray-600 hover:text-indigo-400 transition-colors disabled:opacity-50"
              title="Genera analisi AI (richiede ANTHROPIC_API_KEY)"
            >
              <RefreshCw className={`w-3 h-3 ${loading ? 'animate-spin' : ''}`} />
              {loading ? 'Generazione...' : 'Genera AI'}
            </button>
          </div>

          {/* Testo: AI se disponibile, rule-based altrimenti */}
          {narrative?.text ? (
            <p className="text-sm text-gray-200 leading-relaxed">{narrative.text}</p>
          ) : (
            <FallbackNarrative score={score} scoreTrend={scoreTrend} dimensions={dimensions} />
          )}

          {/* Badge dimensioni elevate */}
          {elevated.length > 0 && (
            <div className="flex flex-wrap gap-1.5 mt-3">
              {elevated.map(d => (
                <span
                  key={d.dimension}
                  className="text-xs px-2 py-0.5 rounded-full font-medium"
                  style={{
                    backgroundColor: DIMENSION_COLORS[d.dimension] + '22',
                    color: DIMENSION_COLORS[d.dimension],
                  }}
                >
                  {DIMENSION_LABELS[d.dimension]} {Math.round(d.score)}
                </span>
              ))}
            </div>
          )}

          <p className="text-xs text-gray-700 mt-2">
            {narrative?.text
              ? 'Generato da Claude AI su proxy pubblici — non sostituisce valutazioni di intelligence.'
              : 'Lettura automatica basata su regole — clicca "Genera AI" per un\'analisi contestuale.'}
          </p>
        </div>
      </div>
    </div>
  )
}

function FallbackNarrative({ score, scoreTrend, dimensions }) {
  if (!score || !dimensions?.length) return null
  const elevated = (dimensions ?? []).filter(d => d.score > 50).sort((a, b) => b.score - a.score)
  const topNames  = elevated.slice(0, 2).map(d => DIMENSION_LABELS[d.dimension]).join(' e ')

  let text = ''
  if (score <= 20)      text = 'Tutti i proxy si trovano sotto la media storica degli ultimi 90 giorni.'
  else if (score <= 40) text = 'I segnali monitorati rientrano nella norma storica, senza anomalie significative.'
  else if (score <= 60) text = elevated.length > 0
    ? `Alcuni proxy mostrano valori superiori alla media storica, in particolare ${topNames}.`
    : 'La situazione è di moderata attenzione, con diversi proxy leggermente sopra la media.'
  else text = elevated.length > 0
    ? `Si registrano anomalie significative principalmente in ${topNames}.`
    : 'Lo score indica anomalie rilevanti su più assi rispetto alla baseline storica.'

  if (scoreTrend != null && scoreTrend > 3)  text += ` Tendenza in aumento (+${Math.round(scoreTrend)} punti).`
  else if (scoreTrend != null && scoreTrend < -3) text += ` Tendenza in miglioramento (${Math.round(scoreTrend)} punti).`

  return <p className="text-sm text-gray-300 leading-relaxed">{text}</p>
}
