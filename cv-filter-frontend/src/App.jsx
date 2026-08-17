import { Routes, Route } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import { RunProvider } from './context/RunContext'
import SetupPage from './pages/SetupPage'
import ProgressPage from './pages/ProgressPage'
import ResultsPage from './pages/ResultsPage'

function App() {
  return (
    <RunProvider>
      <Routes>
        <Route path="/" element={<SetupPage />} />
        <Route path="/progress" element={<ProgressPage />} />
        <Route path="/results" element={<ResultsPage />} />
      </Routes>
      <Toaster
        position="top-right"
        toastOptions={{
          duration: 3000,
          style: {
            background: '#0f1011',
            color: '#e4e1eb',
            border: '1px solid #23252a',
            fontFamily: "'Inter var', 'Inter', sans-serif",
            fontSize: '14px',
            borderRadius: '8px',
            padding: '12px 16px',
          },
          success: {
            iconTheme: { primary: '#5e6ad2', secondary: '#fff' },
          },
          error: {
            iconTheme: { primary: '#ffb4ab', secondary: '#0f1011' },
          },
        }}
      />
    </RunProvider>
  )
}

export default App
