<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { t } from '../../i18n'
import DialogShell from './DialogShell.vue'

defineProps<{ title: string; message: string; confirmLabel: string; danger?: boolean }>()
const emit = defineEmits<{ (e: 'done', value: boolean): void }>()
const confirmBtn = ref<HTMLButtonElement | null>(null)
onMounted(() => confirmBtn.value?.focus())
</script>

<template>
  <DialogShell :title="title" @cancel="emit('done', false)">
    <p class="text-sm">{{ message }}</p>
    <div class="mt-2 flex justify-end gap-2">
      <button type="button" class="btn" @click="emit('done', false)">{{ t('dlg.cancel') }}</button>
      <button ref="confirmBtn" type="button" :class="danger ? 'btn-danger' : 'btn-primary'" @click="emit('done', true)">{{ confirmLabel }}</button>
    </div>
  </DialogShell>
</template>
