import re
import uuid

from flask import Response, g, jsonify, request, send_file

from ..auth import auth_required
from ..container import svc
from ..errors import bad_request, not_found, unprocessable
from ..validation import int_arg
from . import bp
from .serializers import template_dict


@bp.get("/health")
def health():
    ok = bool(svc().repo.ping())
    resp = jsonify({"status": "ok" if ok else "degraded", "db": ok})
    resp.status_code = 200 if ok else 503
    return resp


@bp.get("/templates")
@auth_required()
def templates():
    return jsonify({"items": [template_dict(t) for t in svc().repo.list_templates()]})


# ---- assets -----------------------------------------------------------------
@bp.post("/assets")
@auth_required(write=True)
def upload_asset():
    f = request.files.get("file")
    if f is None:
        raise bad_request("Multipart field 'file' is required", "missing_file")
    node_id = request.form.get("node_id") or None
    if node_id:
        svc().tree.get(g.user, node_id)
    asset, created = svc().assets.upload(g.user, f.filename, f.read(), node_id)
    resp = jsonify({"id": asset.id, "url": f"/api/v1/assets/{asset.id}", "width": asset.width,
                    "height": asset.height, "mime_type": asset.mime_type, "size_bytes": asset.size_bytes})
    resp.status_code = 201 if created else 200
    return resp


@bp.get("/assets/<asset_id>")
def get_asset(asset_id):
    # Capability URL: the id is an unguessable UUID, so <img> tags work without an Authorization header.
    try:
        uuid.UUID(asset_id)
    except ValueError:
        raise not_found("Asset")
    s = svc()
    asset = s.repo.get_asset(asset_id)
    if asset is None or not s.assets.path(asset).exists():
        raise not_found("Asset")
    resp = send_file(s.assets.path(asset), mimetype=asset.mime_type, conditional=True, etag=asset.sha256)
    resp.headers["Cache-Control"] = "public, max-age=31536000, immutable"
    resp.headers["X-Content-Type-Options"] = "nosniff"
    return resp


# ---- search -----------------------------------------------------------------
@bp.get("/search")
@auth_required()
def search():
    a = request.args
    items, total = svc().search.search(
        g.user, a.get("q"), a.get("scope", "all"), a.get("folder_id") or None, a.get("template_id") or None,
        a.get("status") or None, int_arg("limit", 20, 1, 100), int_arg("offset", 0, 0, 100000))
    resp = jsonify({"items": items, "total": total})
    resp.headers["X-Total-Count"] = str(total)
    return resp


# ---- export -----------------------------------------------------------------
@bp.get("/export/<node_id>")
@auth_required()
def export(node_id):
    exp = svc().export.export(g.user, node_id, request.args.get("format", "md"), request.args.get("images", "embed"))
    name = re.sub(r"[^A-Za-z0-9._-]", "_", exp.filename)
    return Response(exp.data, mimetype=exp.mimetype.split(";")[0],
                    headers={"Content-Disposition": f'attachment; filename="{name}"',
                             "Content-Type": exp.mimetype})
