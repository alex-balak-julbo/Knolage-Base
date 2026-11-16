"""Export pages/folders to Markdown, HTML, plain text, or a ZIP mirroring the tree."""
import base64
import io
import json
import zipfile
from dataclasses import dataclass
from html import escape

from ..domain import FOLDER, PAGE
from ..errors import unprocessable
from ..textutil import slugify
from . import content as C

MIME = {"md": "text/markdown; charset=utf-8", "html": "text/html; charset=utf-8",
        "txt": "text/plain; charset=utf-8", "zip": "application/zip"}


@dataclass
class Export:
    data: bytes
    filename: str
    mimetype: str


def _has_text(li):
    return bool(C.extract_text({"type": "doc", "content": [li]}).strip()) if li else False


class _Ctx:
    def __init__(self, repo, assets, user, fmt, mode, prefix="", yaml=False):
        self.repo, self.assets, self.user = repo, assets, user
        self.fmt, self.mode, self.prefix, self.yaml = fmt, mode, prefix, yaml
        self.used, self.stack = {}, []
        self.tpls = {}

    def tpl(self, tid):
        if tid not in self.tpls:
            self.tpls[tid] = self.repo.get_template(tid)
        return self.tpls[tid]

    # ---- inline ----
    def text(self, n):
        s = n["text"]
        marks = {m["type"]: m for m in n.get("marks", [])}
        f = self.fmt
        if f == "html":
            s = escape(s)
            if "bold" in marks: s = f"<strong>{s}</strong>"
            if "italic" in marks: s = f"<em>{s}</em>"
            if "link" in marks: s = f'<a href="{escape(marks["link"]["attrs"]["href"], quote=True)}" rel="noopener noreferrer">{s}</a>'
        elif f == "md":
            if "bold" in marks: s = f"**{s}**"
            if "italic" in marks: s = f"*{s}*"
            if "link" in marks: s = f'[{s}]({marks["link"]["attrs"]["href"]})'
        elif "link" in marks:
            s = f'{s} ({marks["link"]["attrs"]["href"]})'
        return s

    def image(self, n):
        a = n.get("attrs", {})
        alt = a.get("alt", "")
        if self.fmt == "txt":
            return f"[image: {alt}]" if alt else "[image]"
        m = C.ASSET_RE.match(a.get("src", ""))
        asset = self.repo.get_asset(m.group(1)) if m else None
        if asset is None:
            return escape(alt) if self.fmt == "html" else alt
        if self.mode == "assets":
            self.used[asset.id] = asset
            src = f"{self.prefix}assets/{asset.id}.{self.assets.ext(asset)}"
        else:
            src = f"data:{asset.mime_type};base64," + base64.b64encode(self.assets.read(asset)).decode()
        if self.fmt == "html":
            return f'<img src="{src}" alt="{escape(alt, quote=True)}">'
        return f"![{alt}]({src})"

    def inline(self, node):
        br = {"md": "  \n", "html": "<br>", "txt": "\n"}[self.fmt]
        out = []
        for ch in node.get("content", []):
            t = ch["type"]
            out.append(self.text(ch) if t == "text" else br if t == "hardBreak" else self.image(ch))
        return "".join(out)

    # ---- blocks ----
    def list_lines(self, n, ind=0):
        ordered, start = n["type"] == "orderedList", n.get("attrs", {}).get("start", 1)
        lines, k = [], 0
        for li in n.get("content", []):
            if not _has_text(li):
                continue
            marker = f"{start + k}. " if ordered else "- "
            k += 1
            first = True
            for ch in li.get("content", []):
                if ch["type"] == "paragraph":
                    s = self.inline(ch)
                    lines.append(" " * (ind if first else ind + len(marker)) + (marker if first else "") + s)
                    first = False
                else:
                    if first:
                        lines.append(" " * ind + marker.rstrip())
                        first = False
                    lines += self.list_lines(ch, ind + len(marker))
        return lines

    def list_html(self, n):
        tag = "ol" if n["type"] == "orderedList" else "ul"
        items = []
        for li in n.get("content", []):
            if not _has_text(li):
                continue
            inner = "".join(self.inline(c) if c["type"] == "paragraph" else self.list_html(c) for c in li.get("content", []))
            items.append(f"<li>{inner}</li>")
        return f"<{tag}>{''.join(items)}</{tag}>" if items else ""

    def blocks(self, doc, base, rendered):
        out = []
        for n in (doc or {}).get("content", []):
            t = n["type"]
            if t == "paragraph":
                s = self.inline(n)
                if s.strip():
                    out.append(f"<p>{s}</p>" if self.fmt == "html" else s)
            elif t == "heading":
                lvl, s = min(6, base + n["attrs"]["level"]), self.inline(n)
                out.append(f"<h{lvl}>{s}</h{lvl}>" if self.fmt == "html" else
                           ("#" * lvl + " " + s if self.fmt == "md" else s))
            elif t in ("bulletList", "orderedList"):
                s = self.list_html(n) if self.fmt == "html" else "\n".join(self.list_lines(n))
                if s:
                    out.append(s)
            elif t == "image":
                s = self.image(n)
                out.append(f"<p>{s}</p>" if self.fmt == "html" else s)
            elif t == "pageLink":
                pid = n["attrs"]["pageId"]
                child = self.repo.get_node(pid)
                if child and child.owner_id == self.user.id and pid not in self.stack:
                    rendered.add(pid)
                    out += self.page(child, min(6, base + 1))
        return out

    def title(self, name, lvl):
        if self.fmt == "html":
            return f"<h{lvl}>{escape(name)}</h{lvl}>"
        if self.fmt == "md":
            return "#" * lvl + " " + name
        return name + ("\n" + ("=" if lvl == 1 else "-") * len(name) if lvl <= 2 else "")

    def props(self, node):
        tpl = self.ctx_tpl(node)
        rows = [(f["label"], node.props[f["key"]]) for f in (tpl.props_schema if tpl else []) if node.props.get(f["key"])]
        if self.fmt == "html":
            return [f"<p><strong>{escape(l)} :</strong> {escape(v)}</p>" for l, v in rows]
        if self.fmt == "md":
            return [f"**{l} :** {v}" for l, v in rows]
        return [f"{l} : {v}" for l, v in rows]

    def ctx_tpl(self, node):
        return self.tpl(node.template_id) if node.template_id else None

    def page(self, node, lvl):
        self.stack.append(node.id)
        try:
            head = []
            if self.yaml:
                tpl = self.ctx_tpl(node)
                meta = {"title": node.name, "template": node.template_id}
                meta.update({f["key"]: node.props[f["key"]] for f in (tpl.props_schema if tpl else []) if node.props.get(f["key"])})
                head.append("---\n" + "\n".join(f"{k}: {json.dumps(v, ensure_ascii=False)}" for k, v in meta.items()) + "\n---")
                body = [self.title(node.name, lvl)]
            else:
                body = [self.title(node.name, lvl)] + self.props(node)
            rendered = set()
            body += self.blocks(node.content, lvl, rendered)
            for ch in self.repo.children(node.id, self.user.id):  # sub-pages without a pageLink
                if ch.type == PAGE and ch.id not in rendered and ch.id not in self.stack:
                    body += self.page(ch, min(6, lvl + 1))
            return head + body
        finally:
            self.stack.pop()

    def folder(self, node, lvl):
        out = [self.title(node.name, lvl)]
        kids = self.repo.children(node.id, self.user.id)
        for ch in sorted(kids, key=lambda n: n.type != FOLDER):
            out += self.folder(ch, min(6, lvl + 1)) if ch.type == FOLDER else self.page(ch, min(6, lvl + 1))
        return out


