<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { onBeforeRouteLeave, onBeforeRouteUpdate, RouterLink, useRoute } from 'vue-router'
import PageEditor from '../components/editor/PageEditor.vue'
import PropertiesPanel from '../components/page/PropertiesPanel.vue'
import { useNodeActions } from '../composables/useNodeActions'
import { t } from '../i18n'
import { ancestors } from '../lib/tree'
import { usePageStore } from '../stores/page'
import { useTemplatesStore } from '../stores/templates'
import { useTreeStore } from '../stores/tree'
import { useUiStore } from '../stores/ui'

const route = useRoute()
const page = usePageStore()
const tree = useTreeStore()
const templates = useTemplatesStore()
const ui = useUiStore()
const actions = useNodeActions()

const id = computed(() => route.params.id as string)
const title = ref('')
const titleEl = ref<HTMLInputElement | null>(null)
const template = computed(() => templates.byId.get(page.current?.template_id ?? ''))
const crumbs = computed(() => (page.current ? ancestors(tree.index, page.current.id) : []))
const node = computed(() => tree.byId(id.value))

watch(id, async (v) => {
  await page.load(v)
  if (route.query.new && page.current) void nextTick(() => titleEl.value?.select())
}, { immediate: true })

// keep the sidebar in step with the open page (also once the tree finishes loading)
watch(() => [tree.loaded, page.current?.id] as const, ([loaded, cur]) => {
  if (loaded && cur) {
    tree.expandTo(cur)
    tree.select(cur)
  }
}, { immediate: true })

// title input is local state: the server echo never overwrites what is being typed
watch(() => [page.current?.id, page.rev] as const, () => (title.value = page.current?.name ?? ''), { immediate: true })

function onTitle(e: Event) {
  title.value = (e.target as HTMLInputElement).value
  const name = title.value.trim()
  if (!name) return // the server requires a non-empty name: keep the previous one until something is typed
  page.schedule({ name })
  tree.patchLocal(id.value, { name })
}

function revealFolder(folderId: string) {
  tree.expandTo(folderId)
  tree.toggle(folderId, true)
  tree.select(folderId)
  ui.sidebarOpen = true
}

onBeforeRouteLeave(() => page.flush())
onBeforeRouteUpdate(() => page.flush())

const statusLabel = computed(() => {
  switch (page.status) {
    case 'saving': return t('page.saving')
    case 'dirty': return t('page.dirty')
    case 'saved': return '✓ ' + t('page.saved')
    case 'conflict': return t('page.conflict')
    case 'error': return t('page.error') + (page.errorMessage ? ` — ${page.errorMessage}` : '')
    default: return ''
  }
})
</script>

<template>
  <div class="mx-auto w-full max-w-3xl px-4 py-5 md:px-8">
    <p v-if="page.loading && !page.current" class="text-muted">{{ t('page.loading') }}</p>
    <div v-else-if="page.notFound" class="py-16 text-center">
      <p class="text-lg">{{ t('page.notFound') }}</p>
      <RouterLink to="/" class="mt-3 inline-block text-accent underline">{{ t('app.title') }}</RouterLink>
    </div>

    <template v-else-if="page.current">
      <div class="flex flex-wrap items-center gap-2">
        <nav class="min-w-0 flex-1 truncate text-sm text-muted" aria-label="breadcrumb">
          {{ t('crumb.root') }}
          <template v-for="a in crumbs" :key="a.id">
            ›
            <RouterLink v-if="a.type === 'page'" :to="{ name: 'page', params: { id: a.id } }" class="text-accent hover:underline">{{ a.name }}</RouterLink>
            <button v-else type="button" class="text-accent hover:underline" @click="revealFolder(a.id)">{{ a.name }}</button>
          </template>
        </nav>
        <span class="text-xs" :class="page.status === 'error' || page.status === 'conflict' ? 'text-danger' : 'text-muted'" role="status">{{ statusLabel }}</span>
        <button v-if="page.status === 'error' || page.status === 'conflict'" type="button" class="btn" @click="page.retry()">{{ t('page.retry') }}</button>
        <button v-if="node" type="button" class="btn" @click="actions.exportNode(node)">⤓ {{ t('page.export') }}</button>
        <button v-if="node" type="button" class="btn" @click="actions.remove(node)">{{ t('page.delete') }}</button>
      </div>

      <span v-if="template" class="mt-3 inline-block rounded-full bg-accent-soft px-3 py-0.5 text-xs text-accent">{{ template.icon }} {{ template.name }}</span>
      <input
        ref="titleEl"
        :value="title"
        type="text"
        class="mt-1 w-full bg-transparent py-1 text-3xl font-bold outline-none"
        :placeholder="t('page.titlePlaceholder')"
        :aria-label="t('page.titlePlaceholder')"
        maxlength="255"
        @input="onTitle"
      />

      <!-- re-created on every page switch / server-side reload so they start from the saved state -->
      <PropertiesPanel :key="`props-${page.current.id}-${page.rev}`" :node="page.current" />
      <PageEditor :key="`ed-${page.current.id}-${page.rev}`" :page-id="page.current.id" :doc="page.current.content ?? { type: 'doc', content: [{ type: 'paragraph' }] }" />
    </template>
  </div>
</template>
