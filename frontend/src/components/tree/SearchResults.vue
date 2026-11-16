<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import { t } from '../../i18n'
import { findMatches, splitHighlight } from '../../lib/search'
import { useSearchStore } from '../../stores/search'
import { useTemplatesStore } from '../../stores/templates'
import { useUiStore } from '../../stores/ui'

const search = useSearchStore()
const templates = useTemplatesStore()
const ui = useUiStore()
const q = computed(() => search.query.trim())
const countLabel = computed(() => (search.total === 1 ? t('search.one') : t('search.many', { n: search.total })))
</script>

<template>
  <div class="flex-1 overflow-auto px-2 pb-3" aria-live="polite">
    <p v-if="search.tooShort" class="px-2 py-1 text-xs text-muted">{{ t('search.tooShort') }}</p>
    <p v-else-if="search.failed" class="px-2 py-1 text-xs text-danger">{{ t('search.error') }}</p>
    <p v-else-if="!search.loading && !search.results.length" class="px-2 py-1 text-xs text-muted">{{ t('search.none') }}</p>
    <p v-else-if="search.results.length" class="px-2 py-1 text-xs text-muted">{{ countLabel }}</p>

    <RouterLink
      v-for="item in search.results"
      :key="item.id"
      :to="{ name: 'page', params: { id: item.id } }"
      class="block rounded-lg px-2 py-2 text-sm hover:bg-accent-soft"
      @click="ui.sidebarOpen = false"
    >
      <span>{{ item.icon || templates.icon(item.template_id) }} </span>
      <template v-for="(seg, i) in splitHighlight(item.name || t('page.untitled'), findMatches(item.name, q))" :key="i">
        <mark v-if="seg.hit" class="rounded bg-yellow-200 px-0.5 text-black">{{ seg.text }}</mark>
        <template v-else>{{ seg.text }}</template>
      </template>
      <span class="block truncate text-xs text-muted">{{ item.path.map((p) => p.name).join(' › ') || t('crumb.root') }}</span>
      <span v-if="item.snippet" class="block text-xs text-muted">
        <template v-for="(seg, i) in splitHighlight(item.snippet, item.matches)" :key="i">
          <mark v-if="seg.hit" class="rounded bg-yellow-200 px-0.5 text-black">{{ seg.text }}</mark>
          <template v-else>{{ seg.text }}</template>
        </template>
      </span>
    </RouterLink>
  </div>
</template>
