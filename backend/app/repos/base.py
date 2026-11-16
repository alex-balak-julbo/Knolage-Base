"""Repository contract. Services depend only on this interface.

Implementations: MemoryRepo (tests/dev) and SqlRepo (SQLAlchemy: MySQL in production).
"""


def compute_trash_roots(deleted_nodes):
    """Deleted nodes that were deleted on their own (not as part of a parent's deletion)."""
    by_id = {n.id: n for n in deleted_nodes}
    roots = []
    for n in deleted_nodes:
        p = by_id.get(n.parent_id) if n.parent_id else None
        if p is None or p.deleted_at != n.deleted_at:
            roots.append(n)
    return roots


class Repo:
    # users
    def get_user(self, user_id): raise NotImplementedError
    def get_user_by_email(self, email): raise NotImplementedError
    def add_user(self, user): raise NotImplementedError
    def count_users(self): raise NotImplementedError
    # templates
    def list_templates(self): raise NotImplementedError
    def get_template(self, template_id): raise NotImplementedError
    def save_template(self, template): raise NotImplementedError
    # nodes
    def get_node(self, node_id, include_deleted=False): raise NotImplementedError
    def list_active(self, owner_id): raise NotImplementedError
    def children(self, parent_id, owner_id, include_deleted=False): raise NotImplementedError
    def add_node(self, node): raise NotImplementedError
    def save_node(self, node): raise NotImplementedError
    def descendant_ids(self, node_id, include_deleted=False): raise NotImplementedError
    def set_deleted(self, ids, when): raise NotImplementedError
    def clear_deleted(self, ids): raise NotImplementedError
    def delete_hard(self, ids): raise NotImplementedError
    def list_deleted(self, owner_id=None): raise NotImplementedError
    def search_candidates(self, owner_id, q, scope, restrict_ids=None, template_id=None): raise NotImplementedError
    # assets
    def add_asset(self, asset): raise NotImplementedError
    def get_asset(self, asset_id): raise NotImplementedError
    def find_asset_by_sha(self, owner_id, sha): raise NotImplementedError
    # transaction / lifecycle
    def commit(self): pass
    def rollback(self): pass
    def cleanup(self): pass
    def ping(self): return True

    # derived helpers
    def list_trash_roots(self, owner_id):
        return compute_trash_roots(self.list_deleted(owner_id))

    def expired_trash_roots(self, before):
        return [n for n in compute_trash_roots(self.list_deleted(None)) if n.deleted_at < before]
