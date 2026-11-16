"""RFC 7807 problem+json errors."""
from flask import jsonify
from werkzeug.exceptions import HTTPException


class ApiError(Exception):
    def __init__(self, status, title, detail=None, code=None, errors=None, headers=None, extra=None):
        super().__init__(detail or title)
        self.status, self.title, self.detail = status, title, detail
        self.code, self.errors, self.headers, self.extra = code, errors, headers or {}, extra or {}

    def to_response(self):
        body = {"type": "about:blank", "title": self.title, "status": self.status}
        if self.detail:
            body["detail"] = self.detail
        if self.code:
            body["code"] = self.code
        if self.errors:
            body["errors"] = self.errors
        body.update(self.extra)
        resp = jsonify(body)
        resp.status_code = self.status
        resp.headers["Content-Type"] = "application/problem+json"
        for k, v in self.headers.items():
            resp.headers[k] = v
        return resp


def bad_request(detail, code="bad_request"):
    return ApiError(400, "Bad request", detail, code)


def unauthorized(detail="Authentication required", code="unauthorized"):
    return ApiError(401, "Unauthorized", detail, code, headers={"WWW-Authenticate": "Bearer"})


def forbidden(detail="Forbidden", code="forbidden"):
    return ApiError(403, "Forbidden", detail, code)


def not_found(what="Resource"):
    return ApiError(404, "Not found", f"{what} not found", "not_found")


def conflict(detail, code="conflict", **extra):
    return ApiError(409, "Conflict", detail, code, extra=extra)


def unprocessable(detail, code="invalid", errors=None):
    return ApiError(422, "Unprocessable entity", detail, code, errors)


def register_error_handlers(app):
    @app.errorhandler(ApiError)
    def _api(e):
        return e.to_response()

    @app.errorhandler(HTTPException)
    def _http(e):
        return ApiError(e.code or 500, e.name, e.description).to_response()

    @app.errorhandler(Exception)
    def _any(e):
        app.logger.exception("Unhandled error")
        return ApiError(500, "Internal server error").to_response()
