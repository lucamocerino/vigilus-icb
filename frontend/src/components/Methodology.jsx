import { DIMENSION_COLORS, DIMENSION_LABELS, LEVELS } from '../utils/colors.js'

const DIMENSIONS_INFO = [
  {
    key: 'geopolitica',
    weight: '25%',
    description: 'Tensione internazionale con impatto diretto o indiretto sull\'Italia.',
    sources: ['GDELT Goldstein Scale', 'GDELT Tone medio articoli', 'ACLED conflitti regionali'],
    proxies: [
      'Volume articoli su tensioni che coinvolgono l\'Italia',
      'Tone medio della copertura mediatica (negativo = tensione)',
      'Rapporto articoli negativi/totali su temi di sicurezza',
    ],
  },
  {
    key: 'terrorismo',
    weight: '20%',
    description: 'Rischio terroristico diretto e indiretto su territorio italiano o interessi italiani.',
    sources: ['GDELT eventi terrorismo EU', 'Google Trends IT', 'RSS keyword matching'],
    proxies: [
      'Conteggio articoli con tema terrorismo che menzionano l\'Italia',
      'Interesse di ricerca per termini come "attentato", "terrorismo Italia"',
      'Tone medio articoli su eventi terroristici',
    ],
  },
  {
    key: 'cyber',
    weight: '15%',
    description: 'Attacchi informatici e vulnerabilità che colpiscono infrastrutture italiane.',
    sources: ['CSIRT Italia / ACN', 'GDELT tema cyber'],
    proxies: [
      'Numero bollettini sicurezza emessi da CSIRT Italia',
      'Gravità bollettini (critica/alta/media)',
      'Numero CVE menzionate in relazione a PA e infrastrutture critiche',
    ],
  },
  {
    key: 'eversione',
    weight: '15%',
    description: 'Estremismo interno: movimenti anarco-insurrezionali, estrema destra/sinistra, disordini.',
    sources: ['GDELT proteste Italia', 'ACLED Italia', 'RSS keyword matching'],
    proxies: [
      'Conteggio eventi protest e riot in Italia (GDELT)',
      'Numero eventi violenza/protesta ACLED in Italia',
      'Volume articoli su estremismo e disordini interni',
    ],
  },
  {
    key: 'militare',
    weight: '15%',
    description: 'Movimenti militari anomali e postura difensiva di Italia e NATO.',
    sources: ['OpenSky Network (ADS-B)', 'Google Trends', 'GDELT tema difesa'],
    proxies: [
      'Numero voli nelle aree delle basi militari IT (Aviano, Sigonella, Ghedi, Amendola)',
      'Interesse di ricerca per basi NATO e notizie militari',
      'Volume copertura mediatica su temi militari/difesa',
    ],
  },
  {
    key: 'sociale',
    weight: '10%',
    description: 'Tensione sociale: scioperi, manifestazioni, disordini e clima generale.',
    sources: ['Google Trends IT', 'GDELT proteste', 'ACLED Italia'],
    proxies: [
      'Interesse di ricerca per "manifestazione", "sciopero", "protesta"',
      'Volume articoli su tensioni sociali (GDELT)',
      'Conteggio eventi protesta (ACLED)',
    ],
  },
]

const SCORE_LEVELS = [
  { range: '0 – 20',  label: 'CALMO',      color: '#22c55e', desc: 'I proxy indicano una situazione sotto la media storica degli ultimi 90 giorni.' },
  { range: '21 – 40', label: 'NORMALE',    color: '#3b82f6', desc: 'I proxy sono nella norma storica. Nessuna anomalia rilevante.' },
  { range: '41 – 60', label: 'ATTENZIONE', color: '#eab308', desc: 'Alcuni proxy mostrano valori sopra la media. Situazione da monitorare.' },
  { range: '61 – 80', label: 'ELEVATO',    color: '#f97316', desc: 'Anomalie significative su piu\' dimensioni (1-2 deviazioni standard sopra la media).' },
  { range: '81 – 100', label: 'CRITICO',   color: '#ef4444', desc: 'Anomalie estreme, situazione mai vista nei 90 giorni precedenti (>2 dev. standard).' },
]

