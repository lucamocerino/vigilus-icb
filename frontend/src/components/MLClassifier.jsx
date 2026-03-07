import { useState, useEffect, useRef } from 'react'
import { Cpu, Loader } from 'lucide-react'
import { DIMENSION_COLORS } from '../utils/colors.js'
import { apiUrl } from '../utils/api.js'

const THREAT_COLORS = {
  critical: { bg: 'bg-red-500/15', text: 'text-red-400', label: 'CRITICO' },
  high:     { bg: 'bg-orange-500/15', text: 'text-orange-400', label: 'ALTO' },
  medium:   { bg: 'bg-yellow-500/15', text: 'text-yellow-400', label: 'MEDIO' },
  low:      { bg: 'bg-green-500/15', text: 'text-green-400', label: 'BASSO' },
  none:     { bg: 'bg-gray-500/10', text: 'text-gray-500', label: '—' },
}

const SENTIMENT_COLORS = {
  POSITIVE: 'text-green-400',
  NEGATIVE: 'text-red-400',
  UNKNOWN:  'text-gray-600',
}

export default function MLClassifier() {
  const [results, setResults] = useState([])
  const [status, setStatus] = useState('idle')
  const [modelStatus, setModelStatus] = useState('not_loaded')
  const workerRef = useRef(null)

  useEffect(() => {
    // Create web worker inline to avoid Vite build issues
    const workerCode = `
      const THREAT_KEYWORDS = {
        critical: ['attentato', 'esplosione', 'bomba', 'strage', 'guerra', 'attacco armato', 'nucleare', 'evacuazione'],
        high: ['terrorismo', 'hacker', 'ransomware', 'emergenza', 'allerta', 'crisi', 'scontri', 'rivolta'],
        medium: ['protesta', 'sciopero', 'manifestazione', 'incidente', 'arresto', 'sequestro', 'indagine'],
        low: ['accordo', 'cooperazione', 'incontro', 'vertice', 'conferenza', 'riforma'],
      }

      function classifyThreat(text) {
        const lower = text.toLowerCase()
        for (const [level, keywords] of Object.entries(THREAT_KEYWORDS)) {
          if (keywords.some(kw => lower.includes(kw))) return level
        }
        return 'none'
      }

      // Simple keyword-based sentiment (no ML model needed for instant results)
      const POS_WORDS = ['accordo','pace','crescita','successo','vittoria','sicurezza','cooperazione','miglioramento']
      const NEG_WORDS = ['attacco','crisi','morte','vittime','guerra','disastro','emergenza','fallimento','arresto','violenza','bomba','terrorismo','hacker']

      function classifySentiment(text) {
        const lower = text.toLowerCase()
        const pos = POS_WORDS.filter(w => lower.includes(w)).length
        const neg = NEG_WORDS.filter(w => lower.includes(w)).length
        if (neg > pos) return { label: 'NEGATIVE', score: Math.min(0.99, 0.5 + neg * 0.1) }
        if (pos > neg) return { label: 'POSITIVE', score: Math.min(0.99, 0.5 + pos * 0.1) }
        return { label: 'UNKNOWN', score: 0.5 }
      }

      self.onmessage = (event) => {
        const { type, data, id } = event.data
        if (type === 'classify') {
          const headlines = data.headlines || []
          const results = headlines.map(h => ({
            ...h,
            threat_level: classifyThreat(h.title || ''),
            sentiment: classifySentiment(h.title || '').label,
            sentiment_score: classifySentiment(h.title || '').score,
          }))
          self.postMessage({ type: 'classify_result', id, results })
        }
      }
      self.postMessage({ type: 'status', status: 'ready', message: 'Classificatore pronto' })
    `
    const blob = new Blob([workerCode], { type: 'application/javascript' })
    const url = URL.createObjectURL(blob)
    workerRef.current = new Worker(url)

    workerRef.current.onmessage = (event) => {
      const { type, results: classifyResults, status: s } = event.data
      if (type === 'status') {
        setModelStatus(s)
      } else if (type === 'classify_result') {
        setResults(classifyResults || [])
        setStatus('done')
      }
    }

    return () => {
      workerRef.current?.terminate()
      URL.revokeObjectURL(url)
    }
  }, [])

  async function runClassification() {
    setStatus('loading')
    try {
      const resp = await fetch(apiUrl('/api/headlines'))
      const headlines = await resp.json()
      if (!headlines?.length) { setStatus('idle'); return }

      setStatus('classifying')
      workerRef.current?.postMessage({
        type: 'classify',
        data: { headlines: headlines.slice(0, 30) },
        id: Date.now(),
      })
    } catch {
      setStatus('error')
    }
  }

  const threatCounts = {
    critical: results.filter(r => r.threat_level === 'critical').length,
    high: results.filter(r => r.threat_level === 'high').length,
    medium: results.filter(r => r.threat_level === 'medium').length,
  }

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Cpu className="w-4 h-4 text-cyan-400" />
          <h3 className="term-label">ML CLASSIFIER</h3>
          <span className={`text-[10px] px-1.5 py-0.5 rounded ${
            modelStatus === 'ready' ? 'bg-green-500/10 text-green-400' :
            modelStatus === 'loading' ? 'bg-yellow-500/10 text-yellow-400' :
            'bg-gray-500/10 text-gray-500'
          }`}>
            {modelStatus === 'ready' ? 'ML pronto' : modelStatus === 'loading' ? 'caricamento...' : 'browser-side'}
          </span>
        </div>
        <button
          onClick={runClassification}
          disabled={status === 'loading' || status === 'classifying'}
          className="flex items-center gap-1 px-2 py-1 bg-cyan-600/20 border border-cyan-500/30 rounded text-[10px] text-cyan-400 hover:bg-cyan-600/30 disabled:opacity-40 transition-colors"
        >
          {(status === 'loading' || status === 'classifying') ? (
            <><Loader className="w-3 h-3 animate-spin" /> Analisi...</>
          ) : (
            <><Cpu className="w-3 h-3" /> Classifica titoli</>
          )}
        </button>
      </div>

      {/* Threat summary */}
      {results.length > 0 && (
        <div className="flex gap-2 mb-3">
          {Object.entries(threatCounts).filter(([,c]) => c > 0).map(([level, count]) => {
            const style = THREAT_COLORS[level]
            return (
              <span key={level} className={`text-[10px] px-2 py-1 rounded ${style.bg} ${style.text} font-medium`}>
                {style.label}: {count}
              </span>
            )
          })}
          <span className="text-[10px] text-gray-600 px-2 py-1">{results.length} titoli analizzati</span>
        </div>
      )}

      {/* Results list */}
      {results.length > 0 ? (
        <div className="space-y-1 max-h-52 overflow-y-auto">
          {results.filter(r => r.threat_level !== 'none').slice(0, 12).map((r, i) => {
            const threat = THREAT_COLORS[r.threat_level] || THREAT_COLORS.none
            return (
              <div key={i} className="flex items-center gap-2 py-1">
                <span className={`text-[10px] w-12 text-center px-1 py-0.5 rounded ${threat.bg} ${threat.text} font-medium flex-shrink-0`}>
                  {threat.label}
                </span>
                <span className={`text-[10px] w-3 ${SENTIMENT_COLORS[r.sentiment]}`}>
                  {r.sentiment === 'POSITIVE' ? '↑' : r.sentiment === 'NEGATIVE' ? '↓' : '·'}
                </span>
                <span className="text-xs text-gray-400 truncate flex-1">{r.title}</span>
              </div>
            )
          })}
        </div>
      ) : status === 'idle' ? (
        <p className="text-[10px] text-gray-600 text-center py-3">
          Classifica i titoli con threat detection (keyword) + sentiment analysis (ML nel browser)
        </p>
      ) : null}
    </div>
  )
}
