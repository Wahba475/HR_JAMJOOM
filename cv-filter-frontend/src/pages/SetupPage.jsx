import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useRun } from '../context/RunContext'
import UploadDropzone from '../components/UploadDropzone'
import AmbientGlow from '../components/AmbientGlow'

const inputClass =
  'bg-surface-1 border border-hairline rounded-md text-ink placeholder:text-ink-tertiary hover:border-hairline-strong focus-ring text-body py-xs px-sm transition-colors'

const SetupPage = () => {
  const [title, setTitle] = useState('')
  const [jobDescription, setJobDescription] = useState('')
  const [criteria, setCriteria] = useState('')
  const [targetCount, setTargetCount] = useState(5)
  const [files, setFiles] = useState([])
  const [submitting, setSubmitting] = useState(false)

  const { createRun, uploadCvs, startRun } = useRun()
  const navigate = useNavigate()

  const canSubmit = !submitting && files.length > 0 && title.trim() && jobDescription.trim()

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!canSubmit) return

    try {
      setSubmitting(true)
      await createRun({ title, jobDescription, criteria, targetCount: Number(targetCount) })
      await uploadCvs(files)
      await startRun()
      navigate('/progress')
    } catch {
      // errors already surfaced via toast in RunContext
      setSubmitting(false)
    }
  }

  return (
    <div className="bg-canvas text-ink antialiased flex flex-col min-h-screen selection:bg-primary-container selection:text-white">
      <header className="flex items-center px-lg w-full sticky top-0 z-50 h-16 bg-canvas border-b border-hairline">
        <span className="text-headline text-ink">CV Screener</span>
      </header>

      <AmbientGlow />

      <main className="grow flex justify-center py-xl px-md relative z-10">
        <div className="w-full max-w-150 flex flex-col gap-md">
          <div className="flex flex-col gap-xs text-center md:text-left">
            <h1 className="text-display-md text-ink">
              Screen candidates for a role
            </h1>
            <p className="text-body-lg text-ink-subtle">
              Define the criteria and upload resumes to begin the automated screening process.
            </p>
          </div>

          <form onSubmit={handleSubmit} className="flex flex-col gap-md w-full">
            <div className="flex flex-col gap-xs">
              <label className="text-eyebrow text-ink-subtle uppercase tracking-wider" htmlFor="job-title">
                Job title
              </label>
              <input
                id="job-title"
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="e.g. Senior Product Designer"
                className={inputClass}
              />
            </div>

            <div className="flex flex-col gap-xs">
              <label
                className="text-eyebrow text-ink-subtle uppercase tracking-wider"
                htmlFor="job-description"
              >
                Job description
              </label>
              <textarea
                id="job-description"
                rows="3"
                value={jobDescription}
                onChange={(e) => setJobDescription(e.target.value)}
                placeholder="Paste the full job description here..."
                className={`${inputClass} resize-y`}
              />
            </div>

            <div className="flex flex-col gap-xs">
              <label
                className="text-eyebrow text-ink-subtle uppercase tracking-wider"
                htmlFor="hiring-criteria"
              >
                Hiring criteria <span className="text-ink-tertiary font-normal">(Optional)</span>
              </label>
              <textarea
                id="hiring-criteria"
                rows="2"
                value={criteria}
                onChange={(e) => setCriteria(e.target.value)}
                placeholder="Specific skills, years of experience, or required certifications..."
                className={`${inputClass} resize-y`}
              />
            </div>

            <div className="flex flex-col gap-xs">
              <label
                className="text-eyebrow text-ink-subtle uppercase tracking-wider"
                htmlFor="shortlist-size"
              >
                Target Shortlist Size
              </label>
              <input
                id="shortlist-size"
                type="number"
                min="1"
                value={targetCount}
                onChange={(e) => setTargetCount(e.target.value)}
                className={`${inputClass} w-32`}
              />
            </div>

            <UploadDropzone files={files} onFilesChange={setFiles} />

            <div className="pt-md border-t border-hairline flex justify-end gap-sm mt-xs">
              <button
                type="button"
                onClick={() => {
                  setTitle('')
                  setJobDescription('')
                  setCriteria('')
                  setTargetCount(5)
                  setFiles([])
                }}
                className="text-button bg-surface-1 border border-hairline text-ink hover:bg-surface-2 hover:border-hairline-strong active:bg-surface-3 focus-ring rounded-md py-xs px-3.5 transition-colors"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={!canSubmit}
                className="text-button bg-primary-container text-white hover:bg-primary-hover active:bg-primary-focus focus-ring rounded-md py-xs px-3.5 transition-colors flex items-center gap-xs disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:bg-primary-container"
              >
                <span
                  className="material-symbols-outlined text-sm"
                  style={{ fontVariationSettings: "'FILL' 1" }}
                >
                  play_arrow
                </span>
                {submitting ? 'Starting...' : 'Run Screening'}
              </button>
            </div>
          </form>
        </div>
      </main>
    </div>
  )
}

export default SetupPage
