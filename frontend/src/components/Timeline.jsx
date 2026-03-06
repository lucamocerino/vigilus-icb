import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
} from 'recharts'
import { useScoreHistory } from '../hooks/useScore.js'
import { formatDateShort, formatDate } from '../utils/format.js'
import { scoreColor } from '../utils/colors.js'

export default function Timeline({ days = 30 }) {
  const { history, loading } = useScoreHistory(days)

  if (loading) {
    return (
      <div className="card flex items-center justify-center h-48 text-gray-600">
        Caricamento...
      </div>
    )
  }

  const data = history.map(h => ({
    date: formatDateShort(h.timestamp),
    score: Math.round(h.score),
    full_date: h.timestamp,
  }))

  return (
    <div className="card">
      <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-4">
        Storico Score — Ultimi {days} giorni
      </h2>
      <ResponsiveContainer width="100%" height={200}>
        <LineChart data={data} margin={{ top: 5, right: 10, bottom: 5, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
          <XAxis
            dataKey="date"
            tick={{ fill: '#6b7280', fontSize: 11 }}
            interval="preserveStartEnd"
          />
          <YAxis
            domain={[0, 100]}
            tick={{ fill: '#6b7280', fontSize: 11 }}
            ticks={[0, 20, 40, 60, 80, 100]}
          />
          <ReferenceLine y={20} stroke="#22c55e" strokeDasharray="3 3" strokeOpacity={0.4} />
          <ReferenceLine y={40} stroke="#3b82f6" strokeDasharray="3 3" strokeOpacity={0.4} />
          <ReferenceLine y={60} stroke="#eab308" strokeDasharray="3 3" strokeOpacity={0.4} />
          <ReferenceLine y={80} stroke="#f97316" strokeDasharray="3 3" strokeOpacity={0.4} />
          <Tooltip
            contentStyle={{ backgroundColor: '#111827', border: '1px solid #374151' }}
            labelStyle={{ color: '#9ca3af' }}
            formatter={(value) => [value, 'Score']}
            labelFormatter={(_, payload) => payload?.[0]?.payload?.full_date
              ? formatDate(payload[0].payload.full_date)
              : ''
            }
          />
          <Line
            type="monotone"
            dataKey="score"
            stroke="#6366f1"
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4, fill: '#6366f1' }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
