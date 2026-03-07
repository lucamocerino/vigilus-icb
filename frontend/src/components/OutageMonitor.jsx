import { useState, useEffect } from 'react'
import { Wifi, WifiOff, CheckCircle } from 'lucide-react'
import { apiUrl } from '../utils/api.js'

const TYPE_ICONS = {
  telecom: '📡',
  energia: '⚡',
  trasporti: '🚂',
  governo: '🏛',
}

export default function OutageMonitor() {
  const [services, setServices] = useState([])

  useEffect(() => {
    fetch(apiUrl('/api/outages')).then(r => r.json()).then(setServices).catch(() => {})
  }, [])

  if (!services.length) return null

  const allOk = services.every(s => s.status === 'ok')

  return (
    <div className="card">
      <div className="flex items-center gap-2 mb-3">
        {allOk ? <Wifi className="w-4 h-4 text-green-400" /> : <WifiOff className="w-4 h-4 text-red-400" />}
        <h3 className="term-label">INFRASTRUTTURE DIGITALI</h3>
        {allOk && <span className="text-[10px] text-green-400 bg-green-500/10 px-1.5 py-0.5 rounded">tutti operativi</span>}
      </div>

      <div className="grid grid-cols-2 gap-1">
        {services.map((s, i) => (
          <div key={i} className={`flex items-center gap-1.5 px-2 py-1 rounded text-[10px] ${
            s.status === 'ok' ? 'text-gray-400' : 'text-red-400 bg-red-500/10'
          }`}>
            <span>{TYPE_ICONS[s.type] || '●'}</span>
            <span className="truncate">{s.service}</span>
            {s.status === 'ok'
              ? <CheckCircle className="w-3 h-3 text-green-500 ml-auto flex-shrink-0" />
              : <WifiOff className="w-3 h-3 text-red-400 ml-auto flex-shrink-0" />
            }
          </div>
        ))}
      </div>
    </div>
  )
}
