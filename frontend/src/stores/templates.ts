import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { templatesApi } from '../api/endpoints.ts'
import type { Template } from '../api/types.ts'

export const useTemplatesStore = defineStore('templates', () => {
  const items = ref<Template[]>([])
  const byId = computed(() => new Map(items.value.map((x) => [x.id, x] as const)))

  async function load(): Promise<void> {
    items.value = await templatesApi.list()
  }
  const icon = (id: string | null): string => (id && byId.value.get(id)?.icon) || '📄'

  return { items, byId, load, icon }
})
