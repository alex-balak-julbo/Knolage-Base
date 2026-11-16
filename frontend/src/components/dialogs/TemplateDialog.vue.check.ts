
import { onMounted, ref } from 'vue'
import { t } from '../../i18n'
import { useTemplatesStore } from '../../stores/templates'
import DialogShell from './DialogShell.vue'

const props = defineProps<{ parentName: string; title?: string }>()
const emit = defineEmits<{ (e: 'done', value?: { templateId: string; name: string }): void }>()

const templates = useTemplatesStore()
const name = ref('')
const selected = ref(templates.items.find((x) => x.id === 'blank')?.id ?? templates.items[0]?.id ?? 'blank')
const input = ref<HTMLInputElement | null>(null)
onMounted(() => input.value?.focus())

function submit() {
  emit('done', { templateId: selected.value, name: name.value.trim() })
}
