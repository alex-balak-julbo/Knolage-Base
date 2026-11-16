
import { onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { t } from '../../i18n'
import { useTemplatesStore } from '../../stores/templates'
import { useTreeStore } from '../../stores/tree'
import { useUiStore } from '../../stores/ui'
import SidebarTree from '../tree/SidebarTree.vue'

const ui = useUiStore()
const tree = useTreeStore()
const templates = useTemplatesStore()
const route = useRoute()

onMounted(async () => {
  try {
    await Promise.all([tree.load(), templates.load()])
  } catch (e) {
    ui.toastError(e)
  }
})
watch(() => route.fullPath, () => (ui.sidebarOpen = false))
