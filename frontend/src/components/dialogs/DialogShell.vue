<script setup lang="ts">
defineProps<{ title: string }>()
const emit = defineEmits<{ (e: 'cancel'): void }>()
const titleId = `dlg-${Math.random().toString(36).slice(2, 8)}`
</script>

<template>
  <div class="fixed inset-0 z-50 flex items-center justify-center bg-black/45 p-4" @mousedown.self="emit('cancel')" @keydown.esc.stop="emit('cancel')">
    <div role="dialog" aria-modal="true" :aria-labelledby="titleId" class="flex max-h-[90vh] w-full max-w-md flex-col gap-3 overflow-auto rounded-xl border border-line bg-panel p-5 shadow-xl">
      <h2 :id="titleId" class="text-lg font-semibold">{{ title }}</h2>
      <slot />
    </div>
  </div>
</template>
