<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { t } from '../../i18n'
import DialogShell from './DialogShell.vue'

const props = defineProps<{
  title: string
  label?: string
  initial?: string
  placeholder?: string
  hint?: string
  confirmLabel?: string
  allowEmpty?: boolean
}>()
const emit = defineEmits<{ (e: 'done', value?: string): void }>()

const value = ref(props.initial ?? '')
const input = ref<HTMLInputElement | null>(null)
onMounted(() => {
  input.value?.focus()
  input.value?.select()
})

function submit() {
  const v = value.value.trim()
  if (!v && !props.allowEmpty) return
  emit('done', v)
}
</script>

<template>
  <DialogShell :title="title" @cancel="emit('done')">
    <form class="flex flex-col gap-2" @submit.prevent="submit">
      <label v-if="label" class="text-sm text-muted" for="prompt-input">{{ label }}</label>
      <input id="prompt-input" ref="input" v-model="value" class="input" :placeholder="placeholder" autocomplete="off" />
      <p v-if="hint" class="text-xs text-muted">{{ hint }}</p>
      <div class="mt-2 flex justify-end gap-2">
        <button type="button" class="btn" @click="emit('done')">{{ t('dlg.cancel') }}</button>
        <button type="submit" class="btn-primary">{{ confirmLabel ?? t('dlg.ok') }}</button>
      </div>
    </form>
  </DialogShell>
</template>
