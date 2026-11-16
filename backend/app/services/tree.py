"""Tree rules: create / update / move / delete / restore for folders and pages."""
import copy
import uuid

from ..domain import FOLDER, PAGE, STEP, Node, iso, utcnow
from ..errors import conflict, not_found, unprocessable, ApiError
from . import content as C
from .ordering import position_between


class TreeService:
    def __init__(self, repo, cfg):
        self.repo, self.cfg = repo, cfg

    # ------------------------------------------------------------------ helpers
    def get(self, user, node_id, include_deleted=False):
        n = self.repo.get_node(node_id, include_deleted) if node_id else None
        if n is None or n.owner_id != user.id:
            raise not_found("Node")
        return n

    def _clean_name(self, name):
        if not isinstance(name, str) or not name.strip():
            raise unprocessable("name is required", errors={"name": "required"})
        name = name.strip()
        if len(name) > 255:
            raise unprocessable("name too long (max 255)", errors={"name": "too long"})
        return name

    def _folder_depth(self, parent_id):
        depth, cur = 0, parent_id
        while cur:
            n = self.repo.get_node(cur, include_deleted=True)
            if n is None:
                break
            if n.type == FOLDER:
                depth += 1
            cur = n.parent_id
        return depth

    def _folder_height(self, node_id):
        """Number of folder levels strictly below node_id."""
        height, level = 0, [node_id]
        while level:
            nxt = []
            for pid in level:
                nxt += [c.id for c in self.repo.children(pid, self._owner_of(pid)) if c.type == FOLDER]
            if nxt:
                height += 1
            level = nxt
        return height

    def _owner_of(self, node_id):
        return self.repo.get_node(node_id, include_deleted=True).owner_id

    def _check_parent(self, user, node_type, parent_id):
        parent = self.get(user, parent_id) if parent_id else None
        if parent is not None:
            if node_type == FOLDER and parent.type != FOLDER:
                raise unprocessable("A folder can only be placed in a folder or at the root", "invalid_parent")
        return parent

    def _validate_props(self, tpl, props):
        if not isinstance(props, dict):
            raise unprocessable("props must be an object", errors={"props": "must be an object"})
        schema = {f["key"]: f for f in tpl.props_schema}
        errs = {}
        for k, v in props.items():
            f = schema.get(k)
            if f is None:
                errs[k] = "unknown property"
            elif v is None or v == "":
                continue
            elif not isinstance(v, str) or len(v) > 2000:
                errs[k] = "must be a string (max 2000 chars)"
            elif f.get("type") == "select" and v not in f.get("options", []):
                errs[k] = f"must be one of {f.get('options')}"
        if errs:
            raise unprocessable("Invalid properties", "invalid_props", errs)
        return {k: v for k, v in props.items() if v not in (None, "")}

    def _search_text(self, tpl, props, doc):
        parts = [C.extract_text(doc)] if doc else []
        if tpl:
            parts += [str(props[f["key"]]) for f in tpl.props_schema if props.get(f["key"])]
        return "\n".join(p for p in parts if p)

    def _validate_content(self, user, doc):
        def page_ok(pid):
            n = self.repo.get_node(pid)
            return n is not None and n.owner_id == user.id and n.type == PAGE

        def asset_ok(aid):
            a = self.repo.get_asset(aid)
            return a is not None and a.owner_id == user.id

        try:
            return C.validate_doc(doc, asset_ok=asset_ok, page_ok=page_ok,
                                  max_bytes=self.cfg.MAX_CONTENT_BYTES)
        except C.ContentError as e:
            raise unprocessable(str(e), "invalid_content", {"content": e.msg, "path": e.path})

    def _touch(self, node, now=None):
        node.version += 1
        node.updated_at = now or utcnow()

    def _sync_link(self, parent, child_id, add):
        """Keep the parent page's pageLink in sync with its sub-page children."""
        if parent is None or parent.type != PAGE:
            return False
        has = child_id in C.link_ids(parent.content)
        if add and not has:
            parent.content = C.append_link(parent.content, child_id)
        elif not add and has:
            parent.content = C.remove_links(parent.content, [child_id])
        else:
            return False
        tpl = self.repo.get_template(parent.template_id)
        parent.search_text = self._search_text(tpl, parent.props, parent.content)
        self._touch(parent)
        self.repo.save_node(parent)
        return True

    # ------------------------------------------------------------------ queries
    def tree(self, user):
        return sorted(self.repo.list_active(user.id), key=lambda n: (n.parent_id or "", n.position, n.id))

    def breadcrumb(self, user, node_id):
        node, chain = self.get(user, node_id), []
        cur = node.parent_id
        while cur:
            p = self.repo.get_node(cur)
            if p is None:
                break
            chain.insert(0, p)
            cur = p.parent_id
        return chain

    def stats(self, user, node_id):
        self.get(user, node_id)
        ids = self.repo.descendant_ids(node_id)[1:]
        nodes = [self.repo.get_node(i) for i in ids]
        return {"descendants": len(ids),
                "folders": sum(1 for n in nodes if n.type == FOLDER),
                "pages": sum(1 for n in nodes if n.type == PAGE)}

    # ------------------------------------------------------------------ commands
    def create(self, user, *, type, parent_id=None, name, template_id=None, props=None,
               content=None, icon=None, node_id=None, link=True):
        if type not in (FOLDER, PAGE):
            raise unprocessable("type must be 'folder' or 'page'", errors={"type": "invalid"})
        name = self._clean_name(name)
        if node_id:
            if not C.UUID_RE.match(node_id):
                raise unprocessable("id must be a uuid", errors={"id": "invalid"})
            if self.repo.get_node(node_id, include_deleted=True):
                raise conflict("A node with this id already exists", "duplicate_id")
        parent = self._check_parent(user, type, parent_id)
        if type == FOLDER and self._folder_depth(parent_id) + 1 > self.cfg.MAX_FOLDER_DEPTH:
            raise unprocessable(f"Maximum folder depth is {self.cfg.MAX_FOLDER_DEPTH}", "max_depth")
        siblings = self.repo.children(parent_id, user.id)
        node = Node(id=node_id or str(uuid.uuid4()), type=type, owner_id=user.id, name=name,
                    parent_id=parent_id, icon=(icon or None),
                    position=(siblings[-1].position + STEP) if siblings else STEP)
        if type == PAGE:
            tpl = self.repo.get_template(template_id or "blank")
            if tpl is None:
                raise unprocessable("Unknown template", errors={"template_id": "unknown"})
            node.template_id = tpl.id
            node.props = self._validate_props(tpl, props or {})
            node.content = self._validate_content(user, content) if content else copy.deepcopy(tpl.default_content or C.empty_doc())
            node.search_text = self._search_text(tpl, node.props, node.content)
        elif props or content or template_id:
            raise unprocessable("Folders cannot have props, content or a template")
        self.repo.add_node(node)
        affected = []
        if type == PAGE and link and parent is not None and parent.type == PAGE:
            if self._sync_link(parent, node.id, add=True):
                affected.append(parent.id)
        return node, affected

    def update(self, user, node_id, fields, if_match):
        node = self.get(user, node_id)
        if if_match is None:
            raise ApiError(428, "Precondition required", "Send the node version in the If-Match header", "precondition_required")
        if if_match != node.version:
            raise conflict("The node was modified by someone else", "version_conflict", current_version=node.version)
        if node.type == FOLDER and ({"props", "content"} & set(fields)):
            raise unprocessable("Folders have no props or content")
        if "name" in fields:
            node.name = self._clean_name(fields["name"])
        if "icon" in fields:
            icon = fields["icon"]
            if icon is not None and (not isinstance(icon, str) or len(icon) > 16):
                raise unprocessable("icon must be a short string", errors={"icon": "invalid"})
            node.icon = icon or None
        deleted_ids = []
        if node.type == PAGE:
            tpl = self.repo.get_template(node.template_id)
            if "props" in fields:
                merged = {**node.props, **(fields["props"] if isinstance(fields["props"], dict) else {})}
                if not isinstance(fields["props"], dict):
                    raise unprocessable("props must be an object", errors={"props": "must be an object"})
                node.props = self._validate_props(tpl, merged)
            if "content" in fields:
                old_links = set(C.link_ids(node.content))
                node.content = self._validate_content(user, fields["content"])
                removed = old_links - set(C.link_ids(node.content))
                for cid in removed:
                    child = self.repo.get_node(cid)
                    if child and child.parent_id == node.id and child.owner_id == user.id:
                        deleted_ids += self._soft_delete(child.id)
            # every sub-page must be reachable through a pageLink
            linked = set(C.link_ids(node.content))
            for ch in self.repo.children(node.id, user.id):
                if ch.type == PAGE and ch.id not in linked:
                    node.content = C.append_link(node.content, ch.id)
            node.search_text = self._search_text(tpl, node.props, node.content)
        self._touch(node)
        self.repo.save_node(node)
        return node, deleted_ids

    def move(self, user, node_id, *, parent_id=None, before_id=None, after_id=None):
        node = self.get(user, node_id)
        if before_id and after_id:
            raise unprocessable("Use either before_id or after_id", errors={"before_id": "conflict"})
        parent = self._check_parent(user, node.type, parent_id)
        # no cycles: the new parent must not be the node itself or one of its descendants
        cur = parent_id
        while cur:
            if cur == node.id:
                raise unprocessable("Cannot move a node into itself or one of its descendants", "cycle")
            cur = self.repo.get_node(cur, include_deleted=True).parent_id
        if node.type == FOLDER:
            total = self._folder_depth(parent_id) + 1 + self._folder_height(node.id)
            if total > self.cfg.MAX_FOLDER_DEPTH:
                raise unprocessable(f"Maximum folder depth is {self.cfg.MAX_FOLDER_DEPTH}", "max_depth")
        sibs = [s for s in self.repo.children(parent_id, user.id) if s.id != node.id]
        ref = before_id or after_id
        if ref:
            idx = next((i for i, s in enumerate(sibs) if s.id == ref), None)
            if idx is None:
                raise unprocessable("Reference sibling not found under the target parent", "bad_reference")
            index = idx if before_id else idx + 1
        else:
            index = len(sibs)
        old_parent_id = node.parent_id
        node.parent_id = parent_id
        pos = position_between(sibs[index - 1].position if index > 0 else None,
                               sibs[index].position if index < len(sibs) else None)
        affected = []
        if pos is None:  # gap exhausted: renumber the whole sibling list
            order = sibs[:index] + [node] + sibs[index:]
            for k, s in enumerate(order):
                s.position = (k + 1) * STEP
                if s is not node:
                    self.repo.save_node(s)
        else:
            node.position = pos
        self._touch(node)
        self.repo.save_node(node)
        if node.type == PAGE and old_parent_id != parent_id:
            old = self.repo.get_node(old_parent_id) if old_parent_id else None
            if self._sync_link(old, node.id, add=False):
                affected.append(old.id)
            if self._sync_link(parent, node.id, add=True):
                affected.append(parent.id)
        return node, affected

    def _soft_delete(self, node_id, when=None):
        ids = self.repo.descendant_ids(node_id)
        self.repo.set_deleted(ids, when or utcnow())
        return ids

    def delete(self, user, node_id):
        node = self.get(user, node_id)
        ids = self._soft_delete(node_id)
        affected = []
        parent = self.repo.get_node(node.parent_id) if node.parent_id else None
        if node.type == PAGE and self._sync_link(parent, node.id, add=False):
            affected.append(parent.id)
        return {"deleted": len(ids), "ids": ids, "affected": affected}

    # ------------------------------------------------------------------ trash
    def trash(self, user):
        return sorted(self.repo.list_trash_roots(user.id), key=lambda n: n.deleted_at, reverse=True)

    def _trash_ids(self, node):
        return [i for i in self.repo.descendant_ids(node.id, include_deleted=True)
                if self.repo.get_node(i, include_deleted=True).deleted_at == node.deleted_at]

    def restore(self, user, node_id):
        node = self.get(user, node_id, include_deleted=True)
        if not node.deleted_at:
            raise unprocessable("Node is not in the trash", "not_deleted")
        ids = self._trash_ids(node)
        parent = self.repo.get_node(node.parent_id, include_deleted=True) if node.parent_id else None
        if node.parent_id and (parent is None or parent.deleted_at):
            node.parent_id, parent = None, None
        self.repo.clear_deleted(ids)
        node.deleted_at = None
        self._touch(node)
        self.repo.save_node(node)
        if node.type == PAGE and parent is not None:
            self._sync_link(parent, node.id, add=True)
        return node, len(ids)

    def purge(self, user, node_id):
        node = self.get(user, node_id, include_deleted=True)
        if not node.deleted_at:
            raise unprocessable("Only trashed items can be permanently deleted", "not_deleted")
        ids = self._trash_ids(node)
        self.repo.delete_hard(ids)
        return len(ids)

    def empty_trash(self, user):
        return sum(self.purge(user, n.id) for n in self.repo.list_trash_roots(user.id))

    def purge_expired(self):
        from datetime import timedelta
        before = utcnow() - timedelta(days=self.cfg.TRASH_RETENTION_DAYS)
        total = 0
        for n in self.repo.expired_trash_roots(before):
            self.repo.delete_hard(self._trash_ids(n))
            total += 1
        return total
