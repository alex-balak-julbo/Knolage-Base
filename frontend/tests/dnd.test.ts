import assert from 'node:assert/strict'
import { describe, it } from 'node:test'
import { planDrop, zoneFromRatio } from '../src/lib/dnd.ts'
import { buildIndex, type TreeNode } from '../src/lib/tree.ts'

const n = (id: string, type: 'folder' | 'page', parent: string | null = null, position = 1024): TreeNode => ({
  id, type, parent_id: parent, name: id, icon: null, position, template_id: null, version: 1, updated_at: '',
})
const ix = buildIndex([
  n('A', 'folder'), n('B', 'folder', 'A'), n('p1', 'page', 'A'), n('p2', 'page', 'B'), n('R', 'page'),
])

describe('zones', () => {
  it('splits a row in 25 / 50 / 25', () => {
    assert.equal(zoneFromRatio(0.1, 'page', 'folder'), 'before')
    assert.equal(zoneFromRatio(0.5, 'page', 'folder'), 'inside')
    assert.equal(zoneFromRatio(0.9, 'page', 'folder'), 'after')
    assert.equal(zoneFromRatio(0.25, 'page', 'page'), 'inside')
    assert.equal(zoneFromRatio(0.75, 'page', 'page'), 'inside')
  })
  it('never offers "inside a page" to a folder', () => {
    assert.equal(zoneFromRatio(0.5, 'folder', 'page'), 'after')
    assert.equal(zoneFromRatio(0.4, 'folder', 'page'), 'before')
  })
})

describe('planDrop', () => {
  it('drops a page into a folder (appended)', () => {
    assert.deepEqual(planDrop(ix, 'R', 'B', 'inside'), { valid: true, parentId: 'B' })
  })
  it('inserts before / after a sibling under the sibling parent', () => {
    assert.deepEqual(planDrop(ix, 'R', 'p1', 'before'), { valid: true, parentId: 'A', beforeId: 'p1' })
    assert.deepEqual(planDrop(ix, 'R', 'p2', 'after'), { valid: true, parentId: 'B', afterId: 'p2' })
    assert.deepEqual(planDrop(ix, 'p2', 'A', 'before'), { valid: true, parentId: null, beforeId: 'A' })
  })
  it('drops on the root zone', () => {
    assert.deepEqual(planDrop(ix, 'p2', null, 'inside'), { valid: true, parentId: null })
  })
  it('a page dropped inside a page becomes its sub-page', () => {
    assert.deepEqual(planDrop(ix, 'R', 'p1', 'inside'), { valid: true, parentId: 'p1' })
  })
  it('refuses to drop on itself, into its own subtree, or a folder under a page', () => {
    assert.equal(planDrop(ix, 'A', 'A', 'inside').reason, 'self')
    assert.equal(planDrop(ix, 'A', 'B', 'inside').reason, 'cycle')
    assert.equal(planDrop(ix, 'A', 'p2', 'before').reason, 'cycle') // p2 lives inside A/B
    assert.equal(planDrop(ix, 'B', 'p1', 'inside').reason, 'invalid_parent')
    assert.equal(planDrop(ix, 'B', 'p1', 'inside').valid, false)
  })
  it('respects the folder depth limit', () => {
    assert.equal(planDrop(ix, 'A', 'R', 'before', 2).valid, true) // A + B = 2 levels
    assert.equal(planDrop(ix, 'A', 'R', 'before', 1).reason, 'max_depth')
    assert.equal(planDrop(ix, 'B', 'A', 'inside', 1).reason, 'max_depth')
  })
})
