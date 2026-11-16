import os


def _get(name, default=None):
    return os.environ.get(name, default)


class Config:
    """Settings read from environment variables; keyword overrides win (used by tests)."""

    def __init__(self, **overrides):
        self.ENV = _get("APP_ENV", "development")
        self.TESTING = False
        self.SECRET_KEY = _get("SECRET_KEY", "dev-secret-change-me")
        self.JWT_SECRET = _get("JWT_SECRET_KEY", "dev-jwt-secret-change-me")
        self.ACCESS_TTL = int(_get("JWT_ACCESS_TTL", "900"))
        self.REFRESH_TTL = int(_get("JWT_REFRESH_TTL", str(7 * 86400)))
        self.COOKIE_SECURE = _get("COOKIE_SECURE", "0") == "1"
        self.DATABASE_URL = _get("DATABASE_URL")
        self.STORAGE = _get("STORAGE", "sql" if self.DATABASE_URL else "memory")
        self.UPLOAD_DIR = _get("UPLOAD_DIR", "./uploads")
        self.MAX_UPLOAD_MB = int(_get("MAX_UPLOAD_MB", "5"))
        self.MAX_IMAGE_WIDTH = int(_get("MAX_IMAGE_WIDTH", "1600"))
        self.MAX_FOLDER_DEPTH = int(_get("MAX_FOLDER_DEPTH", "8"))
        self.MAX_CONTENT_BYTES = int(_get("MAX_CONTENT_BYTES", str(2 * 1024 * 1024)))
        self.TRASH_RETENTION_DAYS = int(_get("TRASH_RETENTION_DAYS", "30"))
        self.CORS_ORIGINS = [o.strip() for o in _get("CORS_ORIGINS", "").split(",") if o.strip()]
        self.LOGIN_RATE = int(_get("LOGIN_RATE_PER_MIN", "5"))
        self.SEED_DEMO = _get("SEED_DEMO", "0") == "1"
        self.DEMO_EMAIL = _get("DEMO_EMAIL", "admin@example.com")
        self.DEMO_PASSWORD = _get("DEMO_PASSWORD", "admin1234")
        for k, v in overrides.items():
            setattr(self, k, v)
        if self.ENV == "production" and not self.TESTING:
            if "change-me" in self.SECRET_KEY or "change-me" in self.JWT_SECRET:
                raise RuntimeError("Set SECRET_KEY and JWT_SECRET_KEY in production")
