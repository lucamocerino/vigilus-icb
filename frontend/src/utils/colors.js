export const LEVELS = [
  { min: 0,  max: 20,  label: 'CALMO',      color: '#22c55e', bg: 'bg-green-500' },
  { min: 21, max: 40,  label: 'NORMALE',    color: '#3b82f6', bg: 'bg-blue-500' },
  { min: 41, max: 60,  label: 'ATTENZIONE', color: '#eab308', bg: 'bg-yellow-500' },
  { min: 61, max: 80,  label: 'ELEVATO',    color: '#f97316', bg: 'bg-orange-500' },
  { min: 81, max: 100, label: 'CRITICO',    color: '#ef4444', bg: 'bg-red-500' },
]

export function getLevel(score) {
  return LEVELS.find(l => score >= l.min && score <= l.max) ?? LEVELS[4]
}

export function scoreColor(score) {
  return getLevel(score).color
}

export const DIMENSION_COLORS = {
  geopolitica: '#6366f1',
  terrorismo:  '#ef4444',
  cyber:       '#06b6d4',
  eversione:   '#f59e0b',
  militare:    '#64748b',
  sociale:     '#22c55e',
}

export const DIMENSION_LABELS = {
  geopolitica: 'Geopolitica',
  terrorismo:  'Terrorismo',
  cyber:       'Cyber',
  eversione:   'Eversione',
  militare:    'Militare',
  sociale:     'Sociale',
}
