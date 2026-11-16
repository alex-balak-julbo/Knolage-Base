from flask import g, jsonify

from ..auth import auth_required
from ..container import svc
from ..domain import iso
from ..errors import unprocessable
from ..validation import json_body, parse_if_match
from . import bp
from .serializers import node_dict, summary

EDITABLE = ("name", "icon", "props", "content")


def _node_response(node, status=200, **extra):
    resp = jsonify({**node_dict(node, full=True), **extra})
    resp.status_code = status
    resp.headers["ETag"] = f'"{node.version}"'
    return resp


@bp.get("/tree")
@auth_required()
def tree():
    return jsonify({"nodes": [summary(n) for n in svc().tree.tree(g.user)]})


@bp.post("/nodes")
@auth_required(write=True)
def create_node():
    b = json_body()
    node, affected = svc().tree.create(
        g.user, type=b.get("type"), parent_id=b.get("parent_id"), name=b.get("name"),
        template_id=b.get("template_id"), props=b.get("props"), content=b.get("content"),
        icon=b.get("icon"), node_id=b.get("id"), link=b.get("link", True) is not False)
    resp = _node_response(node, 201, affected_ids=affected)
    resp.headers["Location"] = f"/api/v1/nodes/{node.id}"
    return resp


@bp.get("/nodes/<node_id>")
@auth_required()
def get_node(node_id):
    return _node_response(svc().tree.get(g.user, node_id))


@bp.patch("/nodes/<node_id>")
@auth_required(write=True)
def patch_node(node_id):
    b = json_body()
    fields = {k: b[k] for k in EDITABLE if k in b}
    if not fields:
        raise unprocessable(f"Provide at least one of {EDITABLE}")
    node, deleted = svc().tree.update(g.user, node_id, fields, parse_if_match())
    return _node_response(node, deleted_ids=deleted)


@bp.post("/nodes/<node_id>/move")
@auth_required(write=True)
def move_node(node_id):
    b = json_body()
    node, affected = svc().tree.move(g.user, node_id, parent_id=b.get("parent_id"),
                                     before_id=b.get("before_id"), after_id=b.get("after_id"))
    return _node_response(node, affected_ids=affected)


@bp.delete("/nodes/<node_id>")
@auth_required(write=True)
def delete_node(node_id):
    r = svc().tree.delete(g.user, node_id)
    return jsonify({"deleted": r["deleted"], "ids": r["ids"], "affected_ids": r["affected"]})


@bp.get("/nodes/<node_id>/breadcrumb")
@auth_required()
def breadcrumb(node_id):
    chain = svc().tree.breadcrumb(g.user, node_id)
    return jsonify({"items": [{"id": n.id, "type": n.type, "name": n.name, "icon": n.icon} for n in chain]})


@bp.get("/nodes/<node_id>/stats")
@auth_required()
def stats(node_id):
    return jsonify(svc().tree.stats(g.user, node_id))


# ---- trash ----------------------------------------------------------------
@bp.get("/trash")
@auth_required()
def trash():
    items = svc().tree.trash(g.user)
    resp = jsonify({"items": [{**summary(n), "deleted_at": iso(n.deleted_at)} for n in items]})
    resp.headers["X-Total-Count"] = str(len(items))
    return resp


@bp.post("/trash/<node_id>/restore")
@auth_required(write=True)
def restore(node_id):
    node, count = svc().tree.restore(g.user, node_id)
    return _node_response(node, restored=count)


@bp.delete("/trash/<node_id>")
@auth_required(write=True)
def purge(node_id):
    return jsonify({"purged": svc().tree.purge(g.user, node_id)})


@bp.delete("/trash")
@auth_required(write=True)
def empty_trash():
    return jsonify({"purged": svc().tree.empty_trash(g.user)})
