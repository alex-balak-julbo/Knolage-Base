<script setup lang="ts">
import { computed } from 'vue'
import { t } from '../../i18n'
import type { Row } from '../../lib/tree'
import { useTemplatesStore } from '../../stores/templates'

const props = defineProps<{
  row: Row
  selected: boolean
  tabbable: boolean
  dragging: boolean
  drop: 'before' | 'inside' | 'after' | null
}>()
const emit = defineEmits<{
  (e: 'open'): void
  (e: 'toggle'): void
  (e: 'focus'): void
  (e: 'menu', ev: MouseEvent): void
  (e: 'add', ev: MouseEvent): void
}>()

const templates = useTemplatesStore()
const icon = computed(() => props.row.node.icon || (props.row.node.type === 'folder' ? '📁' : templates.icon(props.row.node.template_id)))
</script>

<template>
  <div
    role="treeitem"
    draggable="true"
    class="tree-row group flex cursor-pointer select-none items-center gap-1 rounded-md py-1 pr-1 text-sm hover:bg-accent-soft"
    :class="{ 'bg-accent-soft font-semibold': selected }"
    :style="{ paddingLeft: 4 + row.depth * 16 + 'px' }"
    :data-node-id="row.node.id"
    :data-drop="drop ?? undefined"
    :data-dragging="dragging ? 'true' : undefined"
    :aria-level="row.depth + 1"
    :aria-expanded="row.expandable ? row.expanded : undefined"
    :aria-selected="selected"
    :tabindex="tabbable ? 0 : -1"
    @click="emit('open')"
    @focus="emit('focus')"
    @contextmenu.prevent="emit('menu', $event)"
  >
    <button v-if="row.expandable" type="button" tabindex="-1" class="icon-btn text-xs" :aria-label="row.expanded ? '▾' : '▸'" @click.stop="emit('toggle')">
      {{ row.expanded ? '▾' : '▸' }}
    </button>
    <span v-else class="w-6 shrink-0" />
    <span aria-hidden="true">{{ icon }}</span>
    <span class="min-w-0 flex-1 truncate">{{ row.node.name || t('page.untitled') }}</span>
    <span class="flex shrink-0 gap-0.5 opacity-0 focus-within:opacity-100 group-hover:opacity-100 [@media(hover:none)]:opacity-100">
      <button v-if="row.node.type === 'folder'" type="button" tabindex="-1" class="icon-btn" :aria-label="t('tree.add')" :title="t('tree.add')" @click.stop="emit('add', $event)">＋</button>
      <button type="button" tabindex="-1" class="icon-btn" :aria-label="t('tree.more')" :title="t('tree.more')" @click.stop="emit('menu', $event)">⋯</button>
    </span>
  </div>
</template>
