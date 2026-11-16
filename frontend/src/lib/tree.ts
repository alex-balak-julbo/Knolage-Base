// Pure tree logic (no Vue): indexing, flattening and the same move rules the server enforces.

export type NodeType = 'folder' | 'page'

export interface TreeNode {
  id: string
  type: NodeType
  parent_id: string | null
  name: string
  icon: string | null
  position: number
  template_id: string | null
  version: number
  updated_at: string
  status?: string
}

export interface TreeIndex {
  byId: Map<string, TreeNode>
  children: Map<string | null, string[]>
}

export interface Row {
  node: TreeNode
  depth: number
  expandable: boolean
  expanded: boolean
}

export type MoveCheck = { ok: true } | { ok: false; code: 'not_found' | 'cycle' | 'invalid_parent' | 'max_depth' }

export const MAX_FOLDER_DEPTH = 8

/** Display order: folders first, then pages; then manual position, then id. */
export function compareNodes(a: TreeNode, b: TreeNode): number {
  if (a.type !== b.type) return a.type === 'folder' ? -1 : 1
  return a.position - b.position || (a.id < b.id ? -1 : a.id > b.id ? 1 : 0)
}

export function buildIndex(nodes: TreeNode[]): TreeIndex {
  const byId = new Map(nodes.map((n) => [n.id, n] as const))
  const children = new Map<string | null, string[]>()
  for (const n of nodes) {
    const key = n.parent_id && byId.has(n.parent_id) ? n.parent_id : null // orphans fall back to the root
    const list = children.get(key)
    if (list) list.push(n.id)
    else children.set(key, [n.id])
  }
  for (const ids of children.values()) ids.sort((x, y) => compareNodes(byId.get(x)!, byId.get(y)!))
  return { byId, children }
}

export function childrenOf(ix: TreeIndex, parentId: string | null): TreeNode[] {
  return (ix.children.get(parentId) ?? []).map((id) => ix.byId.get(id)!)
}

export function flatten(ix: TreeIndex, expanded: Record<string, boolean>): Row[] {
  const rows: Row[] = []
  const walk = (parentId: string | null, depth: number) => {
    for (const node of childrenOf(ix, parentId)) {
      const hasKids = (ix.children.get(node.id)?.length ?? 0) > 0
      const expandable = node.type === 'folder' || hasKids
      const isOpen = expandable && expanded[node.id] === true
      rows.push({ node, depth, expandable, expanded: isOpen })
      if (isOpen) walk(node.id, depth + 1)
    }
  }
  walk(null, 0)
  return rows
}

/** Ancestors from the root down to (and excluding) the node. */
export function ancestors(ix: TreeIndex, id: string): TreeNode[] {
  const chain: TreeNode[] = []
  const seen = new Set<string>([id])
  let cur = ix.byId.get(id)?.parent_id ?? null
  while (cur && !seen.has(cur)) {
    seen.add(cur)
    const n = ix.byId.get(cur)
    if (!n) break
    chain.unshift(n)
    cur = n.parent_id
  }
  return chain
}

/** True when `id` is `ancestorId` itself or lives anywhere below it. */
export function isInside(ix: TreeIndex, id: string, ancestorId: string): boolean {
  if (id === ancestorId) return true
  return ancestors(ix, id).some((n) => n.id === ancestorId)
}

export function descendantIds(ix: TreeIndex, id: string): string[] {
  const out: string[] = []
  const walk = (pid: string) => {
    for (const cid of ix.children.get(pid) ?? []) {
      out.push(cid)
      walk(cid)
    }
  }
  walk(id)
  return out
}

/** Number of folder levels from the root down to (and including) parentId. */
export function folderDepth(ix: TreeIndex, parentId: string | null): number {
  if (!parentId) return 0
  const chain = [...ancestors(ix, parentId), ix.byId.get(parentId)!]
  return chain.filter((n) => n?.type === 'folder').length
}

/** Folder levels strictly below the node. */
export function folderHeight(ix: TreeIndex, id: string): number {
  let best = 0
  for (const cid of ix.children.get(id) ?? []) {
    if (ix.byId.get(cid)?.type === 'folder') best = Math.max(best, 1 + folderHeight(ix, cid))
  }
  return best
}

export function canMove(ix: TreeIndex, id: string, newParentId: string | null, maxDepth = MAX_FOLDER_DEPTH): MoveCheck {
  const n = ix.byId.get(id)
  if (!n) return { ok: false, code: 'not_found' }
  if (newParentId === id) return { ok: false, code: 'cycle' }
  if (newParentId !== null) {
    const p = ix.byId.get(newParentId)
    if (!p) return { ok: false, code: 'not_found' }
    if (n.type === 'folder' && p.type === 'page') return { ok: false, code: 'invalid_parent' }
    if (isInside(ix, newParentId, id)) return { ok: false, code: 'cycle' }
  }
  if (n.type === 'folder' && folderDepth(ix, newParentId) + 1 + folderHeight(ix, id) > maxDepth) {
    return { ok: false, code: 'max_depth' }
  }
  return { ok: true }
}

/** Position the server would assign (floats are fine client-side; the tree is reloaded after a move). */
export function optimisticPosition(
  ix: TreeIndex,
  id: string,
  parentId: string | null,
  beforeId?: string | null,
  afterId?: string | null,
): number {
  const sibs = (ix.children.get(parentId) ?? [])
    .filter((x) => x !== id)
    .map((x) => ix.byId.get(x)!)
    .sort((a, b) => a.position - b.position || (a.id < b.id ? -1 : 1))
  const ref = beforeId ?? afterId
  let index = sibs.length
  if (ref) {
    const i = sibs.findIndex((s) => s.id === ref)
    if (i >= 0) index = beforeId ? i : i + 1
  }
  const prev = index > 0 ? sibs[index - 1].position : null
  const next = index < sibs.length ? sibs[index].position : null
  if (prev === null && next === null) return 1024
  if (prev === null) return next! - 1024
  if (next === null) return prev + 1024
  return (prev + next) / 2
}

/** The sibling that currently follows `id` in raw position order (used to undo a move exactly). */
export function nextSiblingByPosition(ix: TreeIndex, id: string): string | null {
  const n = ix.byId.get(id)
  if (!n) return null
  const key = n.parent_id && ix.byId.has(n.parent_id) ? n.parent_id : null
  const sibs = (ix.children.get(key) ?? [])
    .map((x) => ix.byId.get(x)!)
    .sort((a, b) => a.position - b.position || (a.id < b.id ? -1 : 1))
  const i = sibs.findIndex((s) => s.id === id)
  return i >= 0 && i < sibs.length - 1 ? sibs[i + 1].id : null
}