export default function Methodology() {
  return (
    <div className="max-w-4xl mx-auto px-4 py-8 space-y-10">

      {/* Intro */}
      <section>
        <h1 className="text-2xl font-bold mb-3">Come viene calcolato lo score</h1>
        <p className="text-gray-400 leading-relaxed">
          Sentinella Italia produce un <strong className="text-white">indice composito 0-100</strong> che misura
          quanto la situazione attuale e&apos; anomala rispetto alla baseline storica degli ultimi 90 giorni.
          Non e&apos; una valutazione di intelligence: e&apos; un aggregatore statistico di segnali pubblici.
        </p>
      </section>

      {/* Formula */}
      <section className="card">
        <h2 className="text-lg font-semibold mb-4">Formula dello score sintetico</h2>
        <div className="bg-gray-950 rounded-lg p-4 font-mono text-sm overflow-x-auto">
          <p className="text-green-400 mb-2">{'# Score finale (media pesata delle 6 dimensioni)'}</p>
          <p className="text-gray-200">score = (</p>
          {DIMENSIONS_INFO.map((d, i) => (
            <p key={d.key} className="ml-6" style={{ color: DIMENSION_COLORS[d.key] }}>
              {DIMENSION_LABELS[d.key].toLowerCase()}_score * {parseFloat(d.weight) / 100}
              {i < DIMENSIONS_INFO.length - 1 ? ' +' : ''}
            </p>
          ))}
          <p className="text-gray-200">)</p>
        </div>

        <div className="mt-4 p-4 bg-gray-950 rounded-lg font-mono text-sm">
          <p className="text-green-400 mb-2">{'# Ogni sotto-indice è un z-score normalizzato su 0-100'}</p>
          <p className="text-gray-400">{'sotto_indice = normalize('}</p>
          <p className="text-gray-200 ml-6">{'(valore_attuale - media_90gg)'}</p>
          <p className="text-gray-200 ml-6">{'─────────────────────────────'}</p>
          <p className="text-gray-200 ml-6">{'     deviazione_standard_90gg'}</p>
          <p className="text-gray-400">{')'}</p>
        </div>

        <p className="mt-3 text-sm text-gray-500">
          Il z-score viene poi mappato su scala 0-100 con clip a ±3 deviazioni standard.
          z=0 (nella media) corrisponde a circa 50. Valori negativi (sotto la media) danno score basso.
        </p>
      </section>

      {/* Livelli */}
      <section>
        <h2 className="text-lg font-semibold mb-4">Scala dei livelli</h2>
        <div className="space-y-2">
          {SCORE_LEVELS.map(l => (
            <div key={l.label} className="card flex items-start gap-4">
              <div
                className="flex-shrink-0 w-24 text-center py-1 rounded-full text-xs font-bold"
                style={{ backgroundColor: l.color + '22', color: l.color, border: `1px solid ${l.color}44` }}
              >
                {l.range}
              </div>
              <div>
                <span className="font-semibold" style={{ color: l.color }}>{l.label}</span>
                <p className="text-sm text-gray-400 mt-0.5">{l.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Dimensioni */}
      <section>
        <h2 className="text-lg font-semibold mb-4">Le 6 dimensioni</h2>
        <div className="space-y-4">
          {DIMENSIONS_INFO.map(d => (
            <div key={d.key} className="card">
              <div className="flex items-center gap-3 mb-2">
                <div
                  className="w-3 h-3 rounded-full flex-shrink-0"
                  style={{ backgroundColor: DIMENSION_COLORS[d.key] }}
                />
                <h3 className="font-semibold" style={{ color: DIMENSION_COLORS[d.key] }}>
                  {DIMENSION_LABELS[d.key]}
                </h3>
                <span className="ml-auto text-xs text-gray-500 bg-gray-800 px-2 py-0.5 rounded-full">
                  peso {d.weight}
                </span>
              </div>
              <p className="text-sm text-gray-400 mb-3">{d.description}</p>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div>
                  <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">Fonti</p>
                  <ul className="space-y-0.5">
                    {d.sources.map(s => (
                      <li key={s} className="text-xs text-gray-400 flex items-center gap-1.5">
                        <span className="w-1 h-1 rounded-full bg-gray-600 flex-shrink-0" />
                        {s}
                      </li>
                    ))}
                  </ul>
                </div>
                <div>
                  <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">Proxy misurati</p>
                  <ul className="space-y-0.5">
                    {d.proxies.map(p => (
                      <li key={p} className="text-xs text-gray-400 flex items-start gap-1.5">
                        <span className="w-1 h-1 rounded-full mt-1.5 flex-shrink-0" style={{ backgroundColor: DIMENSION_COLORS[d.key] }} />
                        {p}
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Aggiornamento */}
      <section className="card">
        <h2 className="text-lg font-semibold mb-3">Frequenza di aggiornamento</h2>
        <div className="flex flex-wrap gap-2 mb-3">
          {['02:00', '06:00', '10:00', '14:00', '18:00', '22:00'].map(h => (
            <span key={h} className="px-3 py-1 bg-indigo-900/40 border border-indigo-800/50 rounded-full text-sm text-indigo-300 font-mono">
              {h} CET
            </span>
          ))}
        </div>
        <p className="text-sm text-gray-400">
          6 aggiornamenti al giorno. GDELT aggiorna ogni 15 minuti ma aggreghiamo ogni 4 ore
          per ridurre il rumore e rispettare i rate limit di Google Trends (latenza 24-48h).
          ACLED viene integrato su ciclo settimanale.
        </p>
      </section>

      {/* Limiti */}
      <section className="card border-yellow-900/40">
        <h2 className="text-lg font-semibold mb-3 text-yellow-400">Limiti e avvertenze</h2>
        <ul className="space-y-2 text-sm text-gray-400">
          <li className="flex items-start gap-2">
            <span className="text-yellow-500 mt-0.5">!</span>
            <span><strong className="text-gray-300">Falsi positivi:</strong> eventi mediatici di grande portata possono far salire lo score senza un reale aumento del rischio.</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-yellow-500 mt-0.5">!</span>
            <span><strong className="text-gray-300">Baseline corta:</strong> nelle prime settimane di utilizzo la baseline e&apos; basata su valori statici. La qualita&apos; migliora dopo 90 giorni di dati reali.</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-yellow-500 mt-0.5">!</span>
            <span><strong className="text-gray-300">Fonti indirette:</strong> tutti i dati sono proxy pubblici. Non accediamo a dati riservati o di intelligence.</span>
          </li>
          <li className="flex items-start gap-2">
            <span className="text-yellow-500 mt-0.5">!</span>
            <span><strong className="text-gray-300">Non e&apos; un allerta ufficiale:</strong> lo score non sostituisce le comunicazioni delle autorita&apos; competenti.</span>
          </li>
        </ul>
      </section>

    </div>
  )
}
