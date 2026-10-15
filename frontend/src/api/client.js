// Thin fetch wrapper. Every failure becomes an ApiError with the server's state
// (e.g. SERVICE_UNAVAILABLE) so the UI can show it instead of an empty table.

export const API_BASE = import.meta.env.VITE_API_BASE || '/api'

export class ApiError extends Error {
  constructor(status, body) {
    super(body?.detail || `Request failed with status ${status}`)
    this.status = status
    this.body = body
  }
}

function buildUrl(path, params = {}) {
  const url = new URL(API_BASE + path, window.location.origin)
  Object.entries(params).forEach(([key, value]) => {
    if (value !== '' && value !== null && value !== undefined) url.searchParams.set(key, value)
  })
  return url
}

async function request(method, path, { params, body } = {}) {
  const res = await fetch(buildUrl(path, params), {
    method,
    headers: body ? { 'Content-Type': 'application/json' } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  })
  const data = await res.json().catch(() => ({}))
  if (!res.ok) throw new ApiError(res.status, data)
  return data
}

export const apiGet = (path, params) => request('GET', path, { params })
export const apiPost = (path, body) => request('POST', path, { body })
export const apiPatch = (path, body) => request('PATCH', path, { body })
