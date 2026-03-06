import { useState, useEffect } from 'react'
import { ArrowUpRight, ArrowDownRight, Minus, TrendingUp } from 'lucide-react'

const PERIOD_OPTIONS = [
  { value: 'week',    label: 'Settimana' },
  { value: 'month',   label: 'Mese' },
  { value: 'quarter', label: 'Trimestre' },
]

const DIM_LABELS = {
  geopolitica: 'GEO', terrorismo: 'TERR', cyber: 'CYBER',
  eversione: 'EVER', militare: 'MIL', sociale: 'SOC',
}

function DeltaArrow({ delta }) {
  if (delta === null || delta === undefined) return <Minus className="w-3 h-3 text-gray-600" />
  if (delta > 2) return <ArrowUpRight className="w-3 h-3 text-red-400" />
  if (delta < -2) return <ArrowDownRight className="w-3 h-3 text-green-400" />
  return <Minus className="w-3 h-3 text-gray-600" />
}

function DeltaBadge({ direction }) {
  const colors = {
    peggiorato: 'text-red-400 bg-red-500/10',
    migliorato: 'text-green-400 bg-green-500/10',
    stabile: 'text-gray-500 bg-gray-500/10',
  }
  return (
    <span className={`px-2 py-0.5 rounded text-[10px] font-semibold uppercase ${colors[direction] || colors.stabile}`}>
      {direction || 'n/a'}
    </span>
  )
}

export default function ComparisonView() {
  const [period, setPeriod] = useState('week')
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    setLoading(true)
    fetch(`/api/score/compare?period=${period}`)
      .then(r => r.json())
      .then(d => setData(d))
      .catch(() => setData(null))
      .finally(() => setLoading(false))
  }, [period])

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <TrendingUp className="w-4 h-4 text-indigo-400" />
          <h3 className="term-label">CONFRONTO PERIODI</h3>
        </div>
        <div className="flex gap-1">
          {PERIOD_OPTIONS.map(opt => (
            <button
              key={opt.value}
              onClick={() => setPeriod(opt.value)}
              className={`px-2 py-1 rounded text-[10px] font-medium transition-colors ${
                period === opt.value
                  ? 'bg-indigo-600 text-white'
                  : 'text-gray-500 hover:text-gray-300'
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <p className="text-gray-600 text-xs text-center py-4">Caricamento...</p>
      ) : !data ? (
        <p className="text-gray-600 text-xs text-center py-4">Nessun dato</p>
      ) : (
        <div className="space-y-4">
          {/* Score complessivo */}
          <div className="grid grid-cols-3 gap-3 text-center">
            <div>
              <p className="text-[10px] text-gray-600 uppercase">{data.period2?.label}</p>
              <p className="text-lg font-bold text-gray-300">{data.period2?.avg_score ?? '—'}</p>
              <p className="text-[10px] text-gray-600">{data.period2?.count ?? 0} campioni</p>
            </div>
            <div className="flex flex-col items-center justify-center">
              <DeltaArrow delta={data.delta_score} />
              <p className={`text-sm font-bold mt-1 ${
                data.delta_score > 0 ? 'text-red-400' : data.delta_score < 0 ? 'text-green-400' : 'text-gray-500'
              }`}>
                {data.delta_score !== null ? `${data.delta_score > 0 ? '+' : ''}${data.delta_score}` : '—'}
              </p>
              <DeltaBadge direction={data.delta_direction} />
            </div>
            <div>
              <p className="text-[10px] text-gray-600 uppercase">{data.period1?.label}</p>
              <p className="text-lg font-bold text-gray-300">{data.period1?.avg_score ?? '—'}</p>
              <p className="text-[10px] text-gray-600">{data.period1?.count ?? 0} campioni</p>
            </div>
          </div>

          {/* Dimensioni */}
          <div className="border-t border-term-border pt-3">
            <table className="w-full text-xs">
              <thead>
                <tr className="text-[10px] text-gray-600 uppercase">
                  <th className="text-left py-1">Dim</th>
                  <th className="text-right">Precedente</th>
                  <th className="text-right">Attuale</th>
                  <th className="text-right">Δ</th>
                  <th className="text-center">Stato</th>
                </tr>
              </thead>
              <tbody>
                {data.dimensions && Object.entries(data.dimensions).map(([dim, vals]) => (
                  <tr key={dim} className="border-t border-term-border/50">
                    <td className="py-1.5 font-medium text-gray-400">{DIM_LABELS[dim] || dim}</td>
                    <td className="text-right text-gray-500">{vals.period2_avg ?? '—'}</td>
                    <td className="text-right text-gray-300">{vals.period1_avg ?? '—'}</td>
                    <td className="text-right">
                      <span className={`font-medium ${
                        vals.delta > 2 ? 'text-red-400' : vals.delta < -2 ? 'text-green-400' : 'text-gray-600'
                      }`}>
                        {vals.delta !== null ? `${vals.delta > 0 ? '+' : ''}${vals.delta}` : '—'}
                      </span>
                    </td>
                    <td className="text-center">
                      <DeltaBadge direction={vals.direction} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
