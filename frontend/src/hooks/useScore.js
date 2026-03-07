import { useState, useEffect, useCallback } from 'react'
import { apiUrl } from '../utils/api.js'

const MAX_RETRIES = 3
const RETRY_DELAY = 2000

async function fetchWithRetry(url, retries = MAX_RETRIES) {
  for (let i = 0; i <= retries; i++) {
    try {
      const r = await fetch(url)
      if (r.status === 404) return null   // nessun dato ancora — non è un errore
      if (!r.ok) throw new Error(`HTTP ${r.status}`)
      return await r.json()
    } catch (err) {
      if (i === retries) throw err
      await new Promise(res => setTimeout(res, RETRY_DELAY * (i + 1)))
    }
  }
}

export function useScore() {
  const [score, setScore]   = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError]   = useState(null)

  const load = useCallback(async () => {
    try {
      setError(null)
      const data = await fetchWithRetry(apiUrl('/api/score/current'))
      setScore(data)   // può essere null se 404
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  return { score, loading, error, setScore, reload: load }
}

export function useScoreHistory(days = 30) {
  const [history, setHistory] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchWithRetry(apiUrl(`/api/score/history?days=${days}`))
      .then(data => setHistory(data ?? []))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [days])

  return { history, loading }
}
