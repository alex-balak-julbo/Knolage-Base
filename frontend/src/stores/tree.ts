import { defineStore } from 'pinia'
import { computed, ref, watch } from 'vue'
import { ApiError } from '../api/client.ts'
import { nodesApi, trashApi } from '../api/endpoints.ts'
import type { CreateNodeInput, NodeFull } from '../api/types.ts'
import { t } from '../i18n.ts'
import {
  ancestors, buildIndex, flatten, nextSiblingByPosition, optimisticPosition, type TreeNode,
} from '../lib/tree.ts'
import { usePageStore } from './page.ts'
import { useUiStore } from './ui.ts'

const KEY = 'docbase.expanded'

function readExpanded(): Record<string, boolean> {
  try {
    return JSON.parse(localStorage.getItem(KEY) || '{}') as Record<string, boolean>
  } catch {
    return {}
  }
}

export const toTreeNode = (n: NodeFull): TreeNode => ({
  id: n.id, type: n.type, parent_id: n.parent_id, name: n.name, icon: n.icon, position: n.position,
  template_id: n.template_id, version: n.version, updated_at: n.updated_at, status: n.props?.status,
})

export interface MovePlan {
  parentId: string | null
  beforeId?: string
  afterId?: string
}

export const useTreeStore = defineStore('tree', () => {
  const nodes = ref<TreeNode[]>([])
  const loaded = ref(false)
  const expanded = ref<Record<string, boolean>>(readExpanded())
  const selectedFolderId = ref<string | null>(null)
  const focusedId = ref<string | null>(null)

  const index = computed(() => buildIndex(nodes.value))
  const rows = computed(() => flatten(index.value, expanded.value))
  const byId = (id: string | null | undefined): TreeNode | undefined => (id ? index.value.byId.get(id) : undefined)

  watch(expanded, (v) => {
    try {
      localStorage.setItem(KEY, JSON.stringify(v))
    } catch {
      /* ignore */
    }
  }, { deep: true })

  async function load(): Promise<void> {
    nodes.value = await nodesApi.tree()
    loaded.value = true
  }

  function clear(): void {
    nodes.value = []
    loaded.value = false
    selectedFolderId.value = null
    focusedId.value = null
  }

  function toggle(id: string, open?: boolean): void {
    expanded.value = { ...expanded.value, [id]: open ?? !expanded.value[id] }
  }

  function expandTo(id: string): void {
    const next = { ...expanded.value }
    for (const a of ancestors(index.value, id)) next[a.id] = true
    expanded.value = next
  }

  /** Remember the folder that "+ Page" should target: the folder itself, or the page's nearest folder. */
  function select(id: string): void {
    const n = byId(id)
    if (!n) return
    focusedId.value = id
    if (n.type === 'folder') selectedFolderId.value = n.id
    else selectedFolderId.value = [...ancestors(index.value, id)].reverse().find((a) => a.type === 'folder')?.id ?? null
  }

  function patchLocal(id: string, patch: Partial<TreeNode>): void {
    const i = nodes.value.findIndex((n) => n.id === id)
    if (i >= 0) nodes.value[i] = { ...nodes.value[i], ...patch }
  }

  function removeLocal(ids: string[]): void {
    const gone = new Set(ids)
    nodes.value = nodes.value.filter((n) => !gone.has(n.id))
    if (selectedFolderId.value && gone.has(selectedFolderId.value)) selectedFolderId.value = null
  }

  /** The server changed these pages' content (sub-page links): refresh the open one if needed. */
  async function notifyAffected(ids?: string[]): Promise<void> {
    if (ids?.length) await usePageStore().onAffected(ids)
  }

  async function create(input: CreateNodeInput): Promise<NodeFull> {
    const full = await nodesApi.create(input)
    nodes.value = [...nodes.value, toTreeNode(full)]
    if (full.parent_id) toggle(full.parent_id, true)
    await notifyAffected(full.affected_ids)
    return full
  }

  async function rename(id: string, name: string): Promise<void> {
    const attempt = () => nodesApi.patch(id, { name }, byId(id)!.version)
    let res: NodeFull
    try {
      res = await attempt()
    } catch (e) {
      if (!(e instanceof ApiError && e.status === 409)) throw e
      await load() // our cached version was stale: refresh and retry once
      res = await attempt()
    }
    patchLocal(id, { name: res.name, version: res.version, updated_at: res.updated_at })
    usePageStore().adopt(id, res)
  }

  async function remove(id: string) {
    const res = await nodesApi.remove(id)
    removeLocal(res.ids)
    await notifyAffected(res.affected_ids)
    return res
  }

  async function restore(id: string): Promise<void> {
    const res = await trashApi.restore(id)
    await load()
    await notifyAffected(res.parent_id ? [res.parent_id] : [])
  }

  /** Optimistic move: the UI updates at once, rolls back on error, and offers Undo. */
  async function move(id: string, plan: MovePlan, opts: { silent?: boolean } = {}): Promise<void> {
    const node = byId(id)
    if (!node) return
    const ui = useUiStore()
    const prev = { parent_id: node.parent_id, position: node.position, nextId: nextSiblingByPosition(index.value, id) }
    patchLocal(id, { parent_id: plan.parentId, position: optimisticPosition(index.value, id, plan.parentId, plan.beforeId, plan.afterId) })
    if (plan.parentId) toggle(plan.parentId, true)
    try {
      const res = await nodesApi.move(id, { parent_id: plan.parentId, before_id: plan.beforeId, after_id: plan.afterId })
      patchLocal(id, { parent_id: res.parent_id, position: res.position, version: res.version, updated_at: res.updated_at })
      usePageStore().adopt(id, res)
      void load().catch(() => {}) // reconcile: the server may have renumbered the siblings
      await notifyAffected(res.affected_ids)
      if (opts.silent) return
      const to = byId(plan.parentId)
      const message = prev.parent_id !== plan.parentId
        ? plan.parentId && to ? t('toast.moved', { name: node.name, to: to.name }) : t('toast.movedRoot', { name: node.name })
        : t('toast.reordered')
      ui.toast(message, {
        label: t('toast.undo'),
        run: () => move(id, { parentId: prev.parent_id, beforeId: prev.nextId ?? undefined }, { silent: true }),
      })
    } catch (e) {
      patchLocal(id, { parent_id: prev.parent_id, position: prev.position })
      if (e instanceof ApiError && ['cycle', 'invalid_parent', 'max_depth'].includes(e.code ?? '')) {
        ui.toast(t('toast.moveError', { reason: t(`err.${e.code}`) }))
      } else {
        ui.toastError(e)
      }
    }
  }

  return {
    nodes, loaded, expanded, selectedFolderId, focusedId, index, rows,
    byId, load, clear, toggle, expandTo, select, patchLocal, removeLocal, create, rename, remove, restore, move,
  }
})
