import { useState, useEffect } from 'react'

export function useDimension(name) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!name) return
    fetch(`/api/dimension/${name}`)
      .then(r => r.json())
      .then(d => {
        setData(d)
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [name])

  return { data, loading }
}
