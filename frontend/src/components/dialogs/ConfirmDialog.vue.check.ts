
import { onMounted, ref } from 'vue'
import { t } from '../../i18n'
import DialogShell from './DialogShell.vue'

defineProps<{ title: string; message: string; confirmLabel: string; danger?: boolean }>()
const emit = defineEmits<{ (e: 'done', value: boolean): void }>()
const confirmBtn = ref<HTMLButtonElement | null>(null)
onMounted(() => confirmBtn.value?.focus())
