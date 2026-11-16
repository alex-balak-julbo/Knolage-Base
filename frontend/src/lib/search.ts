// Accent/case-insensitive matching with offsets that point into the ORIGINAL text.

export function foldWithMap(s: string): { folded: string; map: number[] } {
  let folded = ''
  const map: number[] = []
  let i = 0
  for (const ch of s) {
    const stripped = ch.normalize('NFKD').replace(/\p{M}/gu, '').toLowerCase()
    for (const c of stripped) {
      folded += c
      for (let k = 0; k < c.length; k++) map.push(i)
    }
    i += ch.length
  }
  return { folded, map }
}

export const fold = (s: string): string => foldWithMap(s).folded

export type Range = [number, number]

export function findMatches(text: string, query: string): Range[] {
  const q = fold(query.trim())
  if (!q) return []
  const { folded, map } = foldWithMap(text)
  const out: Range[] = []
  let from = 0
  for (;;) {
    const at = folded.indexOf(q, from)
    if (at < 0) break
    out.push([map[at], map[at + q.length - 1] + 1])
    from = at + q.length
  }
  return out
}

export interface Segment {
  text: string
  hit: boolean
}

/** Split text into plain/highlighted segments; ranges may be unsorted or overlapping. */
export function splitHighlight(text: string, ranges: Range[]): Segment[] {
  const sorted = ranges
    .map(([a, b]) => [Math.max(0, a), Math.min(text.length, b)] as Range)
    .filter(([a, b]) => b > a)
    .sort((x, y) => x[0] - y[0])
  const merged: Range[] = []
  for (const r of sorted) {
    const last = merged[merged.length - 1]
    if (last && r[0] <= last[1]) last[1] = Math.max(last[1], r[1])
    else merged.push([r[0], r[1]])
  }
  const out: Segment[] = []
  let pos = 0
  for (const [a, b] of merged) {
    if (a > pos) out.push({ text: text.slice(pos, a), hit: false })
    out.push({ text: text.slice(a, b), hit: true })
    pos = b
  }
  if (pos < text.length) out.push({ text: text.slice(pos), hit: false })
  return out
}
