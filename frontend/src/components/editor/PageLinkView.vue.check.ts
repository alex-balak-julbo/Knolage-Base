
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { nodeViewProps, NodeViewWrapper } from '@tiptap/vue-3'
import { t } from '../../i18n'
import { useTemplatesStore } from '../../stores/templates'
import { useTreeStore } from '../../stores/tree'
import { useUiStore } from '../../stores/ui'

const props = defineProps(nodeViewProps)
const tree = useTreeStore()
const templates = useTemplatesStore()
const ui = useUiStore()
const router = useRouter()

const target = computed(() => tree.byId(props.node.attrs.pageId as string))

function open() {
  if (target.value) void router.push({ name: 'page', params: { id: target.value.id } })
}

// Removing the card moves the sub-page to the trash (the server does it when the page is saved).
async function remove() {
  const ok = await ui.confirm({
    title: t('confirm.deleteTitle'),
    message: t('confirm.subpage', { name: target.value?.name ?? '' }),
    confirmLabel: t('menu.delete'),
    danger: true,
  })
  if (ok) props.deleteNode()
}
