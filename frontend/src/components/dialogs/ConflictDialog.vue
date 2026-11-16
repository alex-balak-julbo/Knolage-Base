<script setup lang="ts">
import { t } from '../../i18n'
import DialogShell from './DialogShell.vue'

const emit = defineEmits<{ (e: 'done', value?: 'reload' | 'overwrite'): void }>()
</script>

<template>
  <DialogShell :title="t('conflict.title')" @cancel="emit('done')">
    <p class="text-sm">{{ t('conflict.msg') }}</p>
    <div class="flex flex-col gap-2">
      <button type="button" class="btn" @click="emit('done', 'reload')">{{ t('conflict.reload') }}</button>
      <button type="button" class="btn-primary" @click="emit('done', 'overwrite')">{{ t('conflict.overwrite') }}</button>
      <button type="button" class="btn" @click="emit('done')">{{ t('dlg.cancel') }}</button>
    </div>
  </DialogShell>
</template>
