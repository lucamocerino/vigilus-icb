const translations = {
  it: {
    dashboard: 'DASHBOARD',
    compare: 'CONFRONTO',
    methodology: 'METODOLOGIA',
    score: 'Score',
    trending: 'TRENDING KEYWORDS',
    anomalies: 'ANOMALIE',
    events: 'ULTIMI EVENTI',
    sources: 'STATO FONTI',
    narrative: 'ANALISI',
    map: 'MAPPA OPERATIVA',
    regional: 'BREAKDOWN REGIONALE',
    export_csv: 'CSV 30gg',
    export_report: 'Report',
    search: 'RICERCA EVENTI',
    digest: 'DAILY DIGEST — 24H',
    memory: 'HEADLINE MEMORY',
    classifier: 'ML CLASSIFIER',
    keywords: 'KEYWORD MONITOR',
    hotspot: 'HOTSPOT & CORRELAZIONI',
    predictions: 'PREDICTION MARKETS',
    outages: 'INFRASTRUTTURE DIGITALI',
    region_brief: 'DOSSIER REGIONALE',
    live: 'LIVE STREAMS',
    share: 'Condividi',
    light_mode: 'Light mode',
    dark_mode: 'Dark mode',
    disclaimer: 'NON è un livello di allerta ufficiale. Anomalie statistiche su dati pubblici.',
    no_data: 'Nessun dato ancora disponibile',
    trigger: 'Avvia primo calcolo score',
    loading: 'Connessione al backend...',
    backend_error: 'Backend non raggiungibile',
  },
  en: {
    dashboard: 'DASHBOARD',
    compare: 'COMPARISON',
    methodology: 'METHODOLOGY',
    score: 'Score',
    trending: 'TRENDING KEYWORDS',
    anomalies: 'ANOMALIES',
    events: 'LATEST EVENTS',
    sources: 'SOURCE STATUS',
    narrative: 'ANALYSIS',
    map: 'OPERATIONAL MAP',
    regional: 'REGIONAL BREAKDOWN',
    export_csv: 'CSV 30d',
    export_report: 'Report',
    search: 'EVENT SEARCH',
    digest: 'DAILY DIGEST — 24H',
    memory: 'HEADLINE MEMORY',
    classifier: 'ML CLASSIFIER',
    keywords: 'KEYWORD MONITOR',
    hotspot: 'HOTSPOT & CORRELATIONS',
    predictions: 'PREDICTION MARKETS',
    outages: 'DIGITAL INFRASTRUCTURE',
    region_brief: 'REGIONAL BRIEF',
    live: 'LIVE STREAMS',
    share: 'Share',
    light_mode: 'Light mode',
    dark_mode: 'Dark mode',
    disclaimer: 'NOT an official alert level. Statistical anomalies from public proxies.',
    no_data: 'No data available yet',
    trigger: 'Start first score calculation',
    loading: 'Connecting to backend...',
    backend_error: 'Backend unreachable',
  },
}

export function createI18n() {
  let lang = localStorage.getItem('vigilus_lang') || 'it'

  return {
    get lang() { return lang },
    t(key) { return translations[lang]?.[key] || translations.it[key] || key },
    setLang(l) {
      lang = l
      localStorage.setItem('vigilus_lang', l)
    },
    toggle() {
      const next = lang === 'it' ? 'en' : 'it'
      this.setLang(next)
      return next
    },
  }
}
