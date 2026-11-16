from flask import g, jsonify, request

from ..auth import auth_required, decode_token, make_token, verify_password
from ..container import svc
from ..errors import unauthorized
from ..validation import json_body, req_str
from . import bp

COOKIE = "refresh_token"


def _set_refresh(resp, user_id):
    cfg = svc().cfg
    resp.set_cookie(COOKIE, make_token(cfg, user_id, "refresh"), max_age=cfg.REFRESH_TTL, httponly=True,
                    secure=cfg.COOKIE_SECURE, samesite="Lax", path="/api/v1/auth")


def _user_dict(u):
    return {"id": u.id, "email": u.email, "display_name": u.display_name, "role": u.role}


def _access(user):
    cfg = svc().cfg
    return {"access_token": make_token(cfg, user.id, "access"), "token_type": "Bearer",
            "expires_in": cfg.ACCESS_TTL, "user": _user_dict(user)}


@bp.post("/auth/login")
def login():
    s = svc()
    s.limiter.check(f"login:{request.remote_addr}", s.cfg.LOGIN_RATE)
    body = json_body()
    email, password = req_str(body, "email"), body.get("password")
    user = s.repo.get_user_by_email(email)
    if not verify_password(user, password):
        raise unauthorized("Invalid email or password", "invalid_credentials")
    resp = jsonify(_access(user))
    _set_refresh(resp, user.id)
    return resp


@bp.post("/auth/refresh")
def refresh():
    s = svc()
    token = request.cookies.get(COOKIE)
    if not token:
        raise unauthorized("No refresh token", "no_refresh_token")
    data = decode_token(s.cfg, token, "refresh")
    user = s.repo.get_user(data["sub"])
    if user is None:
        raise unauthorized("Unknown user", "invalid_token")
    return jsonify(_access(user))


@bp.post("/auth/logout")
def logout():
    resp = jsonify({"ok": True})
    resp.delete_cookie(COOKIE, path="/api/v1/auth")
    return resp


@bp.get("/auth/me")
@auth_required()
def me():
    return jsonify(_user_dict(g.user))
