import { useRoute, useRouter } from 'vue-router'
import { t } from '../i18n.ts'
import { descendantIds, type TreeNode } from '../lib/tree.ts'
import { useTemplatesStore } from '../stores/templates.ts'
import { useTreeStore } from '../stores/tree.ts'
import { useUiStore } from '../stores/ui.ts'

/** User-level commands shared by the sidebar, the page header and the home view. */
export function useNodeActions() {
  const tree = useTreeStore()
  const ui = useUiStore()
  const templates = useTemplatesStore()
  const router = useRouter()
  const route = useRoute()

  async function newFolder(parentId: string | null): Promise<void> {
    const name = await ui.prompt({ title: t('dlg.folderName'), label: t('dlg.folderName'), confirmLabel: t('dlg.create') })
    if (!name) return
    try {
      const folder = await tree.create({ type: 'folder', name, parent_id: parentId })
      tree.select(folder.id)
    } catch (e) {
      ui.toastError(e)
    }
  }

  async function newPage(parentId: string | null): Promise<void> {
    const parent = tree.byId(parentId)
    const picked = await ui.pickTemplate({ parentName: parent?.name ?? t('crumb.root') })
    if (!picked) return
    try {
      const name = picked.name.trim() || templates.byId.get(picked.templateId)?.name || t('page.untitled')
      const page = await tree.create({ type: 'page', name, parent_id: parentId, template_id: picked.templateId })
      await router.push({ name: 'page', params: { id: page.id }, query: { new: '1' } })
    } catch (e) {
      ui.toastError(e)
    }
  }

  async function rename(node: TreeNode): Promise<void> {
    const name = await ui.prompt({ title: t('dlg.rename'), label: t('dlg.rename'), initial: node.name, confirmLabel: t('dlg.ok') })
    if (!name || name === node.name) return
    try {
      await tree.rename(node.id, name)
    } catch (e) {
      ui.toastError(e)
    }
  }

  async function remove(node: TreeNode): Promise<void> {
    const n = descendantIds(tree.index, node.id).length
    const ok = await ui.confirm({
      title: t('confirm.deleteTitle'),
      message: n ? t('confirm.deleteMany', { name: node.name, n }) : t('confirm.deleteOne', { name: node.name }),
      confirmLabel: t('menu.delete'),
      danger: true,
    })
    if (!ok) return
    try {
      const res = await tree.remove(node.id)
      if (typeof route.params.id === 'string' && res.ids.includes(route.params.id)) await router.push('/')
      ui.toast(t('toast.deleted', { name: node.name }), { label: t('toast.undo'), run: () => tree.restore(node.id) })
    } catch (e) {
      ui.toastError(e)
    }
  }

  async function moveTo(node: TreeNode): Promise<void> {
    const target = await ui.pickFolder({ nodeId: node.id })
    if (target) await tree.move(node.id, { parentId: target.parentId })
  }

  const exportNode = (node: TreeNode) => ui.exportNode({ nodeId: node.id })

  return { newFolder, newPage, rename, remove, moveTo, exportNode }
}
