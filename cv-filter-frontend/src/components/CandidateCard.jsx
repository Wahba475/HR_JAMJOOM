const initials = (name) =>
  (name || '?')
    .replace(/^(Dr|Mr|Mrs|Ms|Eng)\.?\s+/i, '')
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0])
    .join('')
    .toUpperCase()

const CandidateCard = ({ candidate }) => {
  const { candidate_name, candidate_email, score, rationale, cv_url } = candidate
  const isStrong = score > 80

  return (
    <article className="bg-surface-1 border border-hairline rounded-lg p-lg flex flex-col gap-md hover:bg-surface-2 hover:border-hairline-strong transition-colors group">
      <div className="flex justify-between items-start">
        <div className="flex items-center gap-md">
          {/* Initials stand in for the design's avatar photo — the pipeline
              extracts a name and email from each CV, never a portrait. */}
          <div className="w-10 h-10 rounded-full border border-hairline bg-surface-2 flex items-center justify-center shrink-0">
            <span className="text-caption text-ink-muted font-medium">{initials(candidate_name)}</span>
          </div>
          <div>
            <h2 className="text-[18px] tracking-[-0.4px] font-semibold text-ink">
              {candidate_name || 'Unnamed candidate'}
            </h2>
            <p className="text-[13px] text-ink-subtle mt-0.5">{candidate_email || '—'}</p>
          </div>
        </div>

        <div
          className={`border px-2 py-0.5 rounded-full flex items-center gap-1 shrink-0 ${
            isStrong
              ? 'border-primary-container/40 bg-primary-container/10 text-primary'
              : 'border-hairline bg-surface-2 text-ink-subtle'
          }`}
        >
          <span className="text-[12px] font-medium">{Math.round(score)}% Match</span>
          {isStrong && <span className="material-symbols-outlined text-[14px]">check_circle</span>}
        </div>
      </div>

      <div className="bg-surface-2 rounded-md p-md border border-hairline my-sm">
        <h3 className="text-[11px] font-medium text-ink-subtle mb-2 uppercase tracking-widest">
          AI Rationale
        </h3>
        <p className="text-[14px] text-ink-muted leading-relaxed">{rationale}</p>
      </div>

      <div className="flex gap-sm mt-auto pt-sm">
        <button
          onClick={() => window.open(cv_url, '_blank', 'noopener,noreferrer')}
          className="flex-1 bg-surface-2 text-ink text-[13px] py-1.5 rounded-md border border-hairline hover:bg-surface-3 hover:border-hairline-strong active:bg-surface-4 focus-ring transition-colors flex items-center justify-center gap-2"
        >
          <span className="material-symbols-outlined text-[16px]">visibility</span>
          View CV
        </button>
        <a
          href={cv_url}
          download
          target="_blank"
          rel="noopener noreferrer"
          className="flex-1 bg-surface-1 border border-hairline text-ink text-[13px] py-1.5 rounded-md hover:bg-surface-2 hover:border-hairline-strong active:bg-surface-3 focus-ring transition-colors flex items-center justify-center gap-2"
        >
          <span className="material-symbols-outlined text-[16px]">download</span>
          Download
        </a>
      </div>
    </article>
  )
}

export default CandidateCard
