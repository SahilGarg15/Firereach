/**
 * ErrorBanner — Full-width error display.
 * Shows error code + user-facing message.
 * On EMAIL_SEND_FAILED: renders email draft below the banner, copyable.
 * Zero business logic — purely presentational.
 */
export default function ErrorBanner({ error }) {
  if (!error) return null

  const copyDraft = () => {
    if (error.payload?.email_body) {
      navigator.clipboard.writeText(error.payload.email_body)
    }
  }

  return (
    <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-4 space-y-3">
      <div className="flex items-start gap-3">
        <span className="flex h-6 w-6 items-center justify-center rounded-full bg-red-500/20 text-red-400 flex-shrink-0 mt-0.5">
          <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </span>
        <div>
          <p className="text-sm font-medium text-red-400">{error.code}</p>
          <p className="text-sm text-gray-300 mt-0.5">{error.message}</p>
        </div>
      </div>

      {/* On EMAIL_SEND_FAILED: show the draft for manual copy */}
      {error.code === 'EMAIL_SEND_FAILED' && error.payload?.email_body && (
        <div className="mt-3 space-y-2">
          <div className="flex items-center justify-between">
            <p className="text-xs font-medium text-gray-400">Email Draft (copy manually)</p>
            <button
              onClick={copyDraft}
              className="rounded bg-gray-700 px-3 py-1 text-xs text-gray-300 hover:bg-gray-600 transition-colors"
            >
              Copy to Clipboard
            </button>
          </div>
          <pre className="rounded-lg bg-gray-900 border border-gray-700 p-3 text-xs text-gray-300 whitespace-pre-wrap overflow-auto max-h-60">
            {error.payload.email_body}
          </pre>
        </div>
      )}
    </div>
  )
}
