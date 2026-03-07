/**
 * API base URL — uses Vite proxy in dev, env variable in production.
 * Set VITE_API_URL in environment for production builds.
 */
const API_BASE = import.meta.env.VITE_API_URL || ''

export function apiUrl(path) {
  return `${API_BASE}${path}`
}

export function wsUrl(path) {
  if (API_BASE) {
    const base = API_BASE.replace(/^http/, 'ws')
    return `${base}${path}`
  }
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${proto}//${window.location.host}${path}`
}
