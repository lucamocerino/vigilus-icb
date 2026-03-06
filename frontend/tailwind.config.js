/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      fontFamily: {
        sans: ['"IBM Plex Mono"', 'ui-monospace', 'monospace'],
        mono: ['"IBM Plex Mono"', 'ui-monospace', 'monospace'],
      },
      colors: {
        term: {
          bg:      'var(--term-bg)',
          surface: 'var(--term-surface)',
          border:  'var(--term-border)',
          muted:   'var(--term-muted)',
          dim:     'var(--term-dim)',
        },
        calmo:      '#00c48c',
        normale:    '#3b82f6',
        attenzione: '#f59f00',
        elevato:    '#f97316',
        critico:    '#ef4444',
      },
      screens: {
        'xs': '480px',
      },
    },
  },
  plugins: [],
}
