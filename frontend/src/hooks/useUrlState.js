import { useEffect } from 'react'

/**
 * Encode/decode dashboard state in URL for sharing.
 * Syncs page, historyDays to URL params.
 */
export function useUrlState(page, setPage, historyDays, setHistoryDays) {
  // Read from URL on mount
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const p = params.get('page')
    if (p && ['dashboard', 'compare', 'methodology'].includes(p)) setPage(p)
    const d = parseInt(params.get('days'))
    if (d && d > 0 && d <= 365) setHistoryDays(d)
  }, [])

  // Write to URL on change
  useEffect(() => {
    const params = new URLSearchParams()
    if (page !== 'dashboard') params.set('page', page)
    if (historyDays !== 30) params.set('days', historyDays)
    const qs = params.toString()
    const url = qs ? `${window.location.pathname}?${qs}` : window.location.pathname
    window.history.replaceState(null, '', url)
  }, [page, historyDays])
}
