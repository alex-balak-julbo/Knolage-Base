import { onBeforeUnmount, onMounted, ref, type Ref } from 'vue'
import { planDrop, zoneFromRatio, type Zone } from '../lib/dnd.ts'
import { MAX_FOLDER_DEPTH } from '../lib/tree.ts'
import { useTreeStore } from '../stores/tree.ts'

export interface DropTarget {
  id: string | null // null = the root zone
  zone: Zone
}

/**
 * Native HTML5 drag & drop for the tree, with event delegation on the container.
 * Rows carry data-node-id; the root drop area carries data-root-zone.
 * (Touch screens do not fire HTML5 drag events: "Move to…" is the alternative there.)
 */
export function useTreeDnd(container: Ref<HTMLElement | null>) {
  const tree = useTreeStore()
  const dragId = ref<string | null>(null)
  const drop = ref<DropTarget | null>(null)
  let hoverId: string | null = null
  let hoverTimer: ReturnType<typeof setTimeout> | undefined

  const clearHover = () => {
    clearTimeout(hoverTimer)
    hoverId = null
  }
  const reset = () => {
    dragId.value = null
    drop.value = null
    clearHover()
  }
  const setDrop = (next: DropTarget | null) => {
    const cur = drop.value
    if (cur?.id === next?.id && cur?.zone === next?.zone) return
    drop.value = next
  }

  function evaluate(e: DragEvent) {
    const dragged = dragId.value ? tree.byId(dragId.value) : undefined
    if (!dragged) return null
    const target = e.target as HTMLElement
    const row = target.closest<HTMLElement>('[data-node-id]')
    if (row) {
      const node = tree.byId(row.dataset.nodeId)
      if (!node) return null
      const rect = row.getBoundingClientRect()
      const zone = zoneFromRatio((e.clientY - rect.top) / (rect.height || 1), dragged.type, node.type)
      return { targetId: node.id, zone, plan: planDrop(tree.index, dragged.id, node.id, zone, MAX_FOLDER_DEPTH) }
    }
    if (target.closest('[data-root-zone]')) {
      return { targetId: null, zone: 'inside' as Zone, plan: planDrop(tree.index, dragged.id, null, 'inside', MAX_FOLDER_DEPTH) }
    }
    return null
  }

  function autoScroll(e: DragEvent) {
    const el = container.value
    if (!el) return
    const r = el.getBoundingClientRect()
    if (e.clientY < r.top + 40) el.scrollTop -= 12
    else if (e.clientY > r.bottom - 40) el.scrollTop += 12
  }

  function onDragStart(e: DragEvent) {
    const row = (e.target as HTMLElement).closest<HTMLElement>('[data-node-id]')
    if (!row || !e.dataTransfer) return
    dragId.value = row.dataset.nodeId ?? null
    e.dataTransfer.setData('text/plain', dragId.value ?? '')
    e.dataTransfer.effectAllowed = 'move'
  }

  function onDragOver(e: DragEvent) {
    if (!dragId.value) return
    autoScroll(e)
    const ev = evaluate(e)
    if (!ev || !ev.plan.valid) {
      if (e.dataTransfer) e.dataTransfer.dropEffect = 'none'
      setDrop(null)
      clearHover()
      return
    }
    e.preventDefault() // allows the drop
    if (e.dataTransfer) e.dataTransfer.dropEffect = 'move'
    setDrop({ id: ev.targetId, zone: ev.zone })
    // open a collapsed folder after hovering it for 700 ms
    const node = ev.targetId ? tree.byId(ev.targetId) : undefined
    const collapsed = node && ev.zone === 'inside' && !tree.expanded[node.id] && (node.type === 'folder' || (tree.index.children.get(node.id)?.length ?? 0) > 0)
    if (collapsed && node) {
      if (hoverId !== node.id) {
        clearHover()
        hoverId = node.id
        hoverTimer = setTimeout(() => tree.toggle(node.id, true), 700)
      }
    } else {
      clearHover()
    }
  }

  function onDrop(e: DragEvent) {
    if (!dragId.value) return
    const ev = evaluate(e)
    const id = dragId.value
    reset()
    if (!ev || !ev.plan.valid) return
    e.preventDefault()
    const { parentId, beforeId, afterId } = ev.plan
    void tree.move(id, { parentId, beforeId, afterId })
  }

  function onDragLeave(e: DragEvent) {
    if (!container.value?.contains(e.relatedTarget as Node | null)) setDrop(null)
  }

  const events: [string, (e: DragEvent) => void][] = [
    ['dragstart', onDragStart], ['dragover', onDragOver], ['drop', onDrop], ['dragleave', onDragLeave], ['dragend', reset],
  ]
  onMounted(() => events.forEach(([n, h]) => container.value?.addEventListener(n, h as EventListener)))
  onBeforeUnmount(() => {
    events.forEach(([n, h]) => container.value?.removeEventListener(n, h as EventListener))
    clearHover()
  })

  return { dragId, drop }
}
