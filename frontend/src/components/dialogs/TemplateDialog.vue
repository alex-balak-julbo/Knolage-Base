<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { t } from '../../i18n'
import { useTemplatesStore } from '../../stores/templates'
import DialogShell from './DialogShell.vue'

const props = defineProps<{ parentName: string; title?: string }>()
const emit = defineEmits<{ (e: 'done', value?: { templateId: string; name: string }): void }>()

const templates = useTemplatesStore()
const name = ref('')
const selected = ref(templates.items.find((x) => x.id === 'blank')?.id ?? templates.items[0]?.id ?? 'blank')
const input = ref<HTMLInputElement | null>(null)
onMounted(() => input.value?.focus())

function submit() {
  emit('done', { templateId: selected.value, name: name.value.trim() })
}
</script>

<template>
  <DialogShell :title="props.title ?? t('dlg.newPage')" @cancel="emit('done')">
    <form class="flex flex-col gap-3" @submit.prevent="submit">
      <input ref="input" v-model="name" class="input" :placeholder="t('dlg.pageTitle')" autocomplete="off" />
      <p class="text-xs text-muted">{{ t('dlg.in', { name: parentName }) }} — {{ t('dlg.chooseTemplate') }}</p>
      <div class="grid grid-cols-2 gap-2" role="radiogroup">
        <button
          v-for="tpl in templates.items"
          :key="tpl.id"
          type="button"
          role="radio"
          :aria-checked="selected === tpl.id"
          class="rounded-lg border p-3 text-left text-sm hover:border-accent"
          :class="selected === tpl.id ? 'border-accent bg-accent-soft' : 'border-line bg-canvas'"
          @click="selected = tpl.id"
        >
          <span class="font-semibold">{{ tpl.icon }} {{ tpl.name }}</span>
          <span class="block text-xs text-muted">{{ tpl.description }}</span>
        </button>
      </div>
      <div class="flex justify-end gap-2">
        <button type="button" class="btn" @click="emit('done')">{{ t('dlg.cancel') }}</button>
        <button type="submit" class="btn-primary">{{ t('dlg.create') }}</button>
      </div>
    </form>
  </DialogShell>
</template>
