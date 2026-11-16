
import { onMounted, ref } from 'vue'
import { t } from '../../i18n'
import DialogShell from './DialogShell.vue'

const props = defineProps<{
  title: string
  label?: string
  initial?: string
  placeholder?: string
  hint?: string
  confirmLabel?: string
  allowEmpty?: boolean
}>()
const emit = defineEmits<{ (e: 'done', value?: string): void }>()

const value = ref(props.initial ?? '')
const input = ref<HTMLInputElement | null>(null)
onMounted(() => {
  input.value?.focus()
  input.value?.select()
})

function submit() {
  const v = value.value.trim()
  if (!v && !props.allowEmpty) return
  emit('done', v)
}
