
import { t } from '../../i18n'
import DialogShell from './DialogShell.vue'

const emit = defineEmits<{ (e: 'done', value?: 'reload' | 'overwrite'): void }>()
