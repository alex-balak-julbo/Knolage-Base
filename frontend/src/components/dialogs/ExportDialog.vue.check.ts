
import { computed, ref } from 'vue'
import { ApiError } from '../../api/client'
import { exportApi } from '../../api/endpoints'
import { t } from '../../i18n'
import { saveBlob } from '../../lib/download'
import { useTreeStore } from '../../stores/tree'
import DialogShell from './DialogShell.vue'

const props = defineProps<{ nodeId: string }>()
const emit = defineEmits<{ (e: 'done', value?: boolean): void }>()

const tree = useTreeStore()
const node = computed(() => tree.byId(props.nodeId))
const format = ref<'md' | 'html' | 'txt' | 'zip'>(node.value?.type === 'folder' ? 'zip' : 'md')
const busy = ref(false)
const error = ref('')
const formats = [
  { id: 'md', label: 'Markdown (.md)' },
  { id: 'html', label: 'HTML (.html)' },
  { id: 'txt', label: 'Texte (.txt)' },
  { id: 'zip', label: 'ZIP' },
] as const

async function download() {
  busy.value = true
  error.value = ''
  try {
    const { blob, filename } = await exportApi.download(props.nodeId, format.value)
    saveBlob(blob, filename)
    emit('done', true)
  } catch (e) {
    error.value = e instanceof ApiError ? e.detail || e.message : t('toast.error')
  } finally {
    busy.value = false
  }
}
