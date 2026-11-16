
defineProps<{ title: string }>()
const emit = defineEmits<{ (e: 'cancel'): void }>()
const titleId = `dlg-${Math.random().toString(36).slice(2, 8)}`
