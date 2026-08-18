import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useRun } from '../context/RunContext'
import CandidateCard from '../components/CandidateCard'
import AmbientGlow from '../components/AmbientGlow'

const ResultsPage = () => {
  const { runId, results, fetchResults, exportToSheet, downloadCsv, downloadAllCvs, resetRun } = useRun()
  const navigate = useNavigate()

  useEffect(() => {
    if (!runId) {
      navigate('/', { replace: true })
      return
    }
    fetchResults()
  }, [runId, fetchResults, navigate])

  const startNewScreening = () => {
    resetRun()
    navigate('/')
  }

  return (
    <div className="bg-canvas text-ink min-h-screen flex flex-col antialiased">
      <header className="bg-background border-b border-hairline flex items-center gap-md px-lg w-full sticky top-0 z-50 h-14">
        <button
          onClick={startNewScreening}
          className="flex items-center gap-xs text-ink-subtle hover:text-ink hover:bg-surface-2 focus-ring rounded-md px-2 py-1 -ml-2 transition-colors"
          aria-label="Start a new screening"
        >
          <span className="material-symbols-outlined text-[18px]">arrow_back</span>
          <span className="text-[14px]">New screening</span>
        </button>
        <div className="h-5 w-px bg-hairline" />
        <span className="text-[20px] tracking-[-0.5px] font-semibold text-ink">CV Screener</span>
      </header>

      <AmbientGlow />

      <main className="flex-1 overflow-y-auto p-md md:p-xl lg:p-section relative z-10">
        <header className="flex flex-col md:flex-row md:items-end justify-between gap-lg mb-xl pb-lg border-b border-hairline">
          <div>
            <h1 className="text-display-md text-ink mb-xs">
              Screening Results
            </h1>
            <p className="text-body-lg text-ink-subtle">
              {results.length} shortlisted candidate{results.length === 1 ? '' : 's'}
            </p>
          </div>
          <div className="flex items-center gap-sm">
            <button
              onClick={downloadCsv}
              disabled={results.length === 0}
              className="flex items-center gap-xs px-md py-1.5 rounded-md border border-hairline bg-surface-1 text-ink text-[14px] hover:bg-surface-2 hover:border-hairline-strong active:bg-surface-3 focus-ring transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
            >
              <span className="material-symbols-outlined text-[16px]">description</span>
              CSV
            </button>
            <button
              onClick={downloadAllCvs}
              disabled={results.length === 0}
              className="flex items-center gap-xs px-md py-1.5 rounded-md border border-hairline bg-surface-1 text-ink text-[14px] hover:bg-surface-2 hover:border-hairline-strong active:bg-surface-3 focus-ring transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
            >
              <span className="material-symbols-outlined text-[16px]">folder_zip</span>
              Download all CVs
            </button>
            <button
              onClick={exportToSheet}
              disabled={results.length === 0}
              className="flex items-center gap-xs px-md py-1.5 rounded-md border border-hairline bg-surface-1 text-ink text-[14px] hover:bg-surface-2 hover:border-hairline-strong active:bg-surface-3 focus-ring transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
            >
              <span className="material-symbols-outlined text-[16px]">table_view</span>
              Export to Google Sheet
            </button>
          </div>
        </header>

        {results.length === 0 ? (
          <p className="text-body text-ink-subtle text-center py-section">No candidates yet.</p>
        ) : (
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-lg">
            {results.map((candidate) => (
              <CandidateCard
                key={candidate.candidate_email ?? candidate.candidate_name}
                candidate={candidate}
              />
            ))}
          </div>
        )}
      </main>
    </div>
  )
}

export default ResultsPage
