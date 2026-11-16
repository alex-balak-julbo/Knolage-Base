"""Search: candidate retrieval is delegated to the repo; ranking and snippets live here."""
from ..domain import FOLDER, iso
from ..errors import unprocessable
from ..textutil import fold, fold_with_map

SCOPES = ("all", "title", "content")


def _occurrences(text, q):
    folded, idx = fold_with_map(text)
    fq = fold(q)
    out, start = [], 0
    while fq:
        i = folded.find(fq, start)
        if i < 0:
            break
        out.append((idx[i], idx[i + len(fq) - 1] + 1))
        start = i + max(len(fq), 1)
    return out


def snippet(text, q, before=40, after=60):
    """Return (snippet, [[start, end], ...]) with offsets relative to the snippet."""
    if not text:
        return "", []
    occ = _occurrences(text, q)
    if not occ:
        return text[: before + after].replace("\n", " "), []
    s0 = max(0, occ[0][0] - before)
    e0 = min(len(text), occ[0][1] + after)
    raw = text[s0:e0]
    prefix = "…" if s0 > 0 else ""
    suffix = "…" if e0 < len(text) else ""
    flat = raw.replace("\n", " ")
    matches = [[a - s0 + len(prefix), b - s0 + len(prefix)] for a, b in occ if a >= s0 and b <= e0]
    return prefix + flat + suffix, matches


class SearchService:
    def __init__(self, repo, tree):
        self.repo, self.tree = repo, tree

    def _path(self, node):
        out, cur = [], node.parent_id
        while cur:
            p = self.repo.get_node(cur)
            if not p:
                break
            out.insert(0, {"id": p.id, "name": p.name, "type": p.type})
            cur = p.parent_id
        return out

    def search(self, user, q, scope="all", folder_id=None, template_id=None, status=None, limit=20, offset=0):
        q = (q or "").strip()
        if not q:
            raise unprocessable("q is required", errors={"q": "required"})
        if scope not in SCOPES:
            raise unprocessable(f"scope must be one of {SCOPES}", errors={"scope": "invalid"})
        restrict = None
        if folder_id:
            f = self.tree.get(user, folder_id)
            if f.type != FOLDER:
                raise unprocessable("folder_id must reference a folder", errors={"folder_id": "invalid"})
            restrict = set(self.repo.descendant_ids(folder_id))
        cands = self.repo.search_candidates(user.id, q, scope, restrict, template_id)
        fq, hits = fold(q), []
        for n in cands:
            if status and n.props.get("status") != status:
                continue
            title_hit = fq in fold(n.name)
            content_hit = fq in fold(n.search_text)
            if (scope == "title" and not title_hit) or (scope == "content" and not content_hit):
                continue
            if not (title_hit or content_hit):
                continue
            hits.append((0 if title_hit else 1, n, title_hit, content_hit))
        hits.sort(key=lambda h: (h[0], -h[1].updated_at.timestamp(), h[1].id))
        total = len(hits)
        items = []
        for _, n, t_hit, c_hit in hits[offset: offset + limit]:
            sn, matches = snippet(n.search_text, q) if scope != "title" else snippet(n.search_text, "")
            items.append({"id": n.id, "name": n.name, "icon": n.icon, "template_id": n.template_id,
                          "path": self._path(n), "snippet": sn, "matches": matches,
                          "title_match": t_hit, "updated_at": iso(n.updated_at)})
        return items, total
