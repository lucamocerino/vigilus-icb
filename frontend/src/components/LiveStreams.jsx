import { useState } from 'react'
import { Tv, Maximize2, Minimize2 } from 'lucide-react'

const CHANNELS = [
  { id: 'skytg24',   name: 'Sky TG24',     src: 'https://videoplatform.sky.it/diretta/diretta_iframe.html' },
  { id: 'rainews',   name: 'Rai News 24',  src: 'https://www.rainews.it/dl/rainews/live/ContentItem-3156f2f2-dc70-4953-8e2f-70d7489d73cb.html' },
  { id: 'tgcom24',   name: 'TGCOM24',      src: 'https://mediasetinfinity.mediaset.it/diretta/tgcom24_cH3_p101120129.html' },
]

export default function LiveStreams() {
  const [selected, setSelected] = useState(CHANNELS[0])
  const [expanded, setExpanded] = useState(false)

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Tv className="w-4 h-4 text-red-400" />
          <h3 className="term-label">TG LIVE</h3>
          <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
        </div>
        <div className="flex items-center gap-2">
          {CHANNELS.map(ch => (
            <button
              key={ch.id}
              onClick={() => setSelected(ch)}
              className={`text-[10px] px-2 py-0.5 rounded-full transition-colors ${
                selected.id === ch.id
                  ? 'bg-red-600/20 text-red-400 border border-red-500/30'
                  : 'text-gray-500 hover:text-gray-300 border border-transparent'
              }`}
            >
              {ch.name}
            </button>
          ))}
          <button onClick={() => setExpanded(!expanded)} className="text-gray-500 hover:text-white p-1">
            {expanded ? <Minimize2 className="w-3.5 h-3.5" /> : <Maximize2 className="w-3.5 h-3.5" />}
          </button>
        </div>
      </div>

      <div className={`rounded-lg overflow-hidden bg-black relative ${expanded ? 'h-[400px]' : 'h-48'}`}>
        <iframe
          key={selected.id}
          src={selected.src}
          title={selected.name}
          className="w-full h-full border-0"
          allow="autoplay; fullscreen; encrypted-media"
          allowFullScreen
        />
        <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/80 to-transparent p-2 pointer-events-none">
          <div className="flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-red-500 animate-pulse" />
            <span className="text-[10px] text-white font-medium">{selected.name}</span>
          </div>
        </div>
      </div>
    </div>
  )
}
