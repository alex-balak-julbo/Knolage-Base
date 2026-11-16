
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
