import { defineStore } from 'pinia'
import { computed, ref, watch } from 'vue'
import { searchApi } from '../api/endpoints.ts'
import type { SearchItem, SearchScope } from '../api/types.ts'
import { useTreeStore } from './tree.ts'

export const useSearchStore = defineStore('search', () => {
  const query = ref('')
  const scope = ref<SearchScope>('all')
  const inFolder = ref(false)
  const results = ref<SearchItem[]>([])
  const total = ref(0)
  const loading = ref(false)
  const failed = ref(false)

  const active = computed(() => query.value.trim().length > 0)
  const tooShort = computed(() => active.value && query.value.trim().length < 2)

  let timer: ReturnType<typeof setTimeout> | undefined
  let controller: AbortController | undefined

  async function run(): Promise<void> {
    controller?.abort()
    const q = query.value.trim()
    if (q.length < 2) {
      results.value = []
      total.value = 0
      loading.value = false
      return
    }
    controller = new AbortController()
    loading.value = true
    failed.value = false
    try {
      const folderId = inFolder.value ? useTreeStore().selectedFolderId : null
      const res = await searchApi.search(q, { scope: scope.value, folderId, limit: 50, signal: controller.signal })
      results.value = res.items
      total.value = res.total
    } catch (e) {
      if ((e as Error).name === 'AbortError') return // superseded by a newer query
      failed.value = true
      results.value = []
    } finally {
      loading.value = false
    }
  }

  watch([query, scope, inFolder], () => {
    clearTimeout(timer)
    timer = setTimeout(() => void run(), 200)
  })

  function clear(): void {
    query.value = ''
    results.value = []
    total.value = 0
  }

  return { query, scope, inFolder, results, total, loading, failed, active, tooShort, clear }
})
