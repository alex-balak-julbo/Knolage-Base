// TipTap/ProseMirror JSON helpers. Mirrors the backend whitelist so a page never gets stuck unsaveable.

export interface DocNode {
  type: string
  attrs?: Record<string, unknown>
  content?: DocNode[]
  marks?: { type: string; attrs?: Record<string, unknown> }[]
  text?: string
}

export const ASSET_SRC = /^\/api\/v1\/assets\/[0-9a-fA-F-]{36}$/
const LINK_SCHEMES = /^(https?|mailto):/i

export function emptyDoc(): DocNode {
  return { type: 'doc', content: [{ type: 'paragraph' }] }
}

export function isSafeHref(href: string): boolean {
  return LINK_SCHEMES.test(href.trim())
}

/** Normalise what the user typed: add https:// to bare domains, reject unsafe schemes. */
export function normalizeHref(raw: string): string | null {
  const v = raw.trim()
  if (!v) return null
  if (isSafeHref(v)) return v
  if (/^[a-z][a-z0-9+.-]*:/i.test(v) || v.startsWith('//')) return null
  return /^[^\s/]+\.[^\s/]+/.test(v) ? 'https://' + v : null
}

export function linkIds(doc: DocNode | null | undefined): string[] {
  const out: string[] = []
  const walk = (n: DocNode) => {
    if (n.type === 'pageLink' && typeof n.attrs?.pageId === 'string') out.push(n.attrs.pageId)
    n.content?.forEach(walk)
  }
  if (doc) walk(doc)
  return out
}

/** Drop what the server would reject: unsafe links (text is kept), foreign images, broken page links. */
export function sanitizeForSave(doc: DocNode): DocNode {
  const clean = (n: DocNode): DocNode | null => {
    if (n.type === 'image' && !(typeof n.attrs?.src === 'string' && ASSET_SRC.test(n.attrs.src))) return null
    if (n.type === 'pageLink' && typeof n.attrs?.pageId !== 'string') return null
    const out: DocNode = { ...n }
    if (n.marks) {
      const marks = n.marks.filter((m) => m.type !== 'link' || isSafeHref(String(m.attrs?.href ?? '')))
      if (marks.length) out.marks = marks
      else delete out.marks
    }
    if (n.content) out.content = n.content.map(clean).filter((c): c is DocNode => c !== null)
    return out
  }
  const result = clean(doc) ?? emptyDoc()
  if (!result.content?.length) result.content = [{ type: 'paragraph' }]
  return result
}
