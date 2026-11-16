<script setup lang="ts">
import { t } from '../../i18n'
import { useUiStore } from '../../stores/ui'

const ui = useUiStore()
</script>

<template>
  <div class="pointer-events-none fixed inset-x-0 bottom-4 z-[60] flex flex-col items-center gap-2 px-4" style="padding-bottom: env(safe-area-inset-bottom)" role="status" aria-live="polite">
    <div v-for="toast in ui.toasts" :key="toast.id" class="pointer-events-auto flex max-w-md items-center gap-3 rounded-xl bg-ink px-4 py-2 text-sm text-canvas shadow-lg">
      <span>{{ toast.message }}</span>
      <button v-if="toast.action" type="button" class="font-semibold underline" @click="toast.action.run(); ui.dismissToast(toast.id)">{{ toast.action.label }}</button>
      <button type="button" class="opacity-70 hover:opacity-100" :aria-label="t('dlg.close')" @click="ui.dismissToast(toast.id)">✕</button>
    </div>
  </div>
</template>
