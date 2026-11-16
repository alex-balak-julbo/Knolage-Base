import io
import os
import shutil
import tempfile
import unittest

from PIL import Image

from app import create_app
from app.seed import ensure_templates, ensure_user


def make_repo():
    if os.environ.get("TEST_REPO") == "sql":
        from app.repos.sql import SqlRepo
        repo = SqlRepo("sqlite://")
        repo.create_all()
        return repo
    from app.repos.memory import MemoryRepo
    return MemoryRepo()


def p(text="", marks=None):
    if not text:
        return {"type": "paragraph"}
    t = {"type": "text", "text": text}
    if marks:
        t["marks"] = marks
    return {"type": "paragraph", "content": [t]}


def h(text, level=2):
    return {"type": "heading", "attrs": {"level": level}, "content": [{"type": "text", "text": text}]}


def ul(*items, kind="bulletList"):
    return {"type": kind, "content": [{"type": "listItem", "content": [p(i)]} for i in items]}


def doc(*blocks):
    return {"type": "doc", "content": list(blocks)}


def png_bytes(size=(20, 10), color=(200, 30, 30)):
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, "PNG")
    return buf.getvalue()


class ApiTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.repo = make_repo()
        self.app = create_app({"TESTING": True, "UPLOAD_DIR": self.tmp, "LOGIN_RATE": 1000, "MAX_UPLOAD_MB": 1},
                              repo=self.repo)
        ensure_templates(self.repo)
        self.user = ensure_user(self.repo, "admin@example.com", "secret-pass", "admin")
        self.repo.commit()
        self.c = self.app.test_client()
        self.token = self.c.post("/api/v1/auth/login", json={"email": "admin@example.com", "password": "secret-pass"}).json["access_token"]

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def api(self, method, path, token="default", **kw):
        headers = kw.pop("headers", {})
        tok = self.token if token == "default" else token
        if tok:
            headers["Authorization"] = f"Bearer {tok}"
        return self.c.open("/api/v1" + path, method=method, headers=headers, **kw)

    def mk(self, type, name, parent=None, expect=201, **kw):
        r = self.api("POST", "/nodes", json={"type": type, "name": name, "parent_id": parent, **kw})
        self.assertEqual(r.status_code, expect, r.get_data(as_text=True))
        return r.json

    def folder(self, name, parent=None, **kw):
        return self.mk("folder", name, parent, **kw)["id"]

    def page(self, name, parent=None, **kw):
        return self.mk("page", name, parent, **kw)["id"]

    def patch(self, node_id, expect=200, **fields):
        v = self.api("GET", f"/nodes/{node_id}").json["version"]
        r = self.api("PATCH", f"/nodes/{node_id}", json=fields, headers={"If-Match": str(v)})
        self.assertEqual(r.status_code, expect, r.get_data(as_text=True))
        return r.json

    def move(self, node_id, expect=200, **body):
        r = self.api("POST", f"/nodes/{node_id}/move", json=body)
        self.assertEqual(r.status_code, expect, r.get_data(as_text=True))
        return r.json

    def children(self, parent=None):
        nodes = self.api("GET", "/tree").json["nodes"]
        return [n["id"] for n in sorted((n for n in nodes if n["parent_id"] == parent), key=lambda n: (n["position"], n["id"]))]

    def upload(self, data=None, name="a.png", expect=None):
        r = self.api("POST", "/assets", data={"file": (io.BytesIO(data or png_bytes()), name)},
                     content_type="multipart/form-data")
        if expect:
            self.assertEqual(r.status_code, expect, r.get_data(as_text=True))
        return r
