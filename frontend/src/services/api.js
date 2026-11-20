// Thin API client. Same-origin: Vite proxies /api in dev, Vercel routes /api/* to the Python function.
const TIMEOUT_MS = 30000 // the first request after idle can wait for a cold start

export class ApiError extends Error {
  constructor(message, { status = 0, code = 'network_error', errors = [] } = {}) {
    super(message)
    this.status = status
    this.code = code
    this.errors = errors
  }
}

async function request(path, { method = 'GET', body, retries = 0 } = {}) {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS)
  try {
    const res = await fetch(path, {
      method,
      signal: controller.signal,
      headers: body ? { 'Content-Type': 'application/json' } : undefined,
      body: body ? JSON.stringify(body) : undefined,
    })
    let data = null
    try { data = await res.json() } catch { /* non-JSON body */ }
    if (!res.ok) {
      const d = data?.detail
      if (res.status >= 500 && retries > 0) return request(path, { method, body, retries: retries - 1 })
      throw new ApiError(d?.message || 'The request could not be completed.', { status: res.status, code: d?.code || 'http_error', errors: d?.errors || [] })
    }
    return data
  } catch (err) {
    if (err instanceof ApiError) throw err
    if (retries > 0) return request(path, { method, body, retries: retries - 1 })
    const timedOut = err?.name === 'AbortError'
    throw new ApiError(timedOut ? 'The server took too long to respond. Please try again.' : 'Could not reach the prediction service. Check your connection and try again.', { code: timedOut ? 'timeout' : 'network_error' })
  } finally {
    clearTimeout(timer)
  }
}

const cache = new Map() // GET responses are static per deployment, so keep them for the session (memory only)
const cached = (key, path) => {
  if (!cache.has(key)) cache.set(key, request(path, { retries: 1 }).catch((e) => { cache.delete(key); throw e }))
  return cache.get(key)
}

export const api = {
  features: () => cached('features', '/api/features'),
  model: () => cached('model', '/api/model'),
  analytics: () => cached('analytics', '/api/analytics'),
  predict: (inputs, { explain = true, topN = 10 } = {}) =>
    request('/api/predict', { method: 'POST', body: { inputs, explain, top_n: topN } }),
}
