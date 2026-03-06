import { useState } from 'react'
import { Shield, AlertTriangle, ExternalLink } from 'lucide-react'

const STORAGE_KEY = 'sentinella_disclaimer_v1'

export function useDisclaimer() {
  const [accepted, setAccepted] = useState(() =>
    localStorage.getItem(STORAGE_KEY) === 'true'
  )

  function accept() {
    localStorage.setItem(STORAGE_KEY, 'true')
    setAccepted(true)
  }

  return { accepted, accept }
}

export default function DisclaimerModal({ onAccept }) {
  const [checked, setChecked] = useState(false)

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-gray-950/95 backdrop-blur">
      <div className="bg-gray-900 border border-gray-700 rounded-2xl w-full max-w-lg shadow-2xl">

        {/* Header */}
        <div className="flex items-center gap-3 px-6 pt-6 pb-4 border-b border-gray-800">
          <div className="w-10 h-10 rounded-full bg-indigo-500/20 flex items-center justify-center flex-shrink-0">
            <Shield className="w-5 h-5 text-indigo-400" />
          </div>
          <div>
            <h1 className="font-bold text-lg">Sentinella Italia</h1>
            <p className="text-xs text-gray-500">Dashboard OSINT sicurezza nazionale</p>
          </div>
        </div>

        <div className="px-6 py-5 space-y-4">

          {/* Cosa è */}
          <div>
            <p className="text-sm font-semibold text-gray-300 mb-2">Questo strumento:</p>
            <ul className="space-y-1.5">
              {[
                'Aggrega dati pubblici (GDELT, CSIRT, Google Trends, OpenSky)',
                'Rileva anomalie statistiche rispetto agli ultimi 90 giorni',
                'È open source e completamente trasparente nella metodologia',
                'È aggiornato automaticamente ogni 30 minuti',
              ].map(s => (
                <li key={s} className="flex items-start gap-2 text-sm text-gray-400">
                  <span className="text-green-500 mt-0.5 flex-shrink-0">✓</span> {s}
                </li>
              ))}
            </ul>
          </div>

          {/* Cosa NON è — warning box */}
          <div className="bg-yellow-950/40 border border-yellow-800/50 rounded-xl p-4">
            <div className="flex items-center gap-2 mb-2">
              <AlertTriangle className="w-4 h-4 text-yellow-500 flex-shrink-0" />
              <p className="text-sm font-semibold text-yellow-400">Questo strumento NON è:</p>
            </div>
            <ul className="space-y-1">
              {[
                'Un livello di allerta ufficiale del Governo italiano',
                'Una fonte di intelligence o informazioni classificate',
                'Un sistema di allarme per emergenze reali',
                'Un sostituto delle comunicazioni delle autorità competenti',
              ].map(s => (
                <li key={s} className="flex items-start gap-2 text-sm text-yellow-200/70">
                  <span className="flex-shrink-0 mt-0.5">×</span> {s}
                </li>
              ))}
            </ul>
          </div>

          {/* Emergenza */}
          <p className="text-xs text-gray-600 text-center">
            In caso di emergenza reale, contatta il{' '}
            <span className="font-bold text-gray-400">112</span> o segui le indicazioni
            della{' '}
            <span className="font-semibold text-gray-400">Protezione Civile</span>.
          </p>

          {/* Checkbox */}
          <label className="flex items-start gap-3 cursor-pointer group">
            <div
              className={`w-5 h-5 rounded border flex-shrink-0 mt-0.5 flex items-center justify-center transition-colors ${
                checked
                  ? 'bg-indigo-600 border-indigo-600'
                  : 'border-gray-600 group-hover:border-gray-400'
              }`}
              onClick={() => setChecked(c => !c)}
            >
              {checked && <span className="text-white text-xs font-bold">✓</span>}
            </div>
            <span className="text-sm text-gray-400 leading-snug select-none" onClick={() => setChecked(c => !c)}>
              Ho letto e compreso che questo è uno strumento sperimentale basato su proxy pubblici,
              non un indicatore ufficiale di sicurezza nazionale.
            </span>
          </label>
        </div>

        {/* Footer */}
        <div className="px-6 pb-6 flex items-center justify-between gap-4">
          <a
            href="https://github.com"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1 text-xs text-gray-600 hover:text-gray-400 transition-colors"
          >
            <ExternalLink className="w-3 h-3" /> Metodologia completa
          </a>
          <button
            disabled={!checked}
            onClick={onAccept}
            className={`px-5 py-2 rounded-xl text-sm font-semibold transition-all ${
              checked
                ? 'bg-indigo-600 hover:bg-indigo-500 text-white'
                : 'bg-gray-800 text-gray-600 cursor-not-allowed'
            }`}
          >
            Accetta e continua
          </button>
        </div>
      </div>
    </div>
  )
}
