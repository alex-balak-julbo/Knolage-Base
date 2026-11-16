
import { computed } from 'vue'
import { t } from '../../i18n'
import type { Row } from '../../lib/tree'
import { useTemplatesStore } from '../../stores/templates'

const props = defineProps<{
  row: Row
  selected: boolean
  tabbable: boolean
  dragging: boolean
  drop: 'before' | 'inside' | 'after' | null
}>()
const emit = defineEmits<{
  (e: 'open'): void
  (e: 'toggle'): void
  (e: 'focus'): void
  (e: 'menu', ev: MouseEvent): void
  (e: 'add', ev: MouseEvent): void
}>()

const templates = useTemplatesStore()
const icon = computed(() => props.row.node.icon || (props.row.node.type === 'folder' ? '📁' : templates.icon(props.row.node.template_id)))
