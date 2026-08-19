import axios from 'axios'

/**
 * Shared axios instance for the backend API.
 *
 * The ngrok header is the reason this exists as a shared instance rather
 * than per-call config. ngrok's free tier serves an HTML interstitial
 * ("you are about to visit...") to anything whose User-Agent looks like a
 * browser. That page carries no CORS headers, so the browser reports a CORS
 * failure even though the backend's CORS config is correct — the request
 * never reaches the backend at all. curl is unaffected, which is what makes
 * the symptom so misleading.
 *
 * Sending ngrok-skip-browser-warning on every request bypasses it.
 */
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL,
  headers: {
    'ngrok-skip-browser-warning': 'true',
  },
})

export default api
