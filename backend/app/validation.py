from flask import request

from .errors import bad_request, unprocessable


def json_body():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise bad_request("Request body must be a JSON object", "invalid_json")
    return data


def req_str(d, key, max_len=255):
    v = d.get(key)
    if not isinstance(v, str) or not v.strip():
        raise unprocessable(f"{key} is required", errors={key: "required"})
    if len(v) > max_len:
        raise unprocessable(f"{key} too long", errors={key: f"max {max_len} chars"})
    return v.strip()


def int_arg(name, default, lo, hi):
    raw = request.args.get(name)
    if raw is None or raw == "":
        return default
    try:
        v = int(raw)
    except ValueError:
        raise unprocessable(f"{name} must be an integer", errors={name: "invalid"})
    return max(lo, min(hi, v))


def parse_if_match():
    raw = request.headers.get("If-Match")
    if raw is None:
        return None
    raw = raw.strip()
    if raw.startswith("W/"):
        raw = raw[2:]
    try:
        return int(raw.strip('"'))
    except ValueError:
        raise unprocessable("If-Match must contain the node version", errors={"If-Match": "invalid"})
