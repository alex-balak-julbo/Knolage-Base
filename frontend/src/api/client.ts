// Minimal fetch wrapper: Bearer token in memory, single-flight refresh on 401, problem+json errors.

export class ApiError extends Error {
  status: number
  code?: string
  detail?: string
  errors?: Record<string, string>
  body: Record<string, unknown>
  constructor(status: number, title: string, body: Record<string, unknown> = {}) {
    super((body.detail as string) || title)
    this.name = 'ApiError'
    this.status = status
    this.code = body.code as string | undefined
    this.detail = body.detail as string | undefined
    this.errors = body.errors as Record<string, string> | undefined
    this.body = body
  }
}

export interface RequestOptions {
  json?: unknown
  body?: BodyInit
  query?: Record<string, string | number | boolean | null | undefined>
  headers?: Record<string, string>
  signal?: AbortSignal
  keepalive?: boolean
  auth?: boolean
}

let baseUrl = '/api/v1'
let token: string | null = null
let onAuthLost: (() => void) | undefined
let refreshing: Promise<boolean> | null = null

export function configure(opts: { baseUrl?: string; onAuthLost?: () => void }): void {
  if (opts.baseUrl !== undefined) baseUrl = opts.baseUrl.replace(/\/$/, '')
  if (opts.onAuthLost !== undefined) onAuthLost = opts.onAuthLost
}

export const setAccessToken = (t: string | null): void => {
  token = t
}
export const getAccessToken = (): string | null => token

export function refreshAccessToken(): Promise<boolean> {
  if (refreshing) return refreshing
  refreshing = (async () => {
    try {
      const res = await fetch(baseUrl + '/auth/refresh', { method: 'POST', credentials: 'include' })
      if (!res.ok) return false
      token = ((await res.json()) as { access_token: string }).access_token
      return true
    } catch {
      return false
    } finally {
      refreshing = null
    }
  })()
  return refreshing
}

function queryString(query?: RequestOptions['query']): string {
  if (!query) return ''
  const p = new URLSearchParams()
  for (const [k, v] of Object.entries(query)) if (v !== undefined && v !== null && v !== '') p.set(k, String(v))
  const s = p.toString()
  return s ? '?' + s : ''
}

async function send(method: string, path: string, opts: RequestOptions, retried = false): Promise<Response> {
  const headers: Record<string, string> = { ...opts.headers }
  if (opts.json !== undefined) headers['Content-Type'] = 'application/json'
  if (token && opts.auth !== false) headers['Authorization'] = 'Bearer ' + token
  const res = await fetch(baseUrl + path + queryString(opts.query), {
    method,
    headers,
    credentials: 'include',
    body: opts.json !== undefined ? JSON.stringify(opts.json) : opts.body,
    signal: opts.signal,
    keepalive: opts.keepalive,
  })
  if (res.status === 401 && !retried && opts.auth !== false && !path.startsWith('/auth/')) {
    if (await refreshAccessToken()) return send(method, path, opts, true)
    token = null
    onAuthLost?.()
  }
  return res
}

async function toError(res: Response): Promise<ApiError> {
  let body: Record<string, unknown> = {}
  try {
    body = (await res.json()) as Record<string, unknown>
  } catch {
    /* not JSON */
  }
  return new ApiError(res.status, (body.title as string) || res.statusText || 'Request failed', body)
}

export async function request<T = unknown>(method: string, path: string, opts: RequestOptions = {}): Promise<T> {
  const res = await send(method, path, opts)
  if (!res.ok) throw await toError(res)
  if (res.status === 204) return undefined as T
  return (await res.json()) as T
}

/** Like request() but returns the raw body plus the filename suggested by the server. */
export async function requestBlob(path: string, opts: RequestOptions = {}): Promise<{ blob: Blob; filename: string }> {
  const res = await send('GET', path, opts)
  if (!res.ok) throw await toError(res)
  const m = /filename="?([^";]+)"?/i.exec(res.headers.get('Content-Disposition') ?? '')
  return { blob: await res.blob(), filename: m ? m[1] : 'export' }
}

/** Response of a PATCH-style call that also needs the ETag/version, kept for completeness. */
export const get = <T>(path: string, opts?: RequestOptions) => request<T>('GET', path, opts)
export const post = <T>(path: string, json?: unknown, opts?: RequestOptions) => request<T>('POST', path, { ...opts, json })
export const patch = <T>(path: string, json: unknown, opts?: RequestOptions) => request<T>('PATCH', path, { ...opts, json })
export const del = <T>(path: string, opts?: RequestOptions) => request<T>('DELETE', path, opts)
