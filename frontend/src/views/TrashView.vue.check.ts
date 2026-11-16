
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
