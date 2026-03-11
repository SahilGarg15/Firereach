/**
 * SignalOutput — Display all 11 SignalPayload fields.
 * Fields with data: colored card with signal text.
 * Fields that are None: muted "Not available" card with tooltip.
 * Zero business logic — purely presentational.
 */
export default function SignalOutput({ signals }) {
  if (!signals) return null

  const fetchableFields = [
    { key: 'funding', label: 'Funding Rounds', icon: '💰' },
    { key: 'leadership', label: 'Leadership Changes', icon: '👤' },
    { key: 'hiring', label: 'Hiring Trends', icon: '📋' },
    { key: 'social_mentions', label: 'Social Mentions', icon: '📣' },
    { key: 'tech_stack', label: 'Tech Stack Changes', icon: '🔧' },
    { key: 'keyword_intent', label: 'Keyword Search Intent', icon: '🔍' },
    { key: 'news', label: 'News & Announcements', icon: '📰' },
  ]

  const paidFields = [
    { key: 'website_visits', label: 'Website Visits', icon: '🌐', provider: 'Requires paid data provider (e.g. 6sense, Bombora). See DOCS.md.' },
    { key: 'g2_surges', label: 'G2 Category Surges', icon: '📊', provider: 'Requires paid data provider (e.g. G2 Buyer Intent API). See DOCS.md.' },
    { key: 'competitor_churn', label: 'Competitor Tool Churn', icon: '🔄', provider: 'Requires paid data provider (e.g. G2, Klue). See DOCS.md.' },
    { key: 'product_usage', label: 'Product Usage Signals', icon: '📈', provider: 'Requires paid data provider (e.g. Pendo, Amplitude). See DOCS.md.' },
  ]

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <h3 className="text-sm font-semibold uppercase tracking-wider text-gray-400">Harvested Signals</h3>
        <span className="rounded-full bg-orange-500/20 px-2.5 py-0.5 text-xs font-medium text-orange-400">
          {signals.signal_count} signals found
        </span>
      </div>

      {/* Fetchable signals */}
      <div className="grid gap-2">
        {fetchableFields.map(({ key, label, icon }) => {
          const value = signals[key]
          if (value) {
            return (
              <div key={key} className="rounded-lg border border-gray-700/50 bg-gray-800/50 p-3">
                <div className="flex items-start gap-2">
                  <span className="text-base flex-shrink-0 mt-0.5">{icon}</span>
                  <div className="min-w-0">
                    <p className="text-xs font-medium text-gray-400 mb-1">{label}</p>
                    <p className="text-sm text-gray-200">{value}</p>
                  </div>
                </div>
              </div>
            )
          }
          return (
            <div key={key} className="rounded-lg border border-gray-800/50 bg-gray-900/30 p-3 opacity-50">
              <div className="flex items-center gap-2">
                <span className="text-base">{icon}</span>
                <p className="text-xs text-gray-500">{label} — No data found</p>
              </div>
            </div>
          )
        })}
      </div>

      {/* Paid-provider signals (always None) */}
      <div className="grid gap-2">
        {paidFields.map(({ key, label, icon, provider }) => (
          <div key={key} className="group relative rounded-lg border border-gray-800/30 bg-gray-900/20 p-3 opacity-40">
            <div className="flex items-center gap-2">
              <span className="text-base">{icon}</span>
              <p className="text-xs text-gray-500">{label} — Not available</p>
            </div>
            {/* Tooltip */}
            <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 hidden group-hover:block z-10">
              <div className="rounded-lg bg-gray-800 border border-gray-700 px-3 py-2 text-xs text-gray-300 shadow-lg whitespace-nowrap">
                {provider}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Source URLs */}
      {signals.source_urls && signals.source_urls.length > 0 && (
        <div className="mt-2">
          <p className="text-xs font-medium text-gray-500 mb-1">Sources</p>
          <div className="flex flex-wrap gap-2">
            {signals.source_urls.map((url, idx) => (
              <a
                key={idx}
                href={url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-orange-400/70 hover:text-orange-400 underline underline-offset-2 truncate max-w-[250px]"
              >
                {url}
              </a>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
