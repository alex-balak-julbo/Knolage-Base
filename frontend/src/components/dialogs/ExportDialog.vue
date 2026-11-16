<script setup lang="ts">
import { computed, ref } from 'vue'
import { ApiError } from '../../api/client'
import { exportApi } from '../../api/endpoints'
import { t } from '../../i18n'
import { saveBlob } from '../../lib/download'
import { useTreeStore } from '../../stores/tree'
import DialogShell from './DialogShell.vue'

const props = defineProps<{ nodeId: string }>()
const emit = defineEmits<{ (e: 'done', value?: boolean): void }>()

const tree = useTreeStore()
const node = computed(() => tree.byId(props.nodeId))
const format = ref<'md' | 'html' | 'txt' | 'zip'>(node.value?.type === 'folder' ? 'zip' : 'md')
const busy = ref(false)
const error = ref('')
const formats = [
  { id: 'md', label: 'Markdown (.md)' },
  { id: 'html', label: 'HTML (.html)' },
  { id: 'txt', label: 'Texte (.txt)' },
  { id: 'zip', label: 'ZIP' },
] as const

async function download() {
  busy.value = true
  error.value = ''
  try {
    const { blob, filename } = await exportApi.download(props.nodeId, format.value)
    saveBlob(blob, filename)
    emit('done', true)
  } catch (e) {
    error.value = e instanceof ApiError ? e.detail || e.message : t('toast.error')
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <DialogShell :title="t('dlg.export', { name: node?.name ?? '' })" @cancel="emit('done')">
    <fieldset class="flex flex-col gap-1">
      <label v-for="f in formats" :key="f.id" class="flex items-center gap-2 text-sm">
        <input v-model="format" type="radio" name="export-format" :value="f.id" />
        {{ f.label }}
      </label>
    </fieldset>
    <p v-if="format === 'zip'" class="text-xs text-muted">{{ t('dlg.zipHint') }}</p>
    <p v-if="error" class="text-sm text-danger" role="alert">{{ error }}</p>
    <div class="flex justify-end gap-2">
      <button type="button" class="btn" @click="emit('done')">{{ t('dlg.cancel') }}</button>
      <button type="button" class="btn-primary" :disabled="busy" @click="download">{{ t('dlg.download') }}</button>
    </div>
  </DialogShell>
</template>
