"""JWT access/refresh tokens (PyJWT), password helpers, auth decorator, tiny rate limiter."""
import time
import uuid
from collections import defaultdict, deque
from functools import wraps

import jwt
from flask import current_app, g, request
from werkzeug.security import check_password_hash, generate_password_hash

from .domain import User
from .errors import forbidden, unauthorized, ApiError


def hash_password(pw):
    return generate_password_hash(pw)


def verify_password(user, pw):
    return bool(user) and check_password_hash(user.password_hash, pw or "")


def make_token(cfg, user_id, kind):
    ttl = cfg.ACCESS_TTL if kind == "access" else cfg.REFRESH_TTL
    now = int(time.time())
    return jwt.encode({"sub": user_id, "typ": kind, "iat": now, "exp": now + ttl, "jti": uuid.uuid4().hex},
                      cfg.JWT_SECRET, algorithm="HS256")


def decode_token(cfg, token, kind):
    try:
        data = jwt.decode(token, cfg.JWT_SECRET, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise unauthorized("Token expired", "token_expired")
    except jwt.PyJWTError:
        raise unauthorized("Invalid token", "invalid_token")
    if data.get("typ") != kind:
        raise unauthorized("Wrong token type", "invalid_token")
    return data


def auth_required(write=False, admin=False):
    def deco(fn):
        @wraps(fn)
        def wrapper(*a, **kw):
            svc = current_app.extensions["docbase"]
            header = request.headers.get("Authorization", "")
            if not header.lower().startswith("bearer "):
                raise unauthorized()
            data = decode_token(svc.cfg, header[7:].strip(), "access")
            user = svc.repo.get_user(data["sub"])
            if user is None:
                raise unauthorized("Unknown user", "invalid_token")
            if admin and user.role != "admin":
                raise forbidden("Administrator role required")
            if write and user.role == "reader":
                raise forbidden("Read-only account")
            g.user = user
            return fn(*a, **kw)
        return wrapper
    return deco


class RateLimiter:
    """In-process sliding window. Use Flask-Limiter + Redis when running several workers."""

    def __init__(self):
        self.hits = defaultdict(deque)

    def check(self, key, limit, window=60):
        now, q = time.time(), self.hits[key]
        while q and q[0] <= now - window:
            q.popleft()
        if len(q) >= limit:
            raise ApiError(429, "Too many requests", "Try again in a minute", "rate_limited",
                           headers={"Retry-After": str(window)})
        q.append(now)
