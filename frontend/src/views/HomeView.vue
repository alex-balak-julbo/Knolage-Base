<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import { useNodeActions } from '../composables/useNodeActions'
import { t } from '../i18n'
import { ancestors } from '../lib/tree'
import { useTemplatesStore } from '../stores/templates'
import { useTreeStore } from '../stores/tree'

const tree = useTreeStore()
const templates = useTemplatesStore()
const actions = useNodeActions()

const recent = computed(() =>
  tree.nodes
    .filter((n) => n.type === 'page')
    .sort((a, b) => (a.updated_at < b.updated_at ? 1 : -1))
    .slice(0, 8)
    .map((n) => ({ node: n, path: ancestors(tree.index, n.id).map((a) => a.name).join(' › ') })),
)
</script>

<template>
  <div class="mx-auto w-full max-w-3xl px-4 py-8 md:px-8">
    <h1 class="text-2xl font-bold">{{ t('home.welcome') }}</h1>
    <p class="mt-1 text-muted">{{ t('home.hint') }}</p>
    <div class="mt-4 flex gap-2">
      <button type="button" class="btn" @click="actions.newFolder(null)">{{ t('nav.newFolder') }}</button>
      <button type="button" class="btn-primary" @click="actions.newPage(null)">{{ t('nav.newPage') }}</button>
    </div>
    <h2 class="mt-8 text-sm font-semibold uppercase tracking-wide text-muted">{{ t('home.recent') }}</h2>
    <p v-if="tree.loaded && !recent.length" class="mt-2 text-sm text-muted">{{ t('home.none') }}</p>
    <ul class="mt-2 divide-y divide-line">
      <li v-for="r in recent" :key="r.node.id">
        <RouterLink :to="{ name: 'page', params: { id: r.node.id } }" class="block rounded-lg px-2 py-2 hover:bg-accent-soft">
          {{ r.node.icon || templates.icon(r.node.template_id) }} {{ r.node.name || t('page.untitled') }}
          <span v-if="r.path" class="block text-xs text-muted">{{ r.path }}</span>
        </RouterLink>
      </li>
    </ul>
  </div>
</template>
