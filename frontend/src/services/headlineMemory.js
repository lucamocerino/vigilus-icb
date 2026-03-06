/**
 * Headline Memory — browser-local semantic index using IndexedDB.
 * Stores headline tokens for RAG-powered queries.
 * All data stays in the browser — no server calls needed.
 */

const DB_NAME = 'vigilus_memory'
const DB_VERSION = 1
const STORE_NAME = 'headlines'
const MAX_HEADLINES = 5000

function openDB() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, DB_VERSION)
    req.onupgradeneeded = () => {
      const db = req.result
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        const store = db.createObjectStore(STORE_NAME, { keyPath: 'id', autoIncrement: true })
        store.createIndex('timestamp', 'timestamp')
      }
    }
    req.onsuccess = () => resolve(req.result)
    req.onerror = () => reject(req.error)
  })
}

const STOP = new Set([
  'il','lo','la','le','li','gli','un','uno','una','di','da','in','con','su','per',
  'che','non','più','come','anche','sono','nel','nella','dei','del','della','delle',
  'the','and','for','with','from','has','was','are','but','not','all','new','this',
])

function tokenize(text) {
  return text.toLowerCase()
    .replace(/[^\w\sà-ü]/g, ' ')
    .split(/\s+/)
    .filter(w => w.length >= 3 && !STOP.has(w))
}

export async function storeHeadlines(headlines) {
  const db = await openDB()
  const tx = db.transaction(STORE_NAME, 'readwrite')
  const store = tx.objectStore(STORE_NAME)
  const now = Date.now()

  for (const h of headlines) {
    const tokens = tokenize(h.title || '')
    if (tokens.length < 2) continue
    store.put({
      title: h.title,
      source: h.source || '',
      dimension: h.dimension || '',
      url: h.url || '',
      tokens,
      timestamp: now,
    })
  }

  // Evict oldest if over limit
  const countReq = store.count()
  countReq.onsuccess = () => {
    if (countReq.result > MAX_HEADLINES) {
      const idx = store.index('timestamp')
      const deleteCount = countReq.result - MAX_HEADLINES
      let deleted = 0
      const cursor = idx.openCursor()
      cursor.onsuccess = () => {
        const c = cursor.result
        if (c && deleted < deleteCount) {
          c.delete()
          deleted++
          c.continue()
        }
      }
    }
  }

  return new Promise((resolve, reject) => {
    tx.oncomplete = () => resolve()
    tx.onerror = () => reject(tx.error)
  })
}

export async function searchMemory(query, limit = 20) {
  const queryTokens = tokenize(query)
  if (!queryTokens.length) return []

  const db = await openDB()
  const tx = db.transaction(STORE_NAME, 'readonly')
  const store = tx.objectStore(STORE_NAME)

  return new Promise((resolve, reject) => {
    const results = []
    const req = store.openCursor(null, 'prev')

    req.onsuccess = () => {
      const cursor = req.result
      if (!cursor || results.length >= 500) {
        results.sort((a, b) => b._score - a._score)
        resolve(results.slice(0, limit).map(({ _score, ...r }) => ({ ...r, relevance: Math.round(_score * 100) })))
        return
      }

      const record = cursor.value
      const recordTokens = new Set(record.tokens || [])
      const matches = queryTokens.filter(t => recordTokens.has(t))
      if (matches.length > 0) {
        results.push({ ...record, _score: matches.length / queryTokens.length })
      }
      cursor.continue()
    }
    req.onerror = () => reject(req.error)
  })
}

export async function getMemoryStats() {
  try {
    const db = await openDB()
    const tx = db.transaction(STORE_NAME, 'readonly')
    const store = tx.objectStore(STORE_NAME)
    return new Promise((resolve) => {
      const c = store.count()
      c.onsuccess = () => resolve({ total: c.result, max: MAX_HEADLINES })
      c.onerror = () => resolve({ total: 0, max: MAX_HEADLINES })
    })
  } catch {
    return { total: 0, max: MAX_HEADLINES }
  }
}

export async function clearMemory() {
  const db = await openDB()
  const tx = db.transaction(STORE_NAME, 'readwrite')
  tx.objectStore(STORE_NAME).clear()
  return new Promise((r) => { tx.oncomplete = r })
}
