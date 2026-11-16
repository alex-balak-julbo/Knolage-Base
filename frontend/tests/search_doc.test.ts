import assert from 'node:assert/strict'
import { describe, it } from 'node:test'
import { emptyDoc, linkIds, normalizeHref, sanitizeForSave, type DocNode } from '../src/lib/doc.ts'
import { findMatches, fold, splitHighlight } from '../src/lib/search.ts'

describe('search highlighting', () => {
  it('folds accents and case', () => {
    assert.equal(fold('Procédure ÉTÉ'), 'procedure ete')
  })
  it('returns offsets into the original text', () => {
    const text = 'La Procédure de la procedure'
    const m = findMatches(text, 'PROCEDURE')
    assert.equal(m.length, 2)
    assert.deepEqual(m.map(([a, b]) => text.slice(a, b)), ['Procédure', 'procedure'])
  })
  it('handles empty queries and no match', () => {
    assert.deepEqual(findMatches('abc', '  '), [])
    assert.deepEqual(findMatches('abc', 'z'), [])
  })
  it('splits into segments and merges overlapping ranges', () => {
    assert.deepEqual(splitHighlight('abcdef', [[1, 3], [2, 4]]), [
      { text: 'a', hit: false }, { text: 'bcd', hit: true }, { text: 'ef', hit: false },
    ])
    assert.deepEqual(splitHighlight('abc', [[0, 99]]), [{ text: 'abc', hit: true }])
    assert.deepEqual(splitHighlight('abc', []), [{ text: 'abc', hit: false }])
  })
})

const UID = '11111111-1111-4111-8111-111111111111'
describe('doc helpers', () => {
  it('collects pageLink ids in order', () => {
    const d: DocNode = { type: 'doc', content: [
      { type: 'pageLink', attrs: { pageId: 'a' } },
      { type: 'paragraph' },
      { type: 'pageLink', attrs: { pageId: 'b' } },
    ] }
    assert.deepEqual(linkIds(d), ['a', 'b'])
    assert.deepEqual(linkIds(null), [])
  })

  it('normalises links', () => {
    assert.equal(normalizeHref(' https://a.io '), 'https://a.io')
    assert.equal(normalizeHref('example.com/x'), 'https://example.com/x')
    assert.equal(normalizeHref('mailto:a@b.io'), 'mailto:a@b.io')
    assert.equal(normalizeHref('javascript:alert(1)'), null)
    assert.equal(normalizeHref('//evil.com'), null)
    assert.equal(normalizeHref('nodots'), null)
    assert.equal(normalizeHref('   '), null)
  })

  it('sanitizeForSave removes what the server would reject, and keeps the text', () => {
    const d: DocNode = { type: 'doc', content: [
      { type: 'paragraph', content: [
        { type: 'text', text: 'bad', marks: [{ type: 'link', attrs: { href: 'javascript:alert(1)' } }, { type: 'bold' }] },
        { type: 'text', text: 'ok', marks: [{ type: 'link', attrs: { href: 'https://x.io' } }] },
        { type: 'text', text: 'only-bad-link', marks: [{ type: 'link', attrs: { href: '/relative' } }] },
      ] },
      { type: 'image', attrs: { src: 'https://evil.example/x.png' } },
      { type: 'image', attrs: { src: `/api/v1/assets/${UID}`, alt: 'logo' } },
      { type: 'pageLink', attrs: {} },
    ] }
    const out = sanitizeForSave(d)
    const para = out.content![0].content!
    assert.deepEqual(para[0].marks, [{ type: 'bold' }])
    assert.equal(para[1].marks![0].type, 'link')
    assert.equal('marks' in para[2], false)
    assert.deepEqual(out.content!.map((c) => c.type), ['paragraph', 'image'])
    assert.equal(d.content!.length, 4) // input untouched
  })

  it('never returns an empty document', () => {
    assert.deepEqual(sanitizeForSave({ type: 'doc', content: [{ type: 'image', attrs: { src: 'x' } }] }), emptyDoc())
  })
})
