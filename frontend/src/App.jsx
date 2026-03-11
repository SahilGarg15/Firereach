import { useState, useCallback } from 'react'
import InputForm from './components/InputForm.jsx'
import StatusPanel from './components/StatusPanel.jsx'
import SignalOutput from './components/SignalOutput.jsx'
import BriefOutput from './components/BriefOutput.jsx'
import EmailOutput from './components/EmailOutput.jsx'
import ErrorBanner from './components/ErrorBanner.jsx'

/**
 * App.jsx — Global state: { phase, runId, runData, steps }
 * Four phases: idle → running → [review] → done / error
 * Zero business logic. Thin SSE client.
 */

const API_BASE = import.meta.env.VITE_API_BASE || ''  // Vite proxy in dev, env var in prod

export default function App() {
  const [phase, setPhase] = useState('idle')       // idle | running | review | done | error
  const [runId, setRunId] = useState(null)
  const [steps, setSteps] = useState([{}, {}, {}])  // 3 step objects
  const [signals, setSignals] = useState(null)
  const [brief, setBrief] = useState(null)
  const [emailData, setEmailData] = useState(null)
  const [reviewData, setReviewData] = useState(null)
  const [error, setError] = useState(null)
  const [duration, setDuration] = useState(null)
  const [recipient, setRecipient] = useState('')

  const resetState = () => {
    setPhase('idle')
    setRunId(null)
    setSteps([{}, {}, {}])
    setSignals(null)
    setBrief(null)
    setEmailData(null)
    setReviewData(null)
    setError(null)
    setDuration(null)
    setRecipient('')
  }

  const handleSubmit = useCallback(async (formData) => {
    resetState()
    setPhase('running')
    setRecipient(formData.recipient)

    try {
      // POST /api/v1/run
      const resp = await fetch(`${API_BASE}/api/v1/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData),
      })

      if (!resp.ok) {
        const errData = await resp.json()
        setError({ code: errData.code || 'VALIDATION_ERROR', message: errData.message || 'Request failed.' })
        setPhase('error')
        return
      }

      const { run_id, stream_url } = await resp.json()
      setRunId(run_id)

      // Open SSE stream
      const eventSource = new EventSource(`${API_BASE}${stream_url}`)

      eventSource.addEventListener('step_update', (e) => {
        const data = JSON.parse(e.data)
        setSteps(prev => {
          const next = [...prev]
          next[data.step - 1] = { ...next[data.step - 1], status: 'running', label: data.label }
          return next
        })
      })

      eventSource.addEventListener('step_complete', (e) => {
        const data = JSON.parse(e.data)
        const stepIdx = data.step - 1

        setSteps(prev => {
          const next = [...prev]
          next[stepIdx] = { status: data.status, payload: data.payload }
          return next
        })

        // Update output data based on step
        if (data.step === 1) {
          setSignals(data.payload)
        } else if (data.step === 2) {
          setBrief(data.payload.brief)
        } else if (data.step === 3) {
          setEmailData(data.payload)
        }
      })

      eventSource.addEventListener('review_required', (e) => {
        const data = JSON.parse(e.data)
        setReviewData({ ...data, recipient: formData.recipient })
        setSteps(prev => {
          const next = [...prev]
          next[2] = { status: 'review', payload: { score: data.score } }
          return next
        })
        setPhase('review')
      })

      eventSource.addEventListener('error', (e) => {
        try {
          const data = JSON.parse(e.data)
          setError(data)
          if (data.step > 0) {
            setSteps(prev => {
              const next = [...prev]
              next[data.step - 1] = { status: 'error' }
              return next
            })
          }
          setPhase('error')
        } catch {
          // SSE connection error (not a JSON event)
          setError({ code: 'LLM_API_ERROR', message: 'Connection lost. Please retry.' })
          setPhase('error')
        }
      })

      eventSource.addEventListener('done', (e) => {
        const data = JSON.parse(e.data)
        setDuration(data.total_duration_ms)
        eventSource.close()
        // Only set done if not already in review or error
        setPhase(prev => (prev === 'review' || prev === 'error') ? prev : 'done')
      })

      // Handle unexpected SSE close
      eventSource.onerror = () => {
        // EventSource will auto-reconnect, but if the stream is done this fires
        // Only set error if we haven't received a done event
        setTimeout(() => {
          eventSource.close()
        }, 2000)
      }

    } catch (err) {
      setError({ code: 'VALIDATION_ERROR', message: 'Network error. Please check your connection.' })
      setPhase('error')
    }
  }, [])

  const handleConfirmSent = useCallback((sentData) => {
    setEmailData(sentData)
    setReviewData(null)
    setSteps(prev => {
      const next = [...prev]
      next[2] = { status: 'sent', payload: sentData }
      return next
    })
    setPhase('done')
  }, [])

  const isRunning = phase === 'running'

  return (
    <div className="min-h-screen bg-gray-950">
      {/* Header */}
      <header className="border-b border-gray-800/50 bg-gray-950/80 backdrop-blur-sm sticky top-0 z-20">
        <div className="mx-auto max-w-5xl px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-2xl">🔥</span>
            <div>
              <h1 className="text-lg font-bold text-gray-100">FireReach</h1>
              <p className="text-xs text-gray-500">Autonomous B2B Outreach Engine</p>
            </div>
          </div>
          {phase !== 'idle' && (
            <button
              onClick={resetState}
              className="rounded-lg border border-gray-700 px-4 py-1.5 text-xs text-gray-400 hover:text-gray-200 hover:border-gray-600 transition-colors"
            >
              New Run
            </button>
          )}
        </div>
      </header>

      {/* Main Content */}
      <main className="mx-auto max-w-5xl px-6 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Left Column — Input + Status */}
          <div className="lg:col-span-1 space-y-6">
            <div className="rounded-xl border border-gray-800/50 bg-gray-900/50 p-5">
              <h2 className="text-sm font-semibold uppercase tracking-wider text-gray-400 mb-4">Configuration</h2>
              <InputForm onSubmit={handleSubmit} disabled={isRunning} />
            </div>

            {phase !== 'idle' && (
              <div className="rounded-xl border border-gray-800/50 bg-gray-900/50 p-5">
                <StatusPanel steps={steps} />
                {duration != null && (
                  <p className="mt-3 text-xs text-gray-500 text-right">
                    Completed in {(duration / 1000).toFixed(1)}s
                  </p>
                )}
              </div>
            )}
          </div>

          {/* Right Column — Output */}
          <div className="lg:col-span-2 space-y-6">
            {/* Error Banner */}
            {error && <ErrorBanner error={error} />}

            {/* Signals */}
            {signals && (
              <div className="rounded-xl border border-gray-800/50 bg-gray-900/50 p-5">
                <SignalOutput signals={signals} />
              </div>
            )}

            {/* Brief */}
            {brief && (
              <div className="rounded-xl border border-gray-800/50 bg-gray-900/50 p-5">
                <BriefOutput brief={brief} />
              </div>
            )}

            {/* Email — auto-sent or review-required */}
            {(emailData || reviewData) && (
              <div className="rounded-xl border border-gray-800/50 bg-gray-900/50 p-5">
                <EmailOutput
                  emailData={emailData}
                  reviewData={reviewData}
                  runId={runId}
                  onConfirmSent={handleConfirmSent}
                />
              </div>
            )}

            {/* Idle state */}
            {phase === 'idle' && (
              <div className="flex items-center justify-center min-h-[300px] rounded-xl border border-dashed border-gray-800/50 bg-gray-900/20">
                <div className="text-center space-y-2">
                  <span className="text-4xl">🔥</span>
                  <p className="text-sm text-gray-500">Configure your ICP and target company to begin</p>
                </div>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  )
}
