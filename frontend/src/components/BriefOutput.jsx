/**
 * BriefOutput — Two paragraphs with clear labels.
 * "Pain Points & Growth Context" and "Strategic Alignment"
 * Zero business logic — purely presentational.
 */
export default function BriefOutput({ brief }) {
  if (!brief) return null

  // Split the brief into paragraphs (separated by double newline)
  const paragraphs = brief.split(/\n\n+/).filter(p => p.trim())
  const paragraph1 = paragraphs[0] || ''
  const paragraph2 = paragraphs[1] || ''

  return (
    <div className="space-y-4">
      <h3 className="text-sm font-semibold uppercase tracking-wider text-gray-400">Account Brief</h3>

      {/* Paragraph 1 — Pain Points & Growth Context */}
      <div className="rounded-lg border border-blue-500/20 bg-blue-500/5 p-4">
        <p className="text-xs font-semibold text-blue-400 uppercase tracking-wider mb-2">
          Pain Points & Growth Context
        </p>
        <p className="text-sm text-gray-300 leading-relaxed">{paragraph1}</p>
      </div>

      {/* Paragraph 2 — Strategic Alignment */}
      {paragraph2 && (
        <div className="rounded-lg border border-purple-500/20 bg-purple-500/5 p-4">
          <p className="text-xs font-semibold text-purple-400 uppercase tracking-wider mb-2">
            Strategic Alignment
          </p>
          <p className="text-sm text-gray-300 leading-relaxed">{paragraph2}</p>
        </div>
      )}
    </div>
  )
}
