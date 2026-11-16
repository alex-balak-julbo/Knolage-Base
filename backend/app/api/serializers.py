from ..domain import PAGE, iso


def node_dict(n, full=False):
    d = {"id": n.id, "type": n.type, "parent_id": n.parent_id, "name": n.name, "icon": n.icon,
         "position": n.position, "template_id": n.template_id, "version": n.version,
         "created_at": iso(n.created_at), "updated_at": iso(n.updated_at)}
    if full and n.type == PAGE:
        d["props"], d["content"] = n.props, n.content
    return d


def summary(n):
    d = {"id": n.id, "type": n.type, "parent_id": n.parent_id, "name": n.name, "icon": n.icon,
         "position": n.position, "template_id": n.template_id, "version": n.version,
         "updated_at": iso(n.updated_at)}
    if n.type == PAGE and n.props.get("status"):
        d["status"] = n.props["status"]
    return d


def template_dict(t):
    return {"id": t.id, "name": t.name, "description": t.description, "icon": t.icon,
            "props_schema": t.props_schema, "default_content": t.default_content, "is_system": t.is_system}
