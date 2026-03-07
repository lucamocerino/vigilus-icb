import { useState } from 'react'
import { Download } from 'lucide-react'
import { apiUrl } from '../utils/api.js'

export default function ExportButtons() {
  const [loadingCsv, setLoadingCsv] = useState(false)
  const [loadingPdf, setLoadingPdf] = useState(false)

  async function downloadCsv() {
    setLoadingCsv(true)
    try {
      const resp = await fetch(apiUrl('/api/export/csv?days=30'))
      const blob = await resp.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `sentinella_export_30d.csv`
      a.click()
      URL.revokeObjectURL(url)
    } catch (e) {
      console.error('Export CSV failed:', e)
    } finally {
      setLoadingCsv(false)
    }
  }

  async function downloadReport() {
    setLoadingPdf(true)
    try {
      const resp = await fetch(apiUrl('/api/export/report'))
      const data = await resp.json()
      if (data.error) {
        alert(data.error)
        return
      }
      // Genera contenuto testuale del report
      const lines = [
        data.title,
        `Generato: ${new Date(data.generated_at).toLocaleString('it-IT')}`,
        '',
        `Score attuale: ${data.current.score} (${data.current.level})`,
        `Trend: ${data.current.trend > 0 ? '+' : ''}${data.current.trend}`,
        '',
        '=== DIMENSIONI ===',
        ...data.dimensions.map(d =>
          `${d.name.toUpperCase()}: ${d.score} (peso ${(d.weight * 100).toFixed(0)}%, trend ${d.trend > 0 ? '+' : ''}${d.trend})`
        ),
        '',
        '=== ANOMALIE ===',
        ...(data.anomalies.length > 0
          ? data.anomalies.map(a => `⚠ ${a.dimension}/${a.proxy}: ${a.value} (z=${a.z_score}, ${a.direction})`)
          : ['Nessuna anomalia rilevata']),
        '',
        '=== STORICO 7 GIORNI ===',
        ...data.history_7d.map(h =>
          `${new Date(h.timestamp).toLocaleDateString('it-IT')} ${new Date(h.timestamp).toLocaleTimeString('it-IT', { hour: '2-digit', minute: '2-digit' })}: ${h.score} (${h.level})`
        ),
        '',
        data.disclaimer,
      ]
      const text = lines.join('\n')
      const blob = new Blob([text], { type: 'text/plain;charset=utf-8' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `sentinella_report_${new Date().toISOString().slice(0, 10)}.txt`
      a.click()
      URL.revokeObjectURL(url)
    } catch (e) {
      console.error('Export report failed:', e)
    } finally {
      setLoadingPdf(false)
    }
  }

  return (
    <div className="flex gap-2">
      <button
        onClick={downloadCsv}
        disabled={loadingCsv}
        className="flex items-center gap-1.5 px-3 py-1.5 bg-term-surface border border-term-border rounded-lg text-xs text-gray-400 hover:text-white hover:border-indigo-500 transition-colors disabled:opacity-50"
      >
        <Download className="w-3 h-3" />
        {loadingCsv ? 'Download...' : 'CSV 30gg'}
      </button>
      <button
        onClick={downloadReport}
        disabled={loadingPdf}
        className="flex items-center gap-1.5 px-3 py-1.5 bg-term-surface border border-term-border rounded-lg text-xs text-gray-400 hover:text-white hover:border-indigo-500 transition-colors disabled:opacity-50"
      >
        <Download className="w-3 h-3" />
        {loadingPdf ? 'Generazione...' : 'Report'}
      </button>
    </div>
  )
}
