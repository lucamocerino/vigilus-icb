export function formatDate(isoString) {
  if (!isoString) return '—'
  return new Date(isoString).toLocaleString('it-IT', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export function formatDateShort(isoString) {
  if (!isoString) return '—'
  return new Date(isoString).toLocaleDateString('it-IT', {
    day: '2-digit',
    month: '2-digit',
  })
}

export function formatScore(score) {
  return typeof score === 'number' ? score.toFixed(1) : '—'
}
