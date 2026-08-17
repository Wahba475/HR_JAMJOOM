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

export const RunProvider = ({ children }) => {
  const [runId, setRunId] = useState(null)
  const [status, setStatus] = useState(null)
  const [totalCvs, setTotalCvs] = useState(0)
  const [processedCvs, setProcessedCvs] = useState(0)
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  // Mirrors runId synchronously so calls made right after createRun (before
  // the next render) still target the right run instead of a stale closure.
  const runIdRef = useRef(null)

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
  }, [])

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
      return response.data
    } catch (err) {
      console.error('Error polling run status:', err)
      const errorMessage = err.response?.data?.message || err.message || 'Failed to fetch run status'
      setError(errorMessage)
      toast.error(errorMessage)
      throw err
    }
  }, [])

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

  const exportToSheet = useCallback(async () => {
    try {
      const url = `${import.meta.env.VITE_API_URL}/runs/${runIdRef.current}/export`
      const response = await axios.post(url, null, { responseType: 'blob' })
      saveBlob(response.data, `shortlist_${runIdRef.current.slice(0, 8)}.csv`)
      toast.success('Shortlist downloaded — open it in Google Sheets')
    } catch (err) {
      console.error('Error exporting to sheet:', err)
      const errorMessage = err.response?.data?.message || err.message || 'Failed to export'
      toast.error(errorMessage)
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
    downloadAllCvs,
  }

  return <RunContext.Provider value={value}>{children}</RunContext.Provider>
}
