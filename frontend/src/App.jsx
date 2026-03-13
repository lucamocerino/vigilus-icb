import { useCallback, useState, useRef, lazy, Suspense, startTransition } from 'react'
import Header from './components/Header.jsx'
import ScoreGauge from './components/ScoreGauge.jsx'
import DimensionCard from './components/DimensionCard.jsx'
import ErrorBoundary from './components/ErrorBoundary.jsx'
import MapView from './components/MapView.jsx'
import NewsTicker from './components/NewsTicker.jsx'
import CommandPalette from './components/CommandPalette.jsx'
import ShareButtons from './components/ShareButtons.jsx'
import { useScore } from './hooks/useScore.js'
import { useWebSocket } from './hooks/useWebSocket.js'
import { useTheme } from './hooks/useTheme.js'
import { useUrlState } from './hooks/useUrlState.js'
import { createI18n } from './services/i18n.js'
import { RefreshCw, AlertTriangle, Sun, Moon, Globe } from 'lucide-react'
import { apiUrl } from './utils/api.js'

// Lazy-loaded heavy components
const RadarPlot = lazy(() => import('./components/RadarPlot.jsx'))
const Timeline = lazy(() => import('./components/Timeline.jsx'))
const NarrativeBox = lazy(() => import('./components/NarrativeBox.jsx'))
const HeatmapChart = lazy(() => import('./components/HeatmapChart.jsx'))
const AnomaliesPanel = lazy(() => import('./components/AnomaliesPanel.jsx'))
const EventFeed = lazy(() => import('./components/EventFeed.jsx'))
const SourceStatus = lazy(() => import('./components/SourceStatus.jsx'))
const Methodology = lazy(() => import('./components/Methodology.jsx'))
const ExportButtons = lazy(() => import('./components/ExportButtons.jsx'))
const ComparisonView = lazy(() => import('./components/ComparisonView.jsx'))
const RegionalBreakdown = lazy(() => import('./components/RegionalBreakdown.jsx'))
const TrendingKeywords = lazy(() => import('./components/TrendingKeywords.jsx'))
const EventSearch = lazy(() => import('./components/EventSearch.jsx'))
const DailyDigest = lazy(() => import('./components/DailyDigest.jsx'))
const HotspotPanel = lazy(() => import('./components/HotspotPanel.jsx'))
const PredictionMarkets = lazy(() => import('./components/PredictionMarkets.jsx'))
const OutageMonitor = lazy(() => import('./components/OutageMonitor.jsx'))
const RegionBrief = lazy(() => import('./components/RegionBrief.jsx'))
const DimensionModal = lazy(() => import('./components/DimensionModal.jsx'))

const LazyFallback = () => <div className="h-20 flex items-center justify-center text-gray-700 text-[10px]">...</div>
function L({ children }) { return <Suspense fallback={<LazyFallback />}>{children}</Suspense> }

const i18n = createI18n()

const DIMENSIONS = ['geopolitica', 'terrorismo', 'cyber', 'eversione', 'militare', 'sociale']

function NoDataBanner({ onTrigger }) {
  const [loading, setLoading] = useState(false)

  async function trigger() {
    setLoading(true)
    try {
      await fetch(apiUrl('/api/score/trigger'), { method: 'POST' })
      // reload della pagina dopo 2s per permettere al backend di finire
      setTimeout(() => window.location.reload(), 2000)
    } catch {
      setLoading(false)
    }
  }

  return (
    <div className="flex flex-col items-center justify-center gap-4 py-20 text-center">
      <div className="w-16 h-16 rounded-full bg-indigo-500/10 flex items-center justify-center">
        <AlertTriangle className="w-8 h-8 text-indigo-400" />
      </div>
      <h2 className="text-lg font-semibold text-gray-300">Nessun dato ancora disponibile</h2>
      <p className="text-sm text-gray-500 max-w-sm">
        Il primo ciclo di raccolta non è ancora stato eseguito. Clicca per avviarlo manualmente.
      </p>
      <button
        onClick={trigger}
        disabled={loading}
        className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 rounded-xl text-sm font-semibold transition-colors"
      >
        <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
        {loading ? 'Calcolo in corso (~60s)...' : 'Avvia primo calcolo score'}
      </button>
    </div>
  )
}

