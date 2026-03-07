import { useState, useEffect, useRef } from 'react'
import { DIMENSION_COLORS } from '../utils/colors.js'
import { apiUrl } from '../utils/api.js'

const SOURCE_ICONS = {
  GDELT:  '◆',
  RSS:    '◇',
  CSIRT:  '⬡',
}

export default function NewsTicker() {
  const [headlines, setHeadlines] = useState([])
  const tickerRef = useRef(null)
  const [paused, setPaused] = useState(false)

  useEffect(() => {
    function load() {
      fetch(apiUrl('/api/headlines'))
        .then(r => r.json())
        .then(data => { if (data?.length) setHeadlines(data) })
        .catch(() => {})
    }
    load()
    const interval = setInterval(load, 5 * 60 * 1000)
    return () => clearInterval(interval)
  }, [])

  if (!headlines.length) return null

  // Duplica per loop continuo
  const items = [...headlines, ...headlines]

  return (
    <div
      className="border-b border-term-border bg-term-bg overflow-hidden relative"
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => setPaused(false)}
    >
      <div className="flex items-center">
        {/* Badge fisso */}
        <div className="flex-shrink-0 bg-term-surface border-r border-term-border px-3 py-1.5 z-10">
          <span className="text-[10px] font-bold tracking-widest text-indigo-400">FEED</span>
        </div>

        {/* Ticker scrollante */}
        <div className="overflow-hidden flex-1">
          <div
            ref={tickerRef}
            className="flex items-center gap-6 whitespace-nowrap ticker-scroll"
            style={{
              animationPlayState: paused ? 'paused' : 'running',
              animationDuration: `${items.length * 4}s`,
            }}
          >
            {items.map((h, i) => (
              <span key={i} className="inline-flex items-center gap-1.5 py-1.5">
                <span
                  className="text-[10px] opacity-60"
                  style={{ color: DIMENSION_COLORS[h.dimension] || '#6b7280' }}
                >
                  {SOURCE_ICONS[h.source] || '●'}
                </span>
                <span className="text-[10px] font-medium text-gray-500 uppercase">
                  {h.source}
                </span>
                {h.url ? (
                  <a
                    href={h.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs text-gray-400 hover:text-gray-200 transition-colors"
                  >
                    {h.title.length > 80 ? h.title.slice(0, 80) + '…' : h.title}
                  </a>
                ) : (
                  <span className="text-xs text-gray-400">
                    {h.title.length > 80 ? h.title.slice(0, 80) + '…' : h.title}
                  </span>
                )}
                <span className="text-term-dim mx-2">│</span>
              </span>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
