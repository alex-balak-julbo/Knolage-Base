
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import { useNodeActions } from '../composables/useNodeActions'
import { t } from '../i18n'
import { ancestors } from '../lib/tree'
import { useTemplatesStore } from '../stores/templates'
import { useTreeStore } from '../stores/tree'

const tree = useTreeStore()
const templates = useTemplatesStore()
const actions = useNodeActions()

const recent = computed(() =>
  tree.nodes
    .filter((n) => n.type === 'page')
    .sort((a, b) => (a.updated_at < b.updated_at ? 1 : -1))
    .slice(0, 8)
    .map((n) => ({ node: n, path: ancestors(tree.index, n.id).map((a) => a.name).join(' › ') })),
)
