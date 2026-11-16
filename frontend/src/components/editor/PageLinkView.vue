<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { nodeViewProps, NodeViewWrapper } from '@tiptap/vue-3'
import { t } from '../../i18n'
import { useTemplatesStore } from '../../stores/templates'
import { useTreeStore } from '../../stores/tree'
import { useUiStore } from '../../stores/ui'

const props = defineProps(nodeViewProps)
const tree = useTreeStore()
const templates = useTemplatesStore()
const ui = useUiStore()
const router = useRouter()

const target = computed(() => tree.byId(props.node.attrs.pageId as string))

function open() {
  if (target.value) void router.push({ name: 'page', params: { id: target.value.id } })
}

// Removing the card moves the sub-page to the trash (the server does it when the page is saved).
async function remove() {
  const ok = await ui.confirm({
    title: t('confirm.deleteTitle'),
    message: t('confirm.subpage', { name: target.value?.name ?? '' }),
    confirmLabel: t('menu.delete'),
    danger: true,
  })
  if (ok) props.deleteNode()
}
</script>

<template>
  <NodeViewWrapper class="page-link" contenteditable="false">
    <div
      class="my-1 flex cursor-pointer items-center gap-2 rounded-lg border border-line bg-panel px-3 py-2 hover:border-accent"
      role="link"
      tabindex="0"
      @click="open"
      @keydown.enter.prevent="open"
    >
      <template v-if="target">
        <span aria-hidden="true">{{ target.icon || templates.icon(target.template_id) }}</span>
        <b class="min-w-0 flex-1 truncate">{{ target.name || t('page.untitled') }}</b>
      </template>
      <span v-else class="flex-1 text-muted">…</span>
      <button type="button" class="icon-btn" :aria-label="t('menu.delete')" :title="t('menu.delete')" @click.stop="remove">✕</button>
    </div>
  </NodeViewWrapper>
</template>
