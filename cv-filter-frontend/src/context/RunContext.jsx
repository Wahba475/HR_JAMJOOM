import { createContext, useContext, useState, useCallback, useRef } from 'react'
import axios from 'axios'
import toast from 'react-hot-toast'

const RunContext = createContext()

export const useRun = () => {
  const context = useContext(RunContext)
  if (!context) {
    throw new Error('useRun must be used within a RunProvider')
  }
  return context
}

// A run lives entirely in memory otherwise, so a refresh wiped runId and
// every request went to /runs/null. Only the id and a small snapshot are
// persisted — the actual data is re-fetched from the API, so a reloaded
// tab can never show stale scores.
const STORAGE_KEY = 'cv-screener:run'

const loadPersisted = () => {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY)) || {}
  } catch {
    return {}
  }
}

export const RunProvider = ({ children }) => {
  const persisted = loadPersisted()

  const [runId, setRunId] = useState(persisted.runId ?? null)
  const [status, setStatus] = useState(persisted.status ?? null)
  const [totalCvs, setTotalCvs] = useState(persisted.totalCvs ?? 0)
  const [processedCvs, setProcessedCvs] = useState(persisted.processedCvs ?? 0)
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  // Mirrors runId synchronously so calls made right after createRun (before
  // the next render) still target the right run instead of a stale closure.
  // Seeded from storage so the very first request after a refresh is valid.
  const runIdRef = useRef(persisted.runId ?? null)

  const persist = useCallback((patch) => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({ ...loadPersisted(), ...patch }))
    } catch {
      // Private browsing or a full quota — the app still works for this
      // session, it just won't survive a reload.
    }
  }, [])

  const resetRun = useCallback(() => {
    localStorage.removeItem(STORAGE_KEY)
    runIdRef.current = null
    setRunId(null)
    setStatus(null)
    setTotalCvs(0)
    setProcessedCvs(0)
    setResults([])
    setError(null)
  }, [])

  const createRun = useCallback(async ({ title, jobDescription, criteria, targetCount }) => {
    try {
      setLoading(true)
      setError(null)

      const url = `${import.meta.env.VITE_API_URL}/runs`
      const response = await axios.post(url, {
        title,
        job_description: jobDescription,
        criteria,
        target_count: targetCount,
      })

      const id = response.data.run_id
      runIdRef.current = id
      setRunId(id)
      persist({ runId: id, status: 'pending', totalCvs: 0, processedCvs: 0 })
      return id
    } catch (err) {
      console.error('Error creating run:', err)
      const errorMessage = err.response?.data?.message || err.message || 'Failed to create run'
      setError(errorMessage)
      toast.error(errorMessage)
      throw err
    } finally {
      setLoading(false)
    }
  }, [persist])

  const uploadCvs = useCallback(async (files) => {
    try {
      setLoading(true)
      setError(null)

      const formData = new FormData()
      for (const file of files) {
        formData.append('files', file)
      }

      const url = `${import.meta.env.VITE_API_URL}/runs/${runIdRef.current}/cvs`
      const response = await axios.post(url, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })

      return response.data.uploaded
    } catch (err) {
      console.error('Error uploading CVs:', err)
      const errorMessage = err.response?.data?.message || err.message || 'Failed to upload CVs'
      setError(errorMessage)
      toast.error(errorMessage)
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  const startRun = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)

      const url = `${import.meta.env.VITE_API_URL}/runs/${runIdRef.current}/start`
      await axios.post(url)
    } catch (err) {
      console.error('Error starting run:', err)
      const errorMessage = err.response?.data?.message || err.message || 'Failed to start run'
      setError(errorMessage)
      toast.error(errorMessage)
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  const pollStatus = useCallback(async () => {
    try {
      const url = `${import.meta.env.VITE_API_URL}/runs/${runIdRef.current}`
      const response = await axios.get(url)

      setStatus(response.data.status)
      setTotalCvs(response.data.total_cvs)
      setProcessedCvs(response.data.processed_cvs)
      persist({
        status: response.data.status,
        totalCvs: response.data.total_cvs,
        processedCvs: response.data.processed_cvs,
      })
      return response.data
    } catch (err) {
      console.error('Error polling run status:', err)
      const errorMessage = err.response?.data?.message || err.message || 'Failed to fetch run status'
      setError(errorMessage)
      toast.error(errorMessage)
      throw err
    }
  }, [persist])

  const fetchResults = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)

      const url = `${import.meta.env.VITE_API_URL}/runs/${runIdRef.current}/results`
      const response = await axios.get(url)

      setResults(Array.isArray(response.data) ? response.data : [])
    } catch (err) {
      console.error('Error fetching results:', err)
      const errorMessage = err.response?.data?.message || err.message || 'Failed to load results'
      setError(errorMessage)
      toast.error(errorMessage)
      setResults([])
    } finally {
      setLoading(false)
    }
  }, [])

  // Both exports stream a file back, so they go through a blob URL rather
  // than a plain link: the request has to hit the API base, not the SPA origin.
  const saveBlob = (data, filename) => {
    const href = URL.createObjectURL(data)
    const link = document.createElement('a')
    link.href = href
    link.download = filename
    document.body.appendChild(link)
    link.click()
    link.remove()
    URL.revokeObjectURL(href)
  }

  // Creates a real Google Sheet server-side and opens it. The window is
  // opened synchronously before awaiting, because a popup triggered after
  // an await has lost the user-gesture context and gets blocked.
  const exportToSheet = useCallback(async () => {
    const tab = window.open('', '_blank')
    const toastId = toast.loading('Building your Google Sheet…')
    try {
      const url = `${import.meta.env.VITE_API_URL}/runs/${runIdRef.current}/sheet`
      const response = await axios.post(url)
      const sheetUrl = response.data.sheet_url
      if (tab) tab.location = sheetUrl
      else window.open(sheetUrl, '_blank', 'noopener,noreferrer')
      toast.success('Google Sheet created', { id: toastId })
      return sheetUrl
    } catch (err) {
      if (tab) tab.close()
      console.error('Error exporting to sheet:', err)
      const errorMessage =
        err.response?.data?.detail || err.response?.data?.message || err.message || 'Failed to export'
      toast.error(errorMessage, { id: toastId })
    }
  }, [])

  const downloadCsv = useCallback(async () => {
    try {
      const url = `${import.meta.env.VITE_API_URL}/runs/${runIdRef.current}/export`
      const response = await axios.post(url, null, { responseType: 'blob' })
      saveBlob(response.data, `shortlist_${runIdRef.current.slice(0, 8)}.csv`)
      toast.success('CSV downloaded')
    } catch (err) {
      console.error('Error downloading CSV:', err)
      toast.error(err.response?.data?.message || err.message || 'Failed to download CSV')
    }
  }, [])

  const downloadAllCvs = useCallback(async () => {
    try {
      const url = `${import.meta.env.VITE_API_URL}/runs/${runIdRef.current}/cvs/download`
      const response = await axios.get(url, { responseType: 'blob' })
      saveBlob(response.data, `cvs_${runIdRef.current.slice(0, 8)}.zip`)
      toast.success('CVs downloaded')
    } catch (err) {
      console.error('Error downloading CVs:', err)
      const errorMessage = err.response?.data?.message || err.message || 'Failed to download CVs'
      toast.error(errorMessage)
    }
  }, [])

  const value = {
    runId,
    status,
    totalCvs,
    processedCvs,
    results,
    loading,
    error,
    createRun,
    uploadCvs,
    startRun,
    pollStatus,
    fetchResults,
    exportToSheet,
    downloadCsv,
    downloadAllCvs,
    resetRun,
  }

  return <RunContext.Provider value={value}>{children}</RunContext.Provider>
}
