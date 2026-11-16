<script setup lang="ts">
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
</script>

<template>
  <nav class="flex h-full w-full flex-col border-r border-line bg-side" :aria-label="t('tree.label')">
    <div class="flex items-center justify-between px-3 pb-2 pt-3">
      <RouterLink to="/" class="font-bold" @click="ui.sidebarOpen = false">📚 {{ t('app.title') }}</RouterLink>
    </div>
    <div class="flex gap-2 px-3 pb-2">
      <button type="button" class="btn" @click="actions.newFolder(null)">{{ t('nav.newFolder') }}</button>
      <button type="button" class="btn-primary" @click="actions.newPage(tree.selectedFolderId)">{{ t('nav.newPage') }}</button>
    </div>

    <!-- search -->
    <div class="flex flex-col gap-1.5 px-3 pb-2">
      <div class="relative">
        <input v-model="search.query" type="search" class="input pr-8" :placeholder="t('search.placeholder')" :aria-label="t('search.placeholder')" />
        <button v-if="search.query" type="button" class="icon-btn absolute right-1 top-1/2 -translate-y-1/2" :aria-label="t('search.clear')" @click="search.clear()">✕</button>
      </div>
      <select v-model="search.scope" class="input" :aria-label="t('search.placeholder')">
        <option value="all">{{ t('search.scope.all') }}</option>
        <option value="title">{{ t('search.scope.title') }}</option>
        <option value="content">{{ t('search.scope.content') }}</option>
      </select>
      <label v-if="tree.selectedFolderId" class="flex items-center gap-2 text-xs text-muted">
        <input v-model="search.inFolder" type="checkbox" /> {{ t('search.inFolder') }}
      </label>
    </div>

    <SearchResults v-if="search.active" />

    <!-- tree: drag & drop is only active here, not in search results -->
    <div v-else ref="treeEl" role="tree" :aria-label="t('tree.label')" class="flex-1 overflow-auto px-2 pb-3" @keydown="onKeydown">
      <p v-if="tree.loaded && !tree.rows.length" class="px-2 py-3 text-sm text-muted">{{ t('tree.empty') }}</p>
      <TreeRow
        v-for="row in tree.rows"
        :key="row.node.id"
        :row="row"
        :selected="row.node.id === currentId || row.node.id === tree.selectedFolderId"
        :tabbable="row.node.id === tabbableId"
        :dragging="dragId === row.node.id"
        :drop="drop && drop.id === row.node.id && drop.zone !== undefined ? (drop.zone as 'before' | 'inside' | 'after') : null"
        @open="open(row.node)"
        @toggle="tree.toggle(row.node.id)"
        @focus="tree.focusedId = row.node.id"
        @menu="showMenu(row.node, $event)"
        @add="showMenu(row.node, $event, true)"
      />
      <div data-root-zone class="root-zone mt-3 rounded-lg border border-dashed border-line p-3 text-center text-xs text-muted" :data-drop="drop && drop.id === null ? 'inside' : undefined">
        {{ t('tree.dropRoot') }}
      </div>
    </div>

    <footer class="flex flex-wrap items-center gap-2 border-t border-line px-3 py-2 text-xs">
      <RouterLink to="/trash" class="hover:underline" @click="ui.sidebarOpen = false">🗑 {{ t('footer.trash') }}</RouterLink>
      <select :value="ui.theme" class="rounded border border-line bg-panel px-1 py-0.5" :aria-label="t('footer.theme')" @change="ui.setTheme(($event.target as HTMLSelectElement).value as Theme)">
        <option v-for="th in themes" :key="th" :value="th">{{ t('theme.' + th) }}</option>
      </select>
      <select :value="locale" class="rounded border border-line bg-panel px-1 py-0.5" :aria-label="t('footer.lang')" @change="setLocale(($event.target as HTMLSelectElement).value as Locale)">
        <option value="fr">FR</option>
        <option value="en">EN</option>
      </select>
      <button type="button" class="ml-auto hover:underline" @click="logout">{{ t('footer.logout') }}</button>
    </footer>

    <Menu v-if="menu" :x="menu.x" :y="menu.y" :items="menu.items" @close="menu = null" />
  </nav>
</template>
