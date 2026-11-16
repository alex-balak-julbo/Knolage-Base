from flask import Blueprint

bp = Blueprint("api", __name__, url_prefix="/api/v1")

from . import auth_routes, node_routes, misc_routes  # noqa: E402,F401
