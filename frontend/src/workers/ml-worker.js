/**
 * Browser-side ML Worker — runs NER + sentiment via Transformers.js
 * Executes in a Web Worker so it never blocks the UI thread.
 */
let pipeline = null
let sentimentPipeline = null
let isLoading = false

async function loadModels() {
  if (pipeline || isLoading) return
  isLoading = true

  try {
    const { pipeline: createPipeline } = await import('@xenova/transformers')

    self.postMessage({ type: 'status', status: 'loading', message: 'Caricamento modello sentiment...' })
    sentimentPipeline = await createPipeline('sentiment-analysis', 'Xenova/distilbert-base-uncased-finetuned-sst-2-english', {
      quantized: true,
    })

    self.postMessage({ type: 'status', status: 'ready', message: 'Modelli ML pronti' })
  } catch (e) {
    self.postMessage({ type: 'status', status: 'error', message: e.message })
  } finally {
    isLoading = false
  }
}

async function classifySentiment(texts) {
  if (!sentimentPipeline) {
    await loadModels()
    if (!sentimentPipeline) return texts.map(() => ({ label: 'UNKNOWN', score: 0 }))
  }

  const results = []
  // Process in batches of 8
  for (let i = 0; i < texts.length; i += 8) {
    const batch = texts.slice(i, i + 8)
    const batchResults = await sentimentPipeline(batch, { truncation: true, max_length: 128 })
    // Pipeline returns single result or array
    const arr = Array.isArray(batchResults[0]) ? batchResults : [batchResults].flat()
    results.push(...arr)
  }
  return results
}

// Keyword-based threat classification (instant, no model needed)
const THREAT_KEYWORDS = {
  critical: ['attentato', 'esplosione', 'bomba', 'strage', 'guerra', 'attacco armato', 'nucleare', 'evacuazione'],
  high: ['terrorismo', 'hacker', 'ransomware', 'emergenza', 'allerta', 'crisi', 'scontri', 'rivolta'],
  medium: ['protesta', 'sciopero', 'manifestazione', 'incidente', 'arresto', 'sequestro', 'indagine'],
  low: ['accordo', 'cooperazione', 'incontro', 'vertice', 'conferenza', 'riforma'],
}

function classifyThreat(text) {
  const lower = text.toLowerCase()
  for (const [level, keywords] of Object.entries(THREAT_KEYWORDS)) {
    if (keywords.some(kw => lower.includes(kw))) return level
  }
  return 'none'
}

self.onmessage = async (event) => {
  const { type, data, id } = event.data

  switch (type) {
    case 'init':
      await loadModels()
      break

    case 'classify': {
      // Classify headlines: threat level (instant) + sentiment (ML)
      const headlines = data.headlines || []
      const texts = headlines.map(h => h.title || '')

      // 1. Instant keyword classification
      const threats = texts.map(classifyThreat)

      // 2. ML sentiment (async)
      let sentiments
      try {
        sentiments = await classifySentiment(texts)
      } catch {
        sentiments = texts.map(() => ({ label: 'UNKNOWN', score: 0 }))
      }

      const results = headlines.map((h, i) => ({
        ...h,
        threat_level: threats[i],
        sentiment: sentiments[i]?.label || 'UNKNOWN',
        sentiment_score: sentiments[i]?.score || 0,
      }))

      self.postMessage({ type: 'classify_result', id, results })
      break
    }
  }
}
