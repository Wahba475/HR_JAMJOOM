const RADIUS = 54
const CIRCUMFERENCE = 2 * Math.PI * RADIUS // ~339.292

const ProgressBar = ({ processedCvs, totalCvs }) => {
  const percent = totalCvs > 0 ? Math.round((processedCvs / totalCvs) * 100) : 0
  const offset = CIRCUMFERENCE - (percent / 100) * CIRCUMFERENCE

  return (
    // Explicit px, not max-w-md: the --spacing-md theme token shadows Tailwind's
    // container scale, which would collapse max-w-md to 16px and wrap per-word.
    <div className="relative flex flex-col items-center w-full max-w-112">
      <div className="relative w-48 h-48 sm:w-64 sm:h-64 mb-xl">
        <div className="absolute inset-0 rounded-full border border-primary-container/20 pulse-layer" />
        <div
          className="absolute inset-2 rounded-full border border-primary-container/10 pulse-layer"
          style={{ animationDelay: '1s' }}
        />
        <svg className="w-full h-full" viewBox="0 0 120 120">
          <circle
            cx="60"
            cy="60"
            fill="none"
            r={RADIUS}
            stroke="var(--color-surface-container-high)"
            strokeWidth="4"
          />
          <circle
            className="progress-ring__circle" style={{ filter: percent > 0 ? "drop-shadow(0 0 6px rgb(94 106 210 / 0.7))" : "none" }}
            cx="60"
            cy="60"
            fill="none"
            r={RADIUS}
            stroke="var(--color-primary-container)"
            strokeDasharray={CIRCUMFERENCE}
            strokeDashoffset={offset}
            strokeLinecap="round"
            strokeWidth="4"
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center flex-col">
          <span className="text-display-md text-ink">{percent}%</span>
        </div>
      </div>

      {/* w-full is load-bearing: the flex column centers items, which would
          otherwise shrink this block to min-content and wrap one word per line. */}
      <div className="text-center w-full">
        <h1 className="text-display-md text-ink mb-sm">
          Processing {processedCvs} of {totalCvs} CVs
        </h1>
        <p className="text-body-lg text-ink-subtle">
          Reading each CV and comparing it against your criteria
        </p>
      </div>

      <div className="mt-xl flex items-center gap-2">
        <div className="w-2 h-2 rounded-full bg-primary-container animate-ping" />
        <span className="font-mono text-mono text-ink-tertiary uppercase tracking-widest">
          Analyzing Data
        </span>
      </div>
    </div>
  )
}

export default ProgressBar
