import assert from 'node:assert/strict'
import { describe, it } from 'node:test'
import {
  ancestors, buildIndex, canMove, descendantIds, flatten, folderDepth, folderHeight, isInside, nextSiblingByPosition,
  optimisticPosition,
  type TreeNode,
} from '../src/lib/tree.ts'

let seq = 0
const n = (id: string, type: 'folder' | 'page', parent: string | null = null, position = ++seq * 1024): TreeNode => ({
  id, type, parent_id: parent, name: id, icon: null, position, template_id: null, version: 1, updated_at: '',
})

//  A (folder)
//   ├─ B (folder)
//   │   └─ C (folder)
//   │       └─ p1 (page) ── sub (page)
//   └─ p2 (page)
//  R (root page)
const nodes = [
  n('A', 'folder'), n('B', 'folder', 'A'), n('C', 'folder', 'B'), n('p1', 'page', 'C'), n('sub', 'page', 'p1'),
  n('p2', 'page', 'A', 1), n('R', 'page'),
]
const ix = buildIndex(nodes)

describe('tree index', () => {
  it('sorts folders before pages, then by position', () => {
    assert.deepEqual(ix.children.get('A'), ['B', 'p2'])
    assert.deepEqual(ix.children.get(null), ['A', 'R'])
  })

  it('treats orphans as root nodes', () => {
    const i = buildIndex([n('x', 'page', 'ghost')])
    assert.deepEqual(i.children.get(null), ['x'])
  })

  it('flattens only expanded branches, with depth', () => {
    assert.deepEqual(flatten(ix, {}).map((r) => r.node.id), ['A', 'R'])
    const rows = flatten(ix, { A: true, B: true, C: true, p1: true })
    assert.deepEqual(rows.map((r) => [r.node.id, r.depth]), [
      ['A', 0], ['B', 1], ['C', 2], ['p1', 3], ['sub', 4], ['p2', 1], ['R', 0],
    ])
    assert.equal(rows[0].expandable && rows[0].expanded, true)
    assert.equal(flatten(ix, {}).find((r) => r.node.id === 'R')!.expandable, false)
  })

  it('ancestors, isInside, descendants', () => {
    assert.deepEqual(ancestors(ix, 'sub').map((x) => x.id), ['A', 'B', 'C', 'p1'])
    assert.equal(isInside(ix, 'sub', 'B'), true)
    assert.equal(isInside(ix, 'B', 'B'), true)
    assert.equal(isInside(ix, 'A', 'B'), false)
    assert.deepEqual(descendantIds(ix, 'B').sort(), ['C', 'p1', 'sub'])
  })

  it('folder depth and height', () => {
    assert.equal(folderDepth(ix, null), 0)
    assert.equal(folderDepth(ix, 'C'), 3)
    assert.equal(folderDepth(ix, 'p1'), 3) // pages do not count
    assert.equal(folderHeight(ix, 'A'), 2)
    assert.equal(folderHeight(ix, 'C'), 0)
  })
})

describe('canMove (mirrors the server)', () => {
  it('allows legal moves', () => {
    assert.deepEqual(canMove(ix, 'p2', 'C'), { ok: true })
    assert.deepEqual(canMove(ix, 'R', null), { ok: true })
    assert.deepEqual(canMove(ix, 'R', 'p2'), { ok: true }) // page under page = sub-page
  })
  it('rejects cycles', () => {
    assert.deepEqual(canMove(ix, 'A', 'A'), { ok: false, code: 'cycle' })
    assert.deepEqual(canMove(ix, 'A', 'C'), { ok: false, code: 'cycle' })
    assert.deepEqual(canMove(ix, 'p1', 'sub'), { ok: false, code: 'cycle' })
  })
  it('rejects a folder under a page', () => {
    assert.deepEqual(canMove(ix, 'B', 'p2'), { ok: false, code: 'invalid_parent' })
  })
  it('rejects unknown nodes', () => {
    assert.deepEqual(canMove(ix, 'zzz', null), { ok: false, code: 'not_found' })
    assert.deepEqual(canMove(ix, 'R', 'zzz'), { ok: false, code: 'not_found' })
  })
  it('enforces the maximum folder depth for whole subtrees', () => {
    assert.equal(canMove(ix, 'A', null, 3).ok, true) // A, B, C = 3 levels
    const deep = buildIndex([...nodes, n('X', 'folder')])
    assert.deepEqual(canMove(deep, 'X', 'C', 3), { ok: false, code: 'max_depth' })
    assert.deepEqual(canMove(deep, 'X', 'B', 3), { ok: true })
    assert.deepEqual(canMove(deep, 'A', 'X', 3), { ok: false, code: 'max_depth' })
  })
})

describe('optimisticPosition', () => {
  const sib = buildIndex([n('f', 'folder', null, 0), n('a', 'page', 'f', 1024), n('b', 'page', 'f', 2048), n('c', 'page', 'f', 3072)])
  it('appends, prepends and inserts between neighbours', () => {
    assert.equal(optimisticPosition(sib, 'z', 'f'), 4096)
    assert.equal(optimisticPosition(sib, 'z', 'f', 'a'), 0)
    assert.equal(optimisticPosition(sib, 'z', 'f', null, 'a'), 1536)
    assert.equal(optimisticPosition(sib, 'z', 'f', 'c'), 2560)
    assert.equal(optimisticPosition(sib, 'z', 'empty'), 1024)
  })
  it('ignores the moved node itself', () => {
    assert.equal(optimisticPosition(sib, 'b', 'f', null, 'a'), 2048) // between a(1024) and c(3072)
  })
})

describe('nextSiblingByPosition', () => {
  const ix2 = buildIndex([n('f', 'folder', null, 0), n('a', 'page', 'f', 1024), n('b', 'page', 'f', 2048), n('c', 'folder', 'f', 3072)])
  it('follows raw position order, not the folders-first display order', () => {
    assert.equal(nextSiblingByPosition(ix2, 'a'), 'b')
    assert.equal(nextSiblingByPosition(ix2, 'b'), 'c')
    assert.equal(nextSiblingByPosition(ix2, 'c'), null)
    assert.equal(nextSiblingByPosition(ix2, 'missing'), null)
  })
})
