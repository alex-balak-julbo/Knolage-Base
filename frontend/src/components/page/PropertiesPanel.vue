<script setup lang="ts">
import { computed, ref } from 'vue'
import type { NodeFull } from '../../api/types'
import { usePageStore } from '../../stores/page'
import { useTemplatesStore } from '../../stores/templates'

const props = defineProps<{ node: NodeFull }>()
const page = usePageStore()
const templates = useTemplatesStore()

const fields = computed(() => templates.byId.get(props.node.template_id ?? '')?.props_schema ?? [])
// Local copy: the inputs must not be overwritten by the server echo of an older save.
// The parent re-creates this component (key) whenever the page is reloaded.
const values = ref<Record<string, string>>({ ...(props.node.props ?? {}) })

function update(key: string, value: string) {
  values.value[key] = value
  page.schedule({ props: { [key]: value } })
}
</script>

<template>
  <div v-if="fields.length" class="my-3 divide-y divide-line border-y border-line">
    <div v-for="f in fields" :key="f.key" class="grid items-center gap-2 py-1 sm:grid-cols-[12rem_1fr]">
      <label :for="'prop-' + f.key" class="text-sm text-muted">{{ f.label }}</label>
      <select
        v-if="f.type === 'select'"
        :id="'prop-' + f.key"
        class="rounded-md bg-transparent px-2 py-1 text-sm hover:bg-accent-soft"
        :value="values[f.key] ?? ''"
        @change="update(f.key, ($event.target as HTMLSelectElement).value)"
      >
        <option value="">—</option>
        <option v-for="o in f.options" :key="o" :value="o">{{ o }}</option>
      </select>
      <input
        v-else
        :id="'prop-' + f.key"
        class="rounded-md bg-transparent px-2 py-1 text-sm hover:bg-accent-soft focus:bg-accent-soft"
        :value="values[f.key] ?? ''"
        maxlength="2000"
        autocomplete="off"
        @input="update(f.key, ($event.target as HTMLInputElement).value)"
      />
    </div>
  </div>
</template>
