/**
 * StatusPanel — Three step cards showing pipeline progress.
 * States: pending / active (+ pulse) / done / error
 * Zero business logic — purely presentational.
 */
export default function StatusPanel({ steps }) {
  const stepLabels = [
    'Harvesting Signals',
    'Building Account Brief',
    'Sending Email',
  ]

  const getStatusIcon = (status) => {
    switch (status) {
      case 'done':
      case 'sent':
        return (
          <span className="flex h-6 w-6 items-center justify-center rounded-full bg-green-500/20 text-green-400">
            <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
            </svg>
          </span>
        )
      case 'running':
        return (
          <span className="flex h-6 w-6 items-center justify-center rounded-full bg-orange-500/20">
            <span className="h-2.5 w-2.5 rounded-full bg-orange-400 animate-pulse-dot" />
          </span>
        )
      case 'error':
        return (
          <span className="flex h-6 w-6 items-center justify-center rounded-full bg-red-500/20 text-red-400">
            <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </span>
        )
      case 'review':
        return (
          <span className="flex h-6 w-6 items-center justify-center rounded-full bg-yellow-500/20 text-yellow-400">
            <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01M12 3l9.5 16.5H2.5L12 3z" />
            </svg>
          </span>
        )
      default: // pending
        return (
          <span className="flex h-6 w-6 items-center justify-center rounded-full bg-gray-700/50">
            <span className="h-2 w-2 rounded-full bg-gray-500" />
          </span>
        )
    }
  }

  const getStatusColor = (status) => {
    switch (status) {
      case 'done':
      case 'sent':
        return 'border-green-500/30 bg-green-500/5'
      case 'running':
        return 'border-orange-500/30 bg-orange-500/5'
      case 'error':
        return 'border-red-500/30 bg-red-500/5'
      case 'review':
        return 'border-yellow-500/30 bg-yellow-500/5'
      default:
        return 'border-gray-700/50 bg-gray-800/30'
    }
  }

  return (
    <div className="space-y-3">
      <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-400">Pipeline Status</h3>
      <div className="space-y-2">
        {stepLabels.map((label, idx) => {
          const step = steps[idx] || {}
          const status = step.status || 'pending'
          return (
            <div
              key={idx}
              className={`flex items-center gap-3 rounded-lg border px-4 py-3 transition-all duration-300 ${getStatusColor(status)}`}
            >
              {getStatusIcon(status)}
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-gray-200">{label}</p>
                {step.label && status === 'running' && (
                  <p className="text-xs text-gray-400 mt-0.5">{step.label}</p>
                )}
              </div>
              {/* Signal count badge */}
              {idx === 0 && (status === 'done' || status === 'sent') && step.payload?.signal_count != null && (
                <span className="rounded-full bg-green-500/20 px-2.5 py-0.5 text-xs font-medium text-green-400">
                  {step.payload.signal_count} signals
                </span>
              )}
              {/* Score badge on step 3 */}
              {idx === 2 && step.payload?.score != null && (
                <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${
                  step.payload.score >= 60
                    ? 'bg-green-500/20 text-green-400'
                    : 'bg-yellow-500/20 text-yellow-400'
                }`}>
                  Score: {step.payload.score}
                </span>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
