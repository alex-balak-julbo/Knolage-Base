import copy
import threading

from ..textutil import fold
from .base import Repo


class MemoryRepo(Repo):
    """In-process store. Returns deep copies so callers cannot mutate state by accident."""

    def __init__(self):
        self.lock = threading.RLock()
        self.users, self.templates, self.nodes, self.assets = {}, {}, {}, {}

    # users
    def get_user(self, user_id):
        return copy.deepcopy(self.users.get(user_id))

    def get_user_by_email(self, email):
        e = (email or "").strip().lower()
        for u in self.users.values():
            if u.email.lower() == e:
                return copy.deepcopy(u)

    def add_user(self, user):
        self.users[user.id] = copy.deepcopy(user)

    def count_users(self):
        return len(self.users)

    # templates
    def list_templates(self):
        return [copy.deepcopy(t) for t in self.templates.values()]

    def get_template(self, template_id):
        return copy.deepcopy(self.templates.get(template_id))

    def save_template(self, template):
        self.templates[template.id] = copy.deepcopy(template)

    # nodes
    def get_node(self, node_id, include_deleted=False):
        n = self.nodes.get(node_id)
        if n is None or (n.deleted_at and not include_deleted):
            return None
        return n.clone()

    def list_active(self, owner_id):
        return [n.clone() for n in self.nodes.values() if n.owner_id == owner_id and not n.deleted_at]

    def children(self, parent_id, owner_id, include_deleted=False):
        out = [n for n in self.nodes.values()
               if n.parent_id == parent_id and n.owner_id == owner_id and (include_deleted or not n.deleted_at)]
        return [n.clone() for n in sorted(out, key=lambda n: (n.position, n.id))]

    def add_node(self, node):
        self.nodes[node.id] = node.clone()

    def save_node(self, node):
        if node.id not in self.nodes:
            raise KeyError(node.id)
        self.nodes[node.id] = node.clone()

    def descendant_ids(self, node_id, include_deleted=False):
        ids, frontier = [node_id], [node_id]
        while frontier:
            nxt = [n.id for n in self.nodes.values()
                   if n.parent_id in frontier and n.id not in ids and (include_deleted or not n.deleted_at)]
            ids += nxt
            frontier = nxt
        return ids

    def set_deleted(self, ids, when):
        for i in ids:
            if i in self.nodes:
                self.nodes[i].deleted_at = when

    def clear_deleted(self, ids):
        for i in ids:
            if i in self.nodes:
                self.nodes[i].deleted_at = None

    def delete_hard(self, ids):
        for i in ids:
            self.nodes.pop(i, None)

    def list_deleted(self, owner_id=None):
        return [n.clone() for n in self.nodes.values()
                if n.deleted_at and (owner_id is None or n.owner_id == owner_id)]

    def search_candidates(self, owner_id, q, scope, restrict_ids=None, template_id=None):
        fq, out = fold(q), []
        for n in self.nodes.values():
            if n.owner_id != owner_id or n.deleted_at or n.type != "page":
                continue
            if restrict_ids is not None and n.id not in restrict_ids:
                continue
            if template_id and n.template_id != template_id:
                continue
            t, c = fq in fold(n.name), fq in fold(n.search_text)
            if (scope == "title" and t) or (scope == "content" and c) or (scope == "all" and (t or c)):
                out.append(n.clone())
        return out

    # assets
    def add_asset(self, asset):
        self.assets[asset.id] = copy.deepcopy(asset)

    def get_asset(self, asset_id):
        return copy.deepcopy(self.assets.get(asset_id))

    def find_asset_by_sha(self, owner_id, sha):
        for a in self.assets.values():
            if a.owner_id == owner_id and a.sha256 == sha:
                return copy.deepcopy(a)
