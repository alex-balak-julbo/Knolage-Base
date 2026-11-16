
import { computed, nextTick, ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { useNodeActions } from '../../composables/useNodeActions'
import { useTreeDnd } from '../../composables/useTreeDnd'
import { locale, setLocale, t, type Locale } from '../../i18n'
import type { TreeNode } from '../../lib/tree'
import { useAuthStore } from '../../stores/auth'
import { usePageStore } from '../../stores/page'
import { useSearchStore } from '../../stores/search'
import { useTreeStore } from '../../stores/tree'
import { useUiStore, type Theme } from '../../stores/ui'
import Menu from '../common/Menu.vue'
import type { MenuItem } from '../common/types'
import SearchResults from './SearchResults.vue'
import TreeRow from './TreeRow.vue'

const tree = useTreeStore()
const search = useSearchStore()
const ui = useUiStore()
const auth = useAuthStore()
const page = usePageStore()
const actions = useNodeActions()
const route = useRoute()
const router = useRouter()

const treeEl = ref<HTMLElement | null>(null)
const { dragId, drop } = useTreeDnd(treeEl)
const menu = ref<{ x: number; y: number; items: MenuItem[] } | null>(null)

const currentId = computed(() => (typeof route.params.id === 'string' ? route.params.id : null))
const tabbableId = computed(() => (tree.rows.some((r) => r.node.id === tree.focusedId) ? tree.focusedId : tree.rows[0]?.node.id ?? null))

function open(node: TreeNode) {
  tree.select(node.id)
  if (node.type === 'folder') tree.toggle(node.id)
  else {
    void router.push({ name: 'page', params: { id: node.id } })
    ui.sidebarOpen = false
  }
}

function itemsFor(node: TreeNode, createOnly = false): MenuItem[] {
  const create: MenuItem[] =
    node.type === 'folder'
      ? [
          { label: t('menu.newPage'), run: () => actions.newPage(node.id) },
          { label: t('menu.newFolder'), run: () => actions.newFolder(node.id) },
        ]
      : []
  if (createOnly) return create
  return [
    ...create,
    { label: t('menu.rename'), run: () => actions.rename(node) },
    { label: t('menu.move'), run: () => actions.moveTo(node) },
    { label: t('menu.export'), run: () => actions.exportNode(node) },
    { label: t('menu.delete'), danger: true, run: () => actions.remove(node) },
  ]
}

function showMenu(node: TreeNode, ev: MouseEvent, createOnly = false) {
  const isContext = ev.type === 'contextmenu'
  const r = (ev.currentTarget as HTMLElement).getBoundingClientRect()
  menu.value = { x: isContext ? ev.clientX : r.left, y: isContext ? ev.clientY : r.bottom + 4, items: itemsFor(node, createOnly) }
}

function focusRow(id: string) {
  tree.focusedId = id
  void nextTick(() => treeEl.value?.querySelector<HTMLElement>(`[data-node-id="${id}"]`)?.focus())
}

// WAI-ARIA tree keyboard model + the shortcuts from the spec (F2, Delete, Ctrl+M)
function onKeydown(e: KeyboardEvent) {
  if ((e.target as HTMLElement).tagName === 'INPUT') return
  const rows = tree.rows
  const i = rows.findIndex((r) => r.node.id === (tree.focusedId ?? rows[0]?.node.id))
  const row = rows[i]
  if (!row) return
  const id = row.node.id
  const stop = () => e.preventDefault()
  switch (e.key) {
    case 'ArrowDown': stop(); if (rows[i + 1]) focusRow(rows[i + 1].node.id); break
    case 'ArrowUp': stop(); if (rows[i - 1]) focusRow(rows[i - 1].node.id); break
    case 'Home': stop(); focusRow(rows[0].node.id); break
    case 'End': stop(); focusRow(rows[rows.length - 1].node.id); break
    case 'ArrowRight':
      stop()
      if (row.expandable && !row.expanded) tree.toggle(id, true)
      else if (row.expanded && rows[i + 1]) focusRow(rows[i + 1].node.id)
      break
    case 'ArrowLeft':
      stop()
      if (row.expanded) tree.toggle(id, false)
      else if (row.node.parent_id && tree.byId(row.node.parent_id)) focusRow(row.node.parent_id)
      break
    case 'Enter': case ' ': stop(); open(row.node); break
    case 'F2': stop(); void actions.rename(row.node); break
    case 'Delete': stop(); void actions.remove(row.node); break
    default:
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'm') { stop(); void actions.moveTo(row.node) }
  }
}

async function logout() {
  await page.flush()
  await auth.logout()
  tree.clear()
  page.clear()
  search.clear()
  await router.push({ name: 'login' })
}

const themes: Theme[] = ['system', 'light', 'dark']
