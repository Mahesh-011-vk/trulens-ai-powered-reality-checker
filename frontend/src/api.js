/**
 * TruthLens — Centralized API Client
 * All backend communication goes through this module.
 * Base URL is read from VITE_API_URL env var, falling back to the Vite proxy path '/api'.
 */

const BASE_URL = import.meta.env.VITE_API_URL || '/api'

async function request(path, options = {}) {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || `HTTP ${res.status}`)
  }
  return res.json()
}

/** POST /analyze — run fake/real classification */
export async function analyzeNews(text, modelType = 'ml') {
  return request('/analyze', {
    method: 'POST',
    body: JSON.stringify({ text, model_type: modelType }),
  })
}

/** GET /history — fetch past analyses */
export async function fetchHistory(limit = 50) {
  return request(`/history?limit=${limit}`)
}

/** DELETE /history — clear all history */
export async function clearHistory() {
  return request('/history', { method: 'DELETE' })
}

/** DELETE /history/:id — remove single entry */
export async function deletePrediction(id) {
  return request(`/history/${id}`, { method: 'DELETE' })
}

/** POST /send-report — email a verification report */
export async function sendReport(payload) {
  return request('/send-report', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

/** GET /health — backend connection status */
export async function fetchHealth() {
  return request('/health')
}

/** GET /stats — aggregate analytics */
export async function fetchStats() {
  return request('/stats')
}
