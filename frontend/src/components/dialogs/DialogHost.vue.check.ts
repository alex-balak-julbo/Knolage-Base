
import { useUiStore } from '../../stores/ui'
import ConfirmDialog from './ConfirmDialog.vue'
import ConflictDialog from './ConflictDialog.vue'
import ExportDialog from './ExportDialog.vue'
import MoveDialog from './MoveDialog.vue'
import PromptDialog from './PromptDialog.vue'
import TemplateDialog from './TemplateDialog.vue'

const ui = useUiStore()
const registry = {
  prompt: PromptDialog,
  confirm: ConfirmDialog,
  template: TemplateDialog,
  move: MoveDialog,
  export: ExportDialog,
  conflict: ConflictDialog,
} as const
