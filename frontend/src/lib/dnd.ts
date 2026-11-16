// Drag & drop decisions for the tree, kept free of DOM/Vue so they can be unit-tested.
import { canMove, type MoveCheck, type NodeType, type TreeIndex } from './tree.ts'

export type Zone = 'before' | 'inside' | 'after'

/** Top 25 % = before, bottom 25 % = after, middle = inside. A folder cannot go inside a page. */
export function zoneFromRatio(ratio: number, dragType: NodeType, targetType: NodeType): Zone {
  if (dragType === 'folder' && targetType === 'page') return ratio < 0.5 ? 'before' : 'after'
  if (ratio < 0.25) return 'before'
  if (ratio > 0.75) return 'after'
  return 'inside'
}

export interface DropPlan {
  valid: boolean
  reason?: Extract<MoveCheck, { ok: false }>['code'] | 'self'
  parentId: string | null
  beforeId?: string
  afterId?: string
}

/** targetId === null means the root drop zone (append at the end of the root). */
export function planDrop(ix: TreeIndex, dragId: string, targetId: string | null, zone: Zone, maxDepth?: number): DropPlan {
  if (targetId === null) return finish(ix, dragId, { valid: true, parentId: null }, maxDepth)
  if (targetId === dragId) return { valid: false, reason: 'self', parentId: null }
  const target = ix.byId.get(targetId)
  if (!target) return { valid: false, reason: 'not_found', parentId: null }
  if (zone === 'inside') return finish(ix, dragId, { valid: true, parentId: target.id }, maxDepth)
  const plan: DropPlan = { valid: true, parentId: target.parent_id }
  if (zone === 'before') plan.beforeId = target.id
  else plan.afterId = target.id
  return finish(ix, dragId, plan, maxDepth)
}

function finish(ix: TreeIndex, dragId: string, plan: DropPlan, maxDepth?: number): DropPlan {
  const check = canMove(ix, dragId, plan.parentId, maxDepth)
  return check.ok ? plan : { ...plan, valid: false, reason: check.code }
}
