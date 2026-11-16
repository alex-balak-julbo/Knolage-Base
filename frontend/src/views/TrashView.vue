<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { trashApi } from '../api/endpoints'
import type { TrashItem } from '../api/types'
import { locale, t } from '../i18n'
import { useTemplatesStore } from '../stores/templates'
import { useTreeStore } from '../stores/tree'
import { useUiStore } from '../stores/ui'

const ui = useUiStore()
const tree = useTreeStore()
const templates = useTemplatesStore()
const items = ref<TrashItem[]>([])
const loading = ref(true)

async function refresh() {
  try {
    items.value = await trashApi.list()
  } catch (e) {
    ui.toastError(e)
  } finally {
    loading.value = false
  }
}
onMounted(refresh)

const fmt = (iso: string) => new Date(iso).toLocaleString(locale.value)

async function restore(item: TrashItem) {
  try {
    await tree.restore(item.id)
    ui.toast(t('toast.restored'))
    await refresh()
  } catch (e) {
    ui.toastError(e)
  }
}

async function purge(item: TrashItem) {
  const ok = await ui.confirm({ title: t('confirm.purgeTitle'), message: t('confirm.purgeMsg'), confirmLabel: t('trash.purge'), danger: true })
  if (!ok) return
  try {
    await trashApi.purge(item.id)
    await refresh()
  } catch (e) {
    ui.toastError(e)
  }
}

async function emptyAll() {
  const ok = await ui.confirm({ title: t('confirm.emptyTitle'), message: t('confirm.emptyMsg'), confirmLabel: t('trash.emptyAll'), danger: true })
  if (!ok) return
  try {
    await trashApi.empty()
    await refresh()
  } catch (e) {
    ui.toastError(e)
  }
}
</script>

<template>
  <div class="mx-auto w-full max-w-3xl px-4 py-8 md:px-8">
    <div class="flex items-center justify-between gap-2">
      <h1 class="text-2xl font-bold">🗑 {{ t('trash.title') }}</h1>
      <button v-if="items.length" type="button" class="btn" @click="emptyAll">{{ t('trash.emptyAll') }}</button>
    </div>
    <p v-if="!loading && !items.length" class="mt-4 text-muted">{{ t('trash.empty') }}</p>
    <ul class="mt-4 divide-y divide-line">
      <li v-for="item in items" :key="item.id" class="flex flex-wrap items-center gap-2 py-2">
        <span aria-hidden="true">{{ item.icon || (item.type === 'folder' ? '📁' : templates.icon(item.template_id)) }}</span>
        <span class="min-w-0 flex-1">
          <span class="block truncate">{{ item.name || t('page.untitled') }}</span>
          <span class="block text-xs text-muted">{{ t('trash.deletedOn', { date: fmt(item.deleted_at) }) }}</span>
        </span>
        <button type="button" class="btn" @click="restore(item)">{{ t('trash.restore') }}</button>
        <button type="button" class="btn" @click="purge(item)">{{ t('trash.purge') }}</button>
      </li>
    </ul>
  </div>
</template>
