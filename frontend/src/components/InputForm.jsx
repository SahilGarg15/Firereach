import { useState } from 'react'

/**
 * InputForm — ICP, Company Name, Recipient Email.
 * All required. Email validated client-side. Disabled while running.
 * Zero business logic — just collects input and calls onSubmit.
 */
export default function InputForm({ onSubmit, disabled }) {
  const [icp, setIcp] = useState('')
  const [companyName, setCompanyName] = useState('')
  const [recipient, setRecipient] = useState('')
  const [errors, setErrors] = useState({})

  const validate = () => {
    const newErrors = {}
    if (!icp || icp.trim().length < 10) {
      newErrors.icp = 'ICP must be at least 10 characters.'
    }
    if (icp.length > 500) {
      newErrors.icp = 'ICP must be 500 characters or fewer.'
    }
    if (!companyName || companyName.trim().length < 2) {
      newErrors.companyName = 'Company name must be at least 2 characters.'
    }
    if (companyName.length > 100) {
      newErrors.companyName = 'Company name must be 100 characters or fewer.'
    }
    // Client-side email validation (PRD Flow D)
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
    if (!recipient || !emailRegex.test(recipient)) {
      newErrors.recipient = 'Please enter a valid email address.'
    }
    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!validate()) return
    onSubmit({ icp: icp.trim(), company_name: companyName.trim(), recipient: recipient.trim() })
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      {/* ICP */}
      <div>
        <label htmlFor="icp" className="block text-sm font-medium text-gray-300 mb-1.5">
          Ideal Customer Profile (ICP)
        </label>
        <textarea
          id="icp"
          rows={3}
          value={icp}
          onChange={(e) => setIcp(e.target.value)}
          disabled={disabled}
          placeholder="e.g. We sell cybersecurity training to Series B startups."
          className={`w-full rounded-lg border bg-gray-900 px-4 py-3 text-sm text-gray-100 placeholder-gray-500 
            focus:outline-none focus:ring-2 focus:ring-orange-500/50 focus:border-orange-500 
            disabled:opacity-50 disabled:cursor-not-allowed transition-colors
            ${errors.icp ? 'border-red-500' : 'border-gray-700'}`}
        />
        {errors.icp && <p className="mt-1 text-xs text-red-400">{errors.icp}</p>}
      </div>

      {/* Company Name */}
      <div>
        <label htmlFor="companyName" className="block text-sm font-medium text-gray-300 mb-1.5">
          Target Company
        </label>
        <input
          id="companyName"
          type="text"
          value={companyName}
          onChange={(e) => setCompanyName(e.target.value)}
          disabled={disabled}
          placeholder="e.g. Acme Corp"
          className={`w-full rounded-lg border bg-gray-900 px-4 py-3 text-sm text-gray-100 placeholder-gray-500 
            focus:outline-none focus:ring-2 focus:ring-orange-500/50 focus:border-orange-500 
            disabled:opacity-50 disabled:cursor-not-allowed transition-colors
            ${errors.companyName ? 'border-red-500' : 'border-gray-700'}`}
        />
        {errors.companyName && <p className="mt-1 text-xs text-red-400">{errors.companyName}</p>}
      </div>

      {/* Recipient Email */}
      <div>
        <label htmlFor="recipient" className="block text-sm font-medium text-gray-300 mb-1.5">
          Recipient Email
        </label>
        <input
          id="recipient"
          type="email"
          value={recipient}
          onChange={(e) => setRecipient(e.target.value)}
          disabled={disabled}
          placeholder="e.g. contact@acmecorp.com"
          className={`w-full rounded-lg border bg-gray-900 px-4 py-3 text-sm text-gray-100 placeholder-gray-500 
            focus:outline-none focus:ring-2 focus:ring-orange-500/50 focus:border-orange-500 
            disabled:opacity-50 disabled:cursor-not-allowed transition-colors
            ${errors.recipient ? 'border-red-500' : 'border-gray-700'}`}
        />
        {errors.recipient && <p className="mt-1 text-xs text-red-400">{errors.recipient}</p>}
      </div>

      {/* Submit */}
      <button
        type="submit"
        disabled={disabled}
        className="w-full rounded-lg bg-orange-600 px-6 py-3 text-sm font-semibold text-white
          hover:bg-orange-500 focus:outline-none focus:ring-2 focus:ring-orange-500/50
          disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        {disabled ? 'Running...' : 'Launch Outreach'}
      </button>
    </form>
  )
}
