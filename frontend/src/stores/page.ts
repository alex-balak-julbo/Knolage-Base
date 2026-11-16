import { defineStore } from 'pinia'
import { ref } from 'vue'
import { ApiError } from '../api/client.ts'
import { nodesApi, trashApi } from '../api/endpoints.ts'
import type { NodeFull } from '../api/types.ts'
import { t } from '../i18n.ts'
import { sanitizeForSave, type DocNode } from '../lib/doc.ts'
import { useTreeStore } from './tree.ts'
import { useUiStore } from './ui.ts'

export type SaveStatus = 'idle' | 'dirty' | 'saving' | 'saved' | 'error' | 'conflict'

interface Pending {
  name?: string
  props?: Record<string, string>
  content?: DocNode
}

const DEBOUNCE_MS = 800
const RETRY_MS = 5000

export const usePageStore = defineStore('page', () => {
  const current = ref<NodeFull | null>(null)
  const loading = ref(false)
  const notFound = ref(false)
  const status = ref<SaveStatus>('idle')
  const errorMessage = ref('')
  /** Bumped whenever the editor must be rebuilt from `current.content` (page switch, server-side change). */
  const rev = ref(0)

  let pending: Pending = {}
  let timer: ReturnType<typeof setTimeout> | undefined
  let inFlight: Promise<void> | null = null

  const hasPending = () => Object.keys(pending).length > 0

  function schedule(fields: Pending, delay = DEBOUNCE_MS): void {
    if (!current.value) return
    pending = {
      ...pending,
      ...fields,
      props: fields.props ? { ...pending.props, ...fields.props } : pending.props,
    }
    if (pending.props === undefined) delete pending.props
    if (status.value !== 'saving') status.value = 'dirty'
    clearTimeout(timer)
    timer = setTimeout(() => void flush(), delay)
  }

  async function flush(): Promise<void> {
    clearTimeout(timer)
    while (inFlight) await inFlight
    if (!current.value || !hasPending() || status.value === 'conflict') return
    const node = current.value
    const fields = pending
    pending = {}
    inFlight = save(node, fields).finally(() => {
      inFlight = null
    })
    await inFlight
  }

  function restorePending(fields: Pending): void {
    pending = { ...fields, ...pending, props: { ...fields.props, ...pending.props } }
    if (!Object.keys(pending.props ?? {}).length) delete pending.props
  }

  async function save(node: NodeFull, fields: Pending): Promise<void> {
    const tree = useTreeStore()
    const ui = useUiStore()
    status.value = 'saving'
    const payload: Record<string, unknown> = { ...fields }
    if (fields.content) payload.content = sanitizeForSave(fields.content)
    try {
      const res = await nodesApi.patch(node.id, payload, node.version)
      if (current.value?.id === node.id) {
        current.value = {
          ...current.value,
          version: res.version, name: res.name, props: res.props, updated_at: res.updated_at,
          content: (payload.content as DocNode | undefined) ?? current.value.content,
        }
      }
      tree.patchLocal(node.id, { name: res.name, version: res.version, updated_at: res.updated_at, status: res.props?.status })
      if (res.deleted_ids?.length) {
        tree.removeLocal(res.deleted_ids)
        const first = res.deleted_ids[0]
        ui.toast(t('toast.subDeleted'), {
          label: t('toast.undo'),
          run: async () => {
            await tree.restore(first) // also re-adds the link to this page
            await load(node.id, { force: true })
          },
        })
      }
      status.value = hasPending() ? 'dirty' : 'saved'
      errorMessage.value = ''
      if (hasPending()) timer = setTimeout(() => void flush(), DEBOUNCE_MS)
    } catch (e) {
      restorePending(fields)
      if (e instanceof ApiError && e.code === 'version_conflict') {
        status.value = 'conflict'
        void resolveConflict()
      } else {
        status.value = 'error'
        errorMessage.value = e instanceof ApiError ? e.detail || e.message : t('toast.error')
        // network errors and 5xx are worth retrying; validation errors (422) are not
        if (!(e instanceof ApiError) || e.status >= 500) timer = setTimeout(() => void flush(), RETRY_MS)
      }
    }
  }

  async function resolveConflict(): Promise<void> {
    const ui = useUiStore()
    const choice = await ui.conflict()
    if (!current.value) return
    if (choice === 'reload') {
      pending = {}
      status.value = 'idle'
      await load(current.value.id, { force: true })
    } else if (choice === 'overwrite') {
      const fresh = await nodesApi.get(current.value.id)
      current.value = { ...current.value, version: fresh.version }
      status.value = 'dirty'
      await flush()
    } // dialog dismissed: stay in the conflict state until the user retries
  }

  /** Manual retry (button): clears conflict/error state and saves now. */
  async function retry(): Promise<void> {
    if (status.value === 'conflict') return resolveConflict()
    status.value = 'dirty'
    await flush()
  }

  async function load(id: string, opts: { force?: boolean } = {}): Promise<void> {
    if (!opts.force && current.value?.id === id) return
    await flush() // never drop edits of the page we are leaving
    loading.value = true
    notFound.value = false
    try {
      const node = await nodesApi.get(id)
      if (node.type !== 'page') {
        current.value = null
        notFound.value = true
        return
      }
      current.value = node
      status.value = 'idle'
      pending = {}
      rev.value++
    } catch (e) {
      if (e instanceof ApiError && e.status === 404) {
        current.value = null
        notFound.value = true
      } else {
        throw e
      }
    } finally {
      loading.value = false
    }
  }

  /** Server-side changes to these pages (sub-page links added/removed): reload the open one. */
  async function onAffected(ids: string[]): Promise<void> {
    if (current.value && ids.includes(current.value.id)) await load(current.value.id, { force: true })
  }

  /** Keep our version in step when the tree renames or moves the open page. */
  function adopt(id: string, res: NodeFull): void {
    if (current.value?.id === id) current.value = { ...current.value, version: res.version, name: res.name, parent_id: res.parent_id }
  }

  /** Best-effort save while the tab closes (fetch keepalive keeps the headers, unlike sendBeacon). */
  function flushKeepalive(): void {
    if (!current.value || !hasPending() || status.value === 'conflict') return
    const payload: Record<string, unknown> = { ...pending }
    if (pending.content) payload.content = sanitizeForSave(pending.content)
    void nodesApi.patch(current.value.id, payload, current.value.version, { keepalive: true }).catch(() => {})
  }

  function clear(): void {
    clearTimeout(timer)
    pending = {}
    current.value = null
    status.value = 'idle'
  }

  return { current, loading, notFound, status, errorMessage, rev, schedule, flush, retry, load, onAffected, adopt, flushKeepalive, clear }
})
