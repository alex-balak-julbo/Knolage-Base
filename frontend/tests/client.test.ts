import assert from 'node:assert/strict'
import { afterEach, beforeEach, describe, it } from 'node:test'
import { ApiError, configure, getAccessToken, request, requestBlob, setAccessToken } from '../src/api/client.ts'
import { nodesApi, searchApi } from '../src/api/endpoints.ts'

type Call = { url: string; init: RequestInit }
let calls: Call[] = []
let responder: (c: Call) => Response | Promise<Response>
const realFetch = globalThis.fetch

const json = (body: unknown, status = 200, headers: Record<string, string> = {}) =>
  new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json', ...headers } })
const hdr = (c: Call, k: string) => (c.init.headers as Record<string, string>)[k]

beforeEach(() => {
  calls = []
  let lost = 0
  configure({ baseUrl: '/api/v1', onAuthLost: () => { lost++; (globalThis as any).__lost = lost } })
  ;(globalThis as any).__lost = 0
  setAccessToken(null)
  globalThis.fetch = (async (url: string, init: RequestInit) => {
    const c = { url: String(url), init }
    calls.push(c)
    return responder(c)
  }) as typeof fetch
})
afterEach(() => { globalThis.fetch = realFetch })

describe('api client', () => {
  it('sends the bearer token, JSON body and cookies', async () => {
    setAccessToken('tok')
    responder = () => json({ ok: true })
    await request('POST', '/nodes', { json: { a: 1 } })
    assert.equal(hdr(calls[0], 'Authorization'), 'Bearer tok')
    assert.equal(hdr(calls[0], 'Content-Type'), 'application/json')
    assert.equal(calls[0].init.credentials, 'include')
    assert.equal(calls[0].init.body, '{"a":1}')
  })

  it('serialises query strings, skipping empty values', async () => {
    responder = () => json({ items: [], total: 0 })
    await searchApi.search('café', { scope: 'title', folderId: null, limit: 5 })
    assert.equal(calls[0].url, '/api/v1/search?q=caf%C3%A9&scope=title&limit=5')
  })

  it('turns problem+json into ApiError with code, errors and extras', async () => {
    responder = () => json({ title: 'Conflict', detail: 'stale', code: 'version_conflict', current_version: 7 }, 409)
    await assert.rejects(nodesApi.patch('x', { name: 'n' }, 3), (e: ApiError) => {
      assert.equal(e.status, 409)
      assert.equal(e.code, 'version_conflict')
      assert.equal(e.body.current_version, 7)
      assert.equal(e.message, 'stale')
      return true
    })
    assert.equal(hdr(calls[0], 'If-Match'), '3')
  })

  it('handles empty and non-JSON error bodies', async () => {
    responder = () => new Response('boom', { status: 502, statusText: 'Bad Gateway' })
    await assert.rejects(request('GET', '/tree'), (e: ApiError) => e.status === 502 && e.message === 'Bad Gateway')
    responder = () => new Response(null, { status: 204 })
    assert.equal(await request('DELETE', '/x'), undefined)
  })

  it('refreshes once on 401 and retries the original request', async () => {
    setAccessToken('old')
    responder = (c) => {
      if (c.url.endsWith('/auth/refresh')) return json({ access_token: 'new' })
      return hdr(c, 'Authorization') === 'Bearer new' ? json({ nodes: [] }) : json({ title: 'Unauthorized' }, 401)
    }
    assert.deepEqual(await nodesApi.tree(), [])
    assert.deepEqual(calls.map((c) => c.url.replace('/api/v1', '')), ['/tree', '/auth/refresh', '/tree'])
    assert.equal(getAccessToken(), 'new')
  })

  it('shares a single refresh between parallel requests', async () => {
    setAccessToken('old')
    responder = async (c) => {
      if (c.url.endsWith('/auth/refresh')) { await new Promise((r) => setTimeout(r, 10)); return json({ access_token: 'new' }) }
      return hdr(c, 'Authorization') === 'Bearer new' ? json({ ok: 1 }) : json({}, 401)
    }
    await Promise.all([request('GET', '/a'), request('GET', '/b'), request('GET', '/c')])
    assert.equal(calls.filter((c) => c.url.endsWith('/auth/refresh')).length, 1)
  })

  it('reports auth lost when the refresh fails, and does not loop', async () => {
    setAccessToken('old')
    responder = () => json({ title: 'Unauthorized', code: 'token_expired' }, 401)
    await assert.rejects(request('GET', '/tree'), (e: ApiError) => e.status === 401)
    assert.equal(getAccessToken(), null)
    assert.equal((globalThis as any).__lost, 1)
    assert.equal(calls.length, 2) // original + refresh, no retry
  })

  it('does not try to refresh failed logins', async () => {
    responder = () => json({ title: 'Unauthorized', code: 'invalid_credentials' }, 401)
    await assert.rejects(request('POST', '/auth/login', { json: {}, auth: false }))
    assert.equal(calls.length, 1)
  })

  it('passes keepalive and reads the download filename', async () => {
    responder = () => new Response('# md', { headers: { 'Content-Disposition': 'attachment; filename="page.md"' } })
    const r = await requestBlob('/export/1', { query: { format: 'md' } })
    assert.equal(r.filename, 'page.md')
    assert.equal(await r.blob.text(), '# md')
    responder = () => json({})
    await nodesApi.patch('x', {}, 1, { keepalive: true })
    assert.equal(calls[1].init.keepalive, true)
  })
})
