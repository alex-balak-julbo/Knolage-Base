from flask import current_app

from .auth import RateLimiter
from .services.assets import AssetService
from .services.export import ExportService
from .services.search import SearchService
from .services.tree import TreeService


class Services:
    def __init__(self, cfg, repo):
        self.cfg, self.repo = cfg, repo
        self.tree = TreeService(repo, cfg)
        self.search = SearchService(repo, self.tree)
        self.assets = AssetService(repo, cfg)
        self.export = ExportService(repo, self.assets, self.tree)
        self.limiter = RateLimiter()


def svc() -> Services:
    return current_app.extensions["docbase"]