class ExportService:
    def __init__(self, repo, assets, tree):
        self.repo, self.assets, self.tree = repo, assets, tree

    def export(self, user, node_id, fmt="md", images="embed"):
        node = self.tree.get(user, node_id)
        if fmt not in MIME:
            raise unprocessable("format must be md, html, txt or zip", errors={"format": "invalid"})
        if images not in ("embed", "assets"):
            raise unprocessable("images must be embed or assets", errors={"images": "invalid"})
        if fmt == "zip":
            return self._zip(user, node)
        ctx = _Ctx(self.repo, self.assets, user, fmt, "embed")
        parts = ctx.folder(node, 1) if node.type == FOLDER else ctx.page(node, 1)
        sep = "\n" if fmt == "html" else "\n\n"
        body = sep.join(parts)
        if fmt == "html":
            body = ("<!DOCTYPE html>\n<html lang=\"fr\"><head><meta charset=\"utf-8\">"
                    f"<title>{escape(node.name)}</title><style>body{{font-family:system-ui,sans-serif;max-width:48rem;"
                    "margin:2rem auto;padding:0 1rem;line-height:1.6}img{max-width:100%}</style></head>\n<body>\n"
                    + body + "\n</body></html>")
        return Export((body.rstrip() + "\n").encode("utf-8"), f"{slugify(node.name)}.{fmt}", MIME[fmt])

    def _zip(self, user, node):
        buf = io.BytesIO()
        used = {}
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            def unique(names, base, ext=""):
                n, i = base, 2
                while f"{n}{ext}" in names:
                    n, i = f"{base}-{i}", i + 1
                names.add(f"{n}{ext}")
                return f"{n}{ext}"

            def add_page(page, path):
                ctx = _Ctx(self.repo, self.assets, user, "md", "assets", prefix="../" * len(path), yaml=True)
                text = "\n\n".join(ctx.page(page, 1)).rstrip() + "\n"
                used.update(ctx.used)
                return text

            def add_folder(folder, path, names):
                here = set()
                for ch in sorted(self.repo.children(folder.id, user.id), key=lambda n: n.type != FOLDER):
                    if ch.type == FOLDER:
                        sub = unique(names_for.setdefault(tuple(path), set()), slugify(ch.name))
                        add_folder(ch, path + [sub], None)
                    else:
                        fn = unique(here, slugify(ch.name), ".md")
                        z.writestr("/".join(path + [fn]), add_page(ch, path))

            names_for = {}
            if node.type == FOLDER:
                root = slugify(node.name)
                add_folder(node, [root], None)
            else:
                z.writestr(f"{slugify(node.name)}.md", add_page(node, []))
            for a in used.values():
                z.writestr(f"assets/{a.id}.{self.assets.ext(a)}", self.assets.read(a))
        return Export(buf.getvalue(), f"{slugify(node.name)}.zip", MIME["zip"])
