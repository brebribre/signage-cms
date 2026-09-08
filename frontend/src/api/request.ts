/**
 * Shared fetch helper. Every API hook goes through this.
 *
 * `credentials: 'include'` is mandatory — auth is an HttpOnly session cookie, which JS can
 * neither read nor attach by hand.
 */

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8001'

export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }

  /** 401 means "not signed in" — the router guard treats this specially. */
  get isUnauthorized() {
    return this.status === 401
  }

  /** 409 is a name collision on signup; the form shows it inline. */
  get isConflict() {
    return this.status === 409
  }
}

type Method = 'GET' | 'POST' | 'PATCH' | 'PUT' | 'DELETE'

export async function request<T>(method: Method, path: string, body?: unknown): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${BASE_URL}${path}`, {
      method,
      credentials: 'include',
      headers: body ? { 'Content-Type': 'application/json' } : undefined,
      body: body ? JSON.stringify(body) : undefined,
    })
  } catch {
    throw new ApiError(0, 'Could not reach the server')
  }

  if (!response.ok) {
    // FastAPI returns { detail: ... }. A 422 returns a list of field errors instead, so
    // flatten that to something a person can read rather than printing [object Object].
    let detail = response.statusText
    try {
      const payload = await response.json()
      if (typeof payload?.detail === 'string') {
        detail = payload.detail
      } else if (Array.isArray(payload?.detail)) {
        detail = payload.detail.map((e: { msg?: string }) => e.msg ?? '').filter(Boolean).join('; ')
      }
    } catch {
      /* body was not JSON — keep statusText */
    }
    throw new ApiError(response.status, detail)
  }

  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}
