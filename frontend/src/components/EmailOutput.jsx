import { useState } from 'react'

const API_BASE = import.meta.env.VITE_API_BASE || ''

/**
 * EmailOutput — Two modes based on confidence gate outcome.
 * Auto-sent: Green score badge, subject, body, sent timestamp.
 * Review required: Yellow score badge, warning, preview, "Confirm Send" button.
 * Zero business logic — purely presentational + one confirm-send API call.
 */
export default function EmailOutput({ emailData, reviewData, runId, onConfirmSent }) {
  const [confirming, setConfirming] = useState(false)
  const [confirmError, setConfirmError] = useState(null)

  // ── Auto-sent mode ─────────────────────────────────────────────────────
  if (emailData && emailData.sent_at) {
    return (
      <div className="space-y-4">
        <div className="flex items-center gap-3">
          <h3 className="text-sm font-semibold uppercase tracking-wider text-gray-400">Outreach Email</h3>
          <span className="rounded-full bg-green-500/20 px-2.5 py-0.5 text-xs font-medium text-green-400">
            Grounding Score: {emailData.score}/100
          </span>
        </div>

        <div className="rounded-lg border border-green-500/20 bg-green-500/5 p-4 space-y-3">
          <div>
            <p className="text-xs font-medium text-gray-500 mb-1">Subject</p>
            <p className="text-sm font-medium text-gray-200">{emailData.subject}</p>
          </div>
          <div>
            <p className="text-xs font-medium text-gray-500 mb-1">Body</p>
            <p className="text-sm text-gray-300 whitespace-pre-wrap leading-relaxed">{emailData.body}</p>
          </div>
          <div className="flex items-center gap-4 pt-2 border-t border-green-500/10">
            <p className="text-xs text-green-400">
              Sent at {new Date(emailData.sent_at).toLocaleString()}
            </p>
            {emailData.message_id && (
              <p className="text-xs text-gray-500 truncate">ID: {emailData.message_id}</p>
            )}
          </div>
        </div>
      </div>
    )
  }

  // ── Review required mode ───────────────────────────────────────────────
  if (reviewData) {
    const handleConfirmSend = async () => {
      setConfirming(true)
      setConfirmError(null)
      try {
        const resp = await fetch(`${API_BASE}/api/v1/run/${runId}/confirm-send`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            email_subject: reviewData.subject,
            email_body: reviewData.body,
            recipient: reviewData.recipient || '',
          }),
        })
        if (!resp.ok) {
          const err = await resp.json()
          setConfirmError(err.message || 'Send failed.')
          return
        }
        const result = await resp.json()
        if (onConfirmSent) {
          onConfirmSent({
            subject: reviewData.subject,
            body: reviewData.body,
            score: reviewData.score,
            sent_at: result.sent_at,
            message_id: result.message_id,
          })
        }
      } catch (err) {
        setConfirmError('Network error. Please try again.')
      } finally {
        setConfirming(false)
      }
    }

    return (
      <div className="space-y-4">
        <div className="flex items-center gap-3">
          <h3 className="text-sm font-semibold uppercase tracking-wider text-gray-400">Outreach Email</h3>
          <span className="rounded-full bg-yellow-500/20 px-2.5 py-0.5 text-xs font-medium text-yellow-400">
            Grounding Score: {reviewData.score}/100 · Review Required
          </span>
        </div>

        <div className="rounded-lg border border-yellow-500/20 bg-yellow-500/5 p-4 space-y-3">
          <p className="text-xs text-yellow-400">
            The email's grounding score is below the auto-send threshold. Please review and confirm.
          </p>
          <div>
            <p className="text-xs font-medium text-gray-500 mb-1">Subject</p>
            <p className="text-sm font-medium text-gray-200">{reviewData.subject}</p>
          </div>
          <div>
            <p className="text-xs font-medium text-gray-500 mb-1">Body</p>
            <p className="text-sm text-gray-300 whitespace-pre-wrap leading-relaxed">{reviewData.body}</p>
          </div>

          {confirmError && (
            <p className="text-xs text-red-400">{confirmError}</p>
          )}

          <button
            onClick={handleConfirmSend}
            disabled={confirming}
            className="rounded-lg bg-yellow-600 px-5 py-2 text-sm font-semibold text-white
              hover:bg-yellow-500 focus:outline-none focus:ring-2 focus:ring-yellow-500/50
              disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {confirming ? 'Sending...' : 'Confirm Send'}
          </button>
        </div>
      </div>
    )
  }

  return null
}
