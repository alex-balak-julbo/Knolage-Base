"""TipTap/ProseMirror JSON validation, text extraction and pageLink helpers.

The server never stores raw HTML: documents are validated against a strict
whitelist of nodes/marks and rebuilt from allowed fields only.
"""
import copy
import json
import re
from urllib.parse import urlparse

UUID_RE = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
ASSET_RE = re.compile(r"^/api/v1/assets/([0-9a-fA-F-]{36})$")

ALLOWED_CHILDREN = {
    "doc": {"paragraph", "heading", "bulletList", "orderedList", "pageLink", "image"},
    "paragraph": {"text", "hardBreak", "image"},
    "heading": {"text", "hardBreak"},
    "bulletList": {"listItem"},
    "orderedList": {"listItem"},
    "listItem": {"paragraph", "bulletList", "orderedList"},
}
LEAVES = {"text", "hardBreak", "image", "pageLink"}
MARKS = {"bold", "italic", "link"}
LINK_SCHEMES = {"http", "https", "mailto"}


class ContentError(ValueError):
    def __init__(self, path, msg):
        super().__init__(f"{path}: {msg}")
        self.path, self.msg = path, msg


def empty_doc():
    return {"type": "doc", "content": [{"type": "paragraph"}]}


def _int(v, path, lo, hi):
    if isinstance(v, bool) or not isinstance(v, int) or not (lo <= v <= hi):
        raise ContentError(path, f"must be an integer between {lo} and {hi}")
    return v


def _clean(node, parent, depth, path, ctx):
    if depth > ctx["max_depth"]:
        raise ContentError(path, "document nested too deeply")
    if not isinstance(node, dict):
        raise ContentError(path, "node must be an object")
    t = node.get("type")
    if not isinstance(t, str) or (t not in ALLOWED_CHILDREN and t not in LEAVES):
        raise ContentError(path, f"unknown node type {t!r}")
    if t == "doc" and parent is not None:
        raise ContentError(path, "'doc' is only allowed at the root")
    if parent is not None and t not in ALLOWED_CHILDREN[parent]:
        raise ContentError(path, f"{t!r} is not allowed inside {parent!r}")
    out = {"type": t}
    attrs = node.get("attrs") or {}
    if not isinstance(attrs, dict):
        raise ContentError(path, "attrs must be an object")

    if t == "heading":
        out["attrs"] = {"level": _int(attrs.get("level"), path + ".attrs.level", 1, 2)}
    elif t == "orderedList" and "start" in attrs:
        out["attrs"] = {"start": _int(attrs["start"], path + ".attrs.start", 1, 100000)}
    elif t == "image":
        src = attrs.get("src")
        m = ASSET_RE.match(src) if isinstance(src, str) else None
        if not m or not UUID_RE.match(m.group(1)):
            raise ContentError(path + ".attrs.src", "image must reference /api/v1/assets/<uuid>")
        if ctx["asset_ok"] and not ctx["asset_ok"](m.group(1)):
            raise ContentError(path + ".attrs.src", "unknown asset")
        a = {"src": src}
        if isinstance(attrs.get("alt"), str):
            a["alt"] = attrs["alt"][:500]
        out["attrs"] = a
    elif t == "pageLink":
        pid = attrs.get("pageId")
        if not isinstance(pid, str) or not UUID_RE.match(pid):
            raise ContentError(path + ".attrs.pageId", "pageId must be a uuid")
        if ctx["page_ok"] and not ctx["page_ok"](pid):
            raise ContentError(path + ".attrs.pageId", "unknown page")
        out["attrs"] = {"pageId": pid}
    elif t == "text":
        text = node.get("text")
        if not isinstance(text, str) or not text or len(text) > 100000:
            raise ContentError(path + ".text", "text must be a non-empty string (max 100000 chars)")
        out["text"] = text
        marks = node.get("marks") or []
        if not isinstance(marks, list):
            raise ContentError(path + ".marks", "marks must be a list")
        seen, clean = set(), []
        for i, m in enumerate(marks):
            mp = f"{path}.marks[{i}]"
            if not isinstance(m, dict) or m.get("type") not in MARKS:
                raise ContentError(mp, f"unknown mark {m.get('type') if isinstance(m, dict) else m!r}")
            if m["type"] in seen:
                continue
            seen.add(m["type"])
            if m["type"] == "link":
                href = (m.get("attrs") or {}).get("href")
                if not isinstance(href, str) or urlparse(href.strip()).scheme.lower() not in LINK_SCHEMES:
                    raise ContentError(mp + ".attrs.href", "link must use http, https or mailto")
                clean.append({"type": "link", "attrs": {"href": href.strip()}})
            else:
                clean.append({"type": m["type"]})
        if clean:
            out["marks"] = clean

    if t in LEAVES:
        if node.get("content"):
            raise ContentError(path, f"{t!r} cannot have children")
        return out
    children = node.get("content") or []
    if not isinstance(children, list):
        raise ContentError(path + ".content", "content must be a list")
    if children:
        out["content"] = [_clean(c, t, depth + 1, f"{path}.content[{i}]", ctx) for i, c in enumerate(children)]
    return out


def validate_doc(doc, *, asset_ok=None, page_ok=None, max_bytes=2 * 1024 * 1024, max_depth=10):
    """Return a sanitized copy of ``doc`` or raise ContentError."""
    if not isinstance(doc, dict) or doc.get("type") != "doc":
        raise ContentError("$", "root must be an object of type 'doc'")
    try:
        size = len(json.dumps(doc, ensure_ascii=False).encode("utf-8"))
    except (TypeError, ValueError):
        raise ContentError("$", "document is not valid JSON")
    if size > max_bytes:
        raise ContentError("$", f"document too large (max {max_bytes} bytes)")
    ctx = {"asset_ok": asset_ok, "page_ok": page_ok, "max_depth": max_depth}
    return _clean(doc, None, 0, "$", ctx)


def _inline_text(node):
    parts = []
    for ch in node.get("content", []):
        if ch["type"] == "text":
            parts.append(ch["text"])
        elif ch["type"] == "hardBreak":
            parts.append(" ")
        elif ch["type"] == "image":
            parts.append(ch.get("attrs", {}).get("alt", ""))
    return "".join(parts)


def extract_text(doc):
    """Plain text of a document, one line per paragraph/heading/list item."""
    lines = []

    def walk(n):
        t = n["type"]
        if t in ("paragraph", "heading"):
            s = _inline_text(n).strip()
            if s:
                lines.append(s)
        else:
            for c in n.get("content", []):
                walk(c)

    if doc:
        walk(doc)
    return "\n".join(lines)


def link_ids(doc):
    """pageIds of all pageLink nodes, in document order."""
    found = []

    def walk(n):
        if n.get("type") == "pageLink":
            found.append(n["attrs"]["pageId"])
        for c in n.get("content", []) or []:
            walk(c)

    if doc:
        walk(doc)
    return found


def remove_links(doc, ids):
    ids = set(ids)
    doc = copy.deepcopy(doc)

    def walk(n):
        if "content" in n:
            n["content"] = [c for c in n["content"] if not (c.get("type") == "pageLink" and c["attrs"]["pageId"] in ids)]
            for c in n["content"]:
                walk(c)

    walk(doc)
    if not doc.get("content"):
        doc["content"] = [{"type": "paragraph"}]
    return doc


def append_link(doc, page_id):
    doc = copy.deepcopy(doc) if doc else empty_doc()
    doc.setdefault("content", []).append({"type": "pageLink", "attrs": {"pageId": page_id}})
    return doc
