<script setup lang="ts">
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
</script>

<template>
  <!-- keyed so a new dialog never inherits the state of the previous one -->
  <component :is="registry[ui.dialog.kind] as any" v-if="ui.dialog" :key="ui.dialog.id" v-bind="ui.dialog.props" @done="ui.close($event)" />
</template>