function ConnectionError({ error, onRetry }) {
  return (
    <div className="flex flex-col items-center justify-center gap-4 py-20 text-center">
      <AlertTriangle className="w-8 h-8 text-red-400" />
      <p className="text-red-400 font-medium">Backend non raggiungibile</p>
      <p className="text-gray-600 text-sm">{error}</p>
      <p className="text-gray-700 text-xs">Assicurati che il backend giri su localhost:8000</p>
      <button
        onClick={onRetry}
        className="flex items-center gap-2 px-4 py-2 bg-gray-800 hover:bg-gray-700 rounded-xl text-sm transition-colors"
      >
        <RefreshCw className="w-4 h-4" /> Riprova
      </button>
    </div>
  )
}

export default function App() {
  const { score, loading, error, setScore, reload } = useScore()
  const [historyDays, setHistoryDays]                 = useState(30)
  const [page, setPage]                               = useState('dashboard')
  const [selectedDim, setSelectedDim]                 = useState(null)
  const { theme, toggle: toggleTheme } = useTheme()
  const [lang, setLang] = useState(i18n.lang)
  useUrlState(page, setPage, historyDays, setHistoryDays)

  function toggleLang() {
    const next = i18n.toggle()
    setLang(next)
  }

  // Resize panel
  const [mapWidth, setMapWidth] = useState(60)
  const resizing = useRef(false)

  function startResize(e) {
    resizing.current = true
    const startX = e.clientX
    const startWidth = mapWidth
    function onMove(ev) {
      if (!resizing.current) return
      const delta = ev.clientX - startX
      const vw = window.innerWidth
      const newWidth = Math.max(30, Math.min(80, startWidth + (delta / vw) * 100))
      setMapWidth(newWidth)
    }
    function onUp() {
      resizing.current = false
      document.removeEventListener('mousemove', onMove)
      document.removeEventListener('mouseup', onUp)
    }
    document.addEventListener('mousemove', onMove)
    document.addEventListener('mouseup', onUp)
  }

  const handleWsMessage = useCallback((msg) => {
    if (msg.type === 'score_update') {
      setScore(prev => ({
        ...prev,
        score: msg.data.score,
        level: msg.data.level,
        color: msg.data.color,
        timestamp: msg.data.timestamp,
        score_trend: msg.data.score_trend ?? 0,
        dimensions: DIMENSIONS.map(d => ({
          dimension: d,
          score: msg.data.dimensions[d] ?? prev?.dimensions?.find(x => x.dimension === d)?.score ?? 0,
          raw_values: {},
          trend: 0,
        })),
      }))
    }
  }, [setScore])

  useWebSocket(handleWsMessage)

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center gap-3">
        <RefreshCw className="w-5 h-5 animate-spin text-indigo-400" />
        <p className="text-gray-500">Connessione al backend...</p>
      </div>
    )
  }

  if (error) return (
    <div className="min-h-screen">
      <Header />
      <ConnectionError error={error} onRetry={reload} />
    </div>
  )

  const dimensions = score?.dimensions ?? []
  const selectedDimData = dimensions.find(d => d.dimension === selectedDim)

  return (
    <div className="min-h-screen">
      <Header lastUpdate={score?.timestamp} score={score?.score} dimensions={dimensions} sourcesOk={score?.sources_ok} sourcesTotal={score?.sources_total} />

      {/* News ticker scrollante */}
      <NewsTicker />

      {/* Command palette (Cmd+K) */}
      <CommandPalette onNavigate={(p) => startTransition(() => setPage(p))} onDimension={setSelectedDim} />

      {/* Navigazione */}
      <nav className="border-b border-term-border bg-term-surface">
        <div className="max-w-7xl mx-auto px-3 sm:px-4 flex items-center justify-between">
          <div className="flex gap-0">
          {[
            { id: 'dashboard',   label: '[ DASHBOARD ]' },
            { id: 'compare',     label: '[ CONFRONTO ]' },
            { id: 'methodology', label: '[ METODOLOGIA ]' },
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => startTransition(() => setPage(tab.id))}
              className={`px-4 py-2 text-xs font-medium tracking-widest transition-colors border-b-2 ${
                page === tab.id
                  ? 'border-indigo-500 text-indigo-400'
                  : 'border-transparent text-gray-600 hover:text-gray-400'
              }`}
            >
              {tab.label}
            </button>
          ))}
          </div>
          <div className="flex items-center gap-2">
            <button onClick={toggleLang} className="p-1.5 text-gray-500 hover:text-indigo-400 transition-colors text-[10px] font-bold" title="IT/EN">
              {lang.toUpperCase()}
            </button>
            <button onClick={toggleTheme} className="p-1.5 text-gray-500 hover:text-indigo-400 transition-colors" title={theme === 'dark' ? 'Light mode' : 'Dark mode'}>
              {theme === 'dark' ? <Sun className="w-3.5 h-3.5" /> : <Moon className="w-3.5 h-3.5" />}
            </button>
            <kbd className="text-[9px] text-gray-600 bg-gray-800 px-1.5 py-0.5 rounded hidden md:inline">⌘K</kbd>
            <ShareButtons score={score?.score} level={score?.level} />
          </div>
        </div>
      </nav>

      {page === 'methodology' ? (
        <Methodology />
      ) : page === 'compare' ? (
        <main className="max-w-7xl mx-auto px-3 sm:px-4 py-6 space-y-5">
          <ErrorBoundary label="Confronto periodi">
            <ComparisonView />
          </ErrorBoundary>
        </main>
      ) : score === null ? (
        <NoDataBanner />
      ) : (
        /* ── Map + Sidebar Bloomberg layout ── */
        <div className="flex flex-col lg:flex-row" style={{ height: 'calc(100vh - 110px)' }}>

          {/* LEFT: Mappa (resizable) */}
          <div style={{ width: `${mapWidth}%` }} className="hidden lg:flex flex-col flex-shrink-0 border-r border-term-border">
            {/* Score bar compatta */}
            <div className="flex items-center gap-2 px-3 py-1.5 bg-term-surface border-b border-term-border overflow-x-auto flex-shrink-0">
              <ErrorBoundary label="Score Gauge">
                <div className="flex items-center gap-3 flex-shrink-0">
                  <span className="text-lg font-bold" style={{ color: score?.color }}>{score?.score?.toFixed(1)}</span>
                  <span className="text-[10px] px-1.5 py-0.5 rounded font-semibold" style={{ backgroundColor: score?.color + '22', color: score?.color }}>{score?.level}</span>
                  {score?.score_trend != null && score.score_trend !== 0 && (
                    <span className={`text-[10px] font-bold ${score.score_trend > 0 ? 'text-red-400' : 'text-green-400'}`}>
                      {score.score_trend > 0 ? '▲' : '▼'}{Math.abs(score.score_trend).toFixed(1)}
                    </span>
                  )}
                </div>
              </ErrorBoundary>
              <span className="text-term-dim mx-1">│</span>
              {DIMENSIONS.map(dim => {
                const ds = dimensions.find(d => d.dimension === dim)
                if (!ds) return null
                return (
                  <button key={dim} onClick={() => setSelectedDim(dim)} className="flex items-center gap-1 flex-shrink-0 hover:opacity-80 transition-opacity">
                    <span className="text-[10px] font-semibold" style={{ color: {'geopolitica':'#6366f1','terrorismo':'#ef4444','cyber':'#06b6d4','eversione':'#f59e0b','militare':'#64748b','sociale':'#22c55e'}[dim] }}>
                      {dim.slice(0,3).toUpperCase()}
                    </span>
                    <span className="text-[10px] text-gray-300 tabular-nums">{Math.round(ds.score)}</span>
                  </button>
                )
              })}
            </div>

            {/* Mappa */}
            <div className="flex-1 min-h-0">
              <ErrorBoundary label="Mappa">
                <MapView />
              </ErrorBoundary>
            </div>
          </div>

          {/* Mobile map fallback */}
          <div className="lg:hidden h-[40vh] flex-shrink-0 border-b border-term-border">
            <ErrorBoundary label="Mappa"><MapView /></ErrorBoundary>
          </div>

          {/* Resize handle (desktop only) */}
          <div className="resize-handle hidden lg:block" onMouseDown={startResize} />

          {/* RIGHT: Pannelli scrollabili */}
          <div className="flex-1 overflow-y-auto bg-term-bg">
            <div className="p-2 space-y-2">

              {/* Narrative */}
              <ErrorBoundary label="Narrativa">
                <NarrativeBox score={score?.score} scoreTrend={score?.score_trend} dimensions={dimensions} />
              </ErrorBoundary>

              {/* Feed eventi — in alto */}
              <ErrorBoundary label="Feed eventi"><EventFeed /></ErrorBoundary>

              {/* Radar */}
              <ErrorBoundary label="Radar">
                <RadarPlot dimensions={dimensions} />
              </ErrorBoundary>

              {/* Dimension cards */}
              <div className="grid grid-cols-3 gap-1.5">
                {DIMENSIONS.map(dim => {
                  const ds = dimensions.find(d => d.dimension === dim)
                  return (
                    <DimensionCard key={dim} dimension={dim} score={ds?.score} trend={ds?.trend} onClick={() => setSelectedDim(dim)} />
                  )
                })}
              </div>

              {/* Timeline storico */}
              <div>
                <div className="flex items-center justify-between mb-1">
                  <ErrorBoundary label="Export"><ExportButtons /></ErrorBoundary>
                  <div className="flex gap-1 text-xs">
                    {[7, 30, 90].map(d => (
                      <button key={d} onClick={() => setHistoryDays(d)}
                        className={`px-2 py-0.5 rounded transition-colors ${
                          historyDays === d ? 'bg-indigo-600 text-white' : 'text-gray-500 hover:text-gray-300'
                        }`}
                      >{d}g</button>
                    ))}
                  </div>
                </div>
                <ErrorBoundary label="Timeline"><Timeline days={historyDays} /></ErrorBoundary>
              </div>

              {/* Trending */}
              <ErrorBoundary label="Trending"><TrendingKeywords /></ErrorBoundary>

              {/* Hotspot + Correlations */}
              <ErrorBoundary label="Hotspot"><HotspotPanel /></ErrorBoundary>

              {/* Predictions + Outages */}
              <div className="grid grid-cols-2 gap-2">
                <ErrorBoundary label="Predictions"><PredictionMarkets /></ErrorBoundary>
                <ErrorBoundary label="Outages"><OutageMonitor /></ErrorBoundary>
              </div>

              {/* Intelligence */}
              <div className="grid grid-cols-1 gap-2">
                <ErrorBoundary label="Daily Digest"><DailyDigest /></ErrorBoundary>
              </div>

              {/* Region Brief */}
              <ErrorBoundary label="Dossier Regionale"><RegionBrief /></ErrorBoundary>

              {/* Regional breakdown */}
              <ErrorBoundary label="Regionale"><RegionalBreakdown /></ErrorBoundary>

              {/* Anomalies + Heatmap */}
              <div className="grid grid-cols-2 gap-2">
                <ErrorBoundary label="Anomalie"><AnomaliesPanel /></ErrorBoundary>
                <ErrorBoundary label="Heatmap"><HeatmapChart /></ErrorBoundary>
              </div>

              {/* Sources */}
              <ErrorBoundary label="Stato fonti"><SourceStatus /></ErrorBoundary>
            </div>
          </div>
        </div>
      )}

      {selectedDim && selectedDimData && (
        <ErrorBoundary label="Dettaglio dimensione" fallback={<div />}>
          <DimensionModal
            dimension={selectedDim}
            score={selectedDimData.score}
            trend={selectedDimData.trend}
            rawValues={selectedDimData.raw_values}
            onClose={() => setSelectedDim(null)}
          />
        </ErrorBoundary>
      )}
    </div>
  )
}
