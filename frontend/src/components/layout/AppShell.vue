<script setup lang="ts">
import { onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { t } from '../../i18n'
import { useTemplatesStore } from '../../stores/templates'
import { useTreeStore } from '../../stores/tree'
import { useUiStore } from '../../stores/ui'
import SidebarTree from '../tree/SidebarTree.vue'

const ui = useUiStore()
const tree = useTreeStore()
const templates = useTemplatesStore()
const route = useRoute()

onMounted(async () => {
  try {
    await Promise.all([tree.load(), templates.load()])
  } catch (e) {
    ui.toastError(e)
  }
})
watch(() => route.fullPath, () => (ui.sidebarOpen = false))
</script>

<template>
  <div class="flex h-dvh overflow-hidden bg-canvas text-ink" style="padding-top: env(safe-area-inset-top)">
    <div class="fixed inset-y-0 left-0 z-30 w-80 max-w-[85vw] transition-transform md:static md:translate-x-0" :class="ui.sidebarOpen ? 'translate-x-0' : '-translate-x-full'">
      <SidebarTree />
    </div>
    <div v-if="ui.sidebarOpen" class="fixed inset-0 z-20 bg-black/40 md:hidden" @click="ui.sidebarOpen = false" />
    <main class="flex min-w-0 flex-1 flex-col">
      <header class="flex items-center gap-2 border-b border-line px-3 py-2 md:hidden">
        <button type="button" class="btn" :aria-label="t('nav.menu')" @click="ui.sidebarOpen = true">☰</button>
        <span class="font-semibold">📚 {{ t('app.title') }}</span>
      </header>
      <div class="min-h-0 flex-1 overflow-auto"><slot /></div>
    </main>
  </div>
</template>
