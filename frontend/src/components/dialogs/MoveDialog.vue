<script setup lang="ts">
import { computed } from 'vue'
import { t } from '../../i18n'
import { canMove } from '../../lib/tree'
import { useTreeStore } from '../../stores/tree'
import DialogShell from './DialogShell.vue'

const props = defineProps<{ nodeId: string }>()
const emit = defineEmits<{ (e: 'done', value?: { parentId: string | null }): void }>()
const tree = useTreeStore()

interface Item {
  id: string | null
  label: string
  depth: number
  ok: boolean
}

// Every folder, indented, greyed out when the server would refuse the move.
const items = computed<Item[]>(() => {
  const ix = tree.index
  const out: Item[] = [{ id: null, label: '📚 ' + t('crumb.root'), depth: 0, ok: canMove(ix, props.nodeId, null).ok }]
  const walk = (parentId: string | null, depth: number) => {
    for (const id of ix.children.get(parentId) ?? []) {
      const n = ix.byId.get(id)!
      if (n.type !== 'folder') continue
      out.push({ id: n.id, label: '📁 ' + (n.name || t('page.untitled')), depth, ok: canMove(ix, props.nodeId, n.id).ok })
      walk(n.id, depth + 1)
    }
  }
  walk(null, 1)
  return out
})
const node = computed(() => tree.byId(props.nodeId))
</script>

<template>
  <DialogShell :title="t('dlg.moveTo', { name: node?.name ?? '' })" @cancel="emit('done')">
    <div class="flex max-h-80 flex-col gap-0.5 overflow-auto" role="listbox">
      <button
        v-for="it in items"
        :key="it.id ?? 'root'"
        type="button"
        role="option"
        :disabled="!it.ok || it.id === node?.parent_id"
        class="rounded-lg px-3 py-1.5 text-left text-sm enabled:hover:bg-accent-soft disabled:opacity-40"
        :style="{ paddingLeft: 12 + it.depth * 16 + 'px' }"
        @click="emit('done', { parentId: it.id })"
      >
        {{ it.label }}
      </button>
    </div>
    <div class="flex justify-end">
      <button type="button" class="btn" @click="emit('done')">{{ t('dlg.cancel') }}</button>
    </div>
  </DialogShell>
</template>
