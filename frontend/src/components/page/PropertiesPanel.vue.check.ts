
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
