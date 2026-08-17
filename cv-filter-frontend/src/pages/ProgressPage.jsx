import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useRun } from '../context/RunContext'
import ProgressBar from '../components/ProgressBar'
import AmbientGlow from '../components/AmbientGlow'

const POLL_INTERVAL_MS = 1500

const ProgressPage = () => {
  const { status, totalCvs, processedCvs, pollStatus } = useRun()
  const navigate = useNavigate()

  useEffect(() => {
    const interval = setInterval(() => {
      pollStatus()
    }, POLL_INTERVAL_MS)

    return () => clearInterval(interval)
  }, [pollStatus])

  useEffect(() => {
    if (status === 'completed') {
      navigate('/results')
    }
  }, [status, navigate])

  return (
    <div className="min-h-screen flex flex-col items-center justify-center relative overflow-hidden bg-canvas">
      <header className="absolute top-0 left-0 w-full flex items-center px-lg py-md z-50">
        <span className="text-headline text-ink">CV Screener</span>
      </header>

      <AmbientGlow variant="focus" />

      <main className="flex-1 w-full flex flex-col items-center justify-center p-md z-10 relative">
        <ProgressBar processedCvs={processedCvs} totalCvs={totalCvs} />
      </main>
    </div>
  )
}

export default ProgressPage
