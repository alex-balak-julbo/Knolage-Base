<script setup lang="ts">
import { computed } from 'vue'
import { slashState } from './extensions/SlashCommand'

const style = computed(() => {
  const r = slashState.rect
  if (!r) return { display: 'none' }
  const left = Math.max(8, Math.min(r.left, innerWidth - 232))
  const below = r.bottom + 6
  const top = below + 280 > innerHeight ? Math.max(8, r.top - 6 - Math.min(280, slashState.items.length * 36 + 8)) : below
  return { left: left + 'px', top: top + 'px' }
})
</script>

<template>
  <Teleport to="body">
    <div v-if="slashState.open && slashState.items.length" role="listbox" class="fixed z-50 max-h-72 w-56 overflow-auto rounded-xl border border-line bg-panel p-1 shadow-xl" :style="style">
      <!-- mousedown.prevent keeps the editor focused while clicking an entry -->
      <button
        v-for="(item, i) in slashState.items"
        :key="item.id"
        type="button"
        role="option"
        :aria-selected="i === slashState.index"
        class="flex w-full items-center gap-2 rounded-lg px-3 py-1.5 text-left text-sm"
        :class="i === slashState.index ? 'bg-accent-soft' : 'hover:bg-accent-soft'"
        @mousedown.prevent="slashState.select(item)"
        @mouseenter="slashState.index = i"
      >
        <span class="w-6 text-center text-muted" aria-hidden="true">{{ item.icon }}</span>{{ item.label }}
      </button>
    </div>
  </Teleport>
</template>
