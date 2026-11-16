import logging

from flask import Flask, request

from .config import Config
from .container import Services
from .errors import register_error_handlers
from .seed import ensure_templates


def build_repo(cfg):
    if cfg.STORAGE == "memory":
        from .repos.memory import MemoryRepo
        return MemoryRepo()
    from .repos.sql import SqlRepo  # imported lazily: SQLAlchemy is only needed here
    if not cfg.DATABASE_URL:
        raise RuntimeError("DATABASE_URL is required when STORAGE=sql")
    return SqlRepo(cfg.DATABASE_URL)


def create_app(config=None, repo=None):
    app = Flask(__name__)
    cfg = config if isinstance(config, Config) else Config(**(config or {}))
    app.config.update(SECRET_KEY=cfg.SECRET_KEY, TESTING=cfg.TESTING, MAX_CONTENT_LENGTH=(max(cfg.MAX_UPLOAD_MB * 1024 * 1024, cfg.MAX_CONTENT_BYTES) + 1024 * 1024))
    repo = repo or build_repo(cfg)
    app.extensions["docbase"] = Services(cfg, repo)
    register_error_handlers(app)
    logging.basicConfig(level=logging.INFO)

    from .api import bp
    app.register_blueprint(bp)

    @app.before_request
    def _cors_preflight():
        if request.method == "OPTIONS" and request.headers.get("Origin") in cfg.CORS_ORIGINS:
            return "", 204

    @app.after_request
    def _finish(resp):
        origin = request.headers.get("Origin")
        if origin and origin in cfg.CORS_ORIGINS:
            resp.headers["Access-Control-Allow-Origin"] = origin
            resp.headers["Access-Control-Allow-Credentials"] = "true"
            resp.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type, If-Match"
            resp.headers["Access-Control-Allow-Methods"] = "GET, POST, PATCH, DELETE, OPTIONS"
            resp.headers["Access-Control-Expose-Headers"] = "X-Total-Count, ETag, Location"
            resp.headers["Vary"] = "Origin"
        if resp.status_code < 400:
            repo.commit()
        else:
            repo.rollback()
        return resp

    @app.teardown_request
    def _cleanup(exc):
        if exc is not None:
            repo.rollback()
        repo.cleanup()

    if cfg.STORAGE == "memory":  # nothing persists, so bootstrap on every start
        ensure_templates(repo)
        if getattr(cfg, "SEED_DEMO", False):
            from .seed import demo_data, ensure_user
            user = ensure_user(repo, cfg.DEMO_EMAIL, cfg.DEMO_PASSWORD, "admin")
            demo_data(app.extensions["docbase"].tree, user)
        repo.commit()

    from .cli import register_cli
    register_cli(app)
    return app
