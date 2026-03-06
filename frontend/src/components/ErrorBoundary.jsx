import { Component } from 'react'
import { AlertTriangle, RefreshCw } from 'lucide-react'

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }

  componentDidCatch(error, info) {
    console.error('[ErrorBoundary]', error, info)
  }

  render() {
    if (!this.state.hasError) return this.props.children

    const { fallback } = this.props
    if (fallback) return fallback

    return (
      <div className="card flex flex-col items-center gap-3 py-8 text-center">
        <AlertTriangle className="w-8 h-8 text-yellow-500" />
        <p className="text-sm font-medium text-gray-300">
          {this.props.label ?? 'Errore nel componente'}
        </p>
        <p className="text-xs text-gray-600 max-w-xs">
          {this.state.error?.message ?? 'Errore sconosciuto'}
        </p>
        <button
          onClick={() => this.setState({ hasError: false, error: null })}
          className="flex items-center gap-2 text-xs px-3 py-1.5 bg-gray-800 hover:bg-gray-700 rounded-lg transition-colors"
        >
          <RefreshCw className="w-3 h-3" /> Riprova
        </button>
      </div>
    )
  }
}
