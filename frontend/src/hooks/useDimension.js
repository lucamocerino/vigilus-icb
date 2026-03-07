import { useState, useEffect } from 'react'
import { apiUrl } from '../utils/api.js'

export function useDimension(name) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!name) return
    fetch(apiUrl(`/api/dimension/${name}`))
      .then(r => r.json())
      .then(d => {
        setData(d)
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [name])

  return { data, loading }
}
