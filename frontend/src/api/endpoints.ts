import { del, get, patch, post, request, requestBlob, setAccessToken } from './client.ts'
import type {
  CreateNodeInput, LoginResponse, MoveInput, NodeFull, SearchItem, SearchScope, Template, TrashItem, TreeNode, User,
} from './types.ts'

export const authApi = {
  async login(email: string, password: string): Promise<LoginResponse> {
    const r = await post<LoginResponse>('/auth/login', { email, password }, { auth: false })
    setAccessToken(r.access_token)
    return r
  },
  async refresh(): Promise<LoginResponse | null> {
    try {
      const r = await post<LoginResponse>('/auth/refresh', undefined, { auth: false })
      setAccessToken(r.access_token)
      return r
    } catch {
      return null
    }
  },
  async logout(): Promise<void> {
    try {
      await post('/auth/logout', undefined, { auth: false })
    } finally {
      setAccessToken(null)
    }
  },
  me: () => get<User>('/auth/me'),
}

export const nodesApi = {
  tree: () => get<{ nodes: TreeNode[] }>('/tree').then((r) => r.nodes),
  get: (id: string) => get<NodeFull>(`/nodes/${id}`),
  create: (input: CreateNodeInput) => post<NodeFull>('/nodes', input),
  /** `version` goes in If-Match; the server answers 409 with `current_version` when it is stale. */
  patch: (id: string, fields: Record<string, unknown>, version: number, opts: { keepalive?: boolean } = {}) =>
    patch<NodeFull>(`/nodes/${id}`, fields, { headers: { 'If-Match': String(version) }, keepalive: opts.keepalive }),
  move: (id: string, input: MoveInput) => post<NodeFull>(`/nodes/${id}/move`, input),
  remove: (id: string) => del<{ deleted: number; ids: string[]; affected_ids: string[] }>(`/nodes/${id}`),
  stats: (id: string) => get<{ descendants: number; folders: number; pages: number }>(`/nodes/${id}/stats`),
}

export const trashApi = {
  list: () => get<{ items: TrashItem[] }>('/trash').then((r) => r.items),
  restore: (id: string) => post<NodeFull>(`/trash/${id}/restore`),
  purge: (id: string) => del<{ purged: number }>(`/trash/${id}`),
  empty: () => del<{ purged: number }>('/trash'),
}

export const templatesApi = {
  list: () => get<{ items: Template[] }>('/templates').then((r) => r.items),
}

export const searchApi = {
  search: (
    q: string,
    opts: { scope?: SearchScope; folderId?: string | null; limit?: number; offset?: number; signal?: AbortSignal } = {},
  ) =>
    get<{ items: SearchItem[]; total: number }>('/search', {
      query: { q, scope: opts.scope ?? 'all', folder_id: opts.folderId, limit: opts.limit, offset: opts.offset },
      signal: opts.signal,
    }),
}

export const assetsApi = {
  upload(file: File, nodeId?: string) {
    const body = new FormData()
    body.append('file', file)
    if (nodeId) body.append('node_id', nodeId)
    return request<{ id: string; url: string; width: number; height: number }>('POST', '/assets', { body })
  },
}

export const exportApi = {
  download: (id: string, format: 'md' | 'html' | 'txt' | 'zip') => requestBlob(`/export/${id}`, { query: { format } }),
}
