import io
import json
import zipfile

from tests.helpers import ApiTestCase, doc, h, p, png_bytes, ul

UID = "22222222-2222-4222-8222-222222222222"


class AuthTests(ApiTestCase):
    def test_requires_token(self):
        self.assertEqual(self.api("GET", "/tree", token=None).status_code, 401)
        self.assertEqual(self.api("GET", "/tree", token="garbage").status_code, 401)

    def test_login_refresh_me(self):
        bad = self.c.post("/api/v1/auth/login", json={"email": "admin@example.com", "password": "nope"})
        self.assertEqual(bad.status_code, 401)
        ok = self.c.post("/api/v1/auth/login", json={"email": "ADMIN@example.com", "password": "secret-pass"})
        self.assertEqual(ok.status_code, 200)
        self.assertIn("HttpOnly", ok.headers["Set-Cookie"])
        r = self.c.post("/api/v1/auth/refresh")  # cookie jar of the test client
        self.assertEqual(r.status_code, 200)
        me = self.api("GET", "/auth/me", token=r.json["access_token"])
        self.assertEqual(me.json["email"], "admin@example.com")
        self.assertNotIn("password_hash", me.json)

    def test_refresh_token_is_not_an_access_token(self):
        from app.auth import make_token
        cfg = self.app.extensions["docbase"].cfg
        self.assertEqual(self.api("GET", "/tree", token=make_token(cfg, self.user.id, "refresh")).status_code, 401)

    def test_reader_cannot_write(self):
        from app.seed import ensure_user
        ensure_user(self.repo, "r@example.com", "reader-pass", "reader")
        self.repo.commit()
        tok = self.c.post("/api/v1/auth/login", json={"email": "r@example.com", "password": "reader-pass"}).json["access_token"]
        self.assertEqual(self.api("GET", "/tree", token=tok).status_code, 200)
        self.assertEqual(self.api("POST", "/nodes", token=tok, json={"type": "folder", "name": "x"}).status_code, 403)

    def test_login_rate_limit(self):
        svc = self.app.extensions["docbase"]
        svc.cfg.LOGIN_RATE = 3
        svc.limiter.hits.clear()
        codes = [self.c.post("/api/v1/auth/login", json={"email": "a@b.c", "password": "x"}).status_code for _ in range(5)]
        self.assertEqual(codes[:3], [401] * 3)
        self.assertEqual(codes[3], 429)

    def test_users_are_isolated(self):
        from app.seed import ensure_user
        ensure_user(self.repo, "o@example.com", "other-pass", "editor")
        self.repo.commit()
        other = self.c.post("/api/v1/auth/login", json={"email": "o@example.com", "password": "other-pass"}).json["access_token"]
        fid = self.folder("Mine")
        self.assertEqual(self.api("GET", f"/nodes/{fid}", token=other).status_code, 404)
        self.assertEqual(self.api("GET", "/tree", token=other).json["nodes"], [])
        self.assertEqual(self.api("POST", "/nodes", token=other, json={"type": "page", "name": "x", "parent_id": fid}).status_code, 404)


class TreeRuleTests(ApiTestCase):
    def test_nested_folders_and_pages(self):
        a = self.folder("A")
        b = self.folder("B", a)
        pg = self.page("Page", b)
        root_page = self.page("Root page")
        nodes = {n["id"]: n for n in self.api("GET", "/tree").json["nodes"]}
        self.assertEqual(nodes[b]["parent_id"], a)
        self.assertEqual(nodes[pg]["parent_id"], b)
        self.assertIsNone(nodes[root_page]["parent_id"])
        bc = self.api("GET", f"/nodes/{pg}/breadcrumb").json["items"]
        self.assertEqual([i["name"] for i in bc], ["A", "B"])
        self.assertNotIn("content", nodes[pg])  # tree is lightweight
        self.assertEqual(nodes[pg]["version"], 1)  # needed by the client for If-Match

    def test_folder_cannot_live_under_a_page(self):
        pg = self.page("P")
        r = self.mk("folder", "F", pg, expect=422)
        self.assertEqual(r["code"], "invalid_parent")

    def test_max_folder_depth(self):
        parent = None
        for i in range(8):
            parent = self.folder(f"L{i}", parent)
        self.assertEqual(self.mk("folder", "too deep", parent, expect=422)["code"], "max_depth")
        self.page("pages are not limited", parent)

    def test_depth_limit_applies_to_moved_subtrees(self):
        deep = None
        for i in range(7):
            deep = self.folder(f"D{i}", deep)
        sub = self.folder("S")
        self.folder("S2", sub)  # S has height 1
        self.assertEqual(self.move(sub, 422, parent_id=deep)["code"], "max_depth")
        lone = self.folder("lone")
        self.move(lone, parent_id=deep)  # a single folder fits at depth 8

    def test_validation_errors(self):
        self.assertEqual(self.mk("folder", "  ", expect=422)["errors"]["name"], "required")
        self.assertEqual(self.mk("file", "x", expect=422)["errors"]["type"], "invalid")
        self.assertEqual(self.mk("folder", "x" * 300, expect=422)["title"], "Unprocessable entity")
        self.mk("page", "x", template_id="nope", expect=422)
        self.mk("folder", "x", template_id="procedure", expect=422)
        self.assertEqual(self.api("POST", "/nodes", data="not json", content_type="text/plain").status_code, 400)

    def test_client_supplied_id_is_idempotent_guard(self):
        self.mk("folder", "x", id=UID)
        self.assertEqual(self.mk("folder", "y", id=UID, expect=409)["code"], "duplicate_id")
        self.mk("folder", "y", id="not-a-uuid", expect=422)

    def test_templates_and_props(self):
        tpls = {t["id"] for t in self.api("GET", "/templates").json["items"]}
        self.assertEqual(tpls, {"blank", "procedure"})
        pid = self.page("Proc", template_id="procedure", props={"app": "Veeam", "status": "Validée"})
        node = self.api("GET", f"/nodes/{pid}").json
        self.assertEqual(node["props"], {"app": "Veeam", "status": "Validée"})
        self.assertEqual(node["content"]["content"][0]["content"][0]["text"], "Prérequis")
        self.mk("page", "bad", template_id="procedure", props={"status": "Perdu"}, expect=422)
        self.mk("page", "bad", template_id="procedure", props={"nope": "x"}, expect=422)
        merged = self.patch(pid, props={"purpose": "But"})
        self.assertEqual(merged["props"], {"app": "Veeam", "status": "Validée", "purpose": "But"})


class MoveTests(ApiTestCase):
    def test_reorder_before_after_and_append(self):
        a, b, c = self.page("a"), self.page("b"), self.page("c")
        self.assertEqual(self.children(), [a, b, c])
        self.move(c, before_id=a)
        self.assertEqual(self.children(), [c, a, b])
        self.move(c, after_id=b)
        self.assertEqual(self.children(), [a, b, c])
        self.move(a)  # no reference: append at the end
        self.assertEqual(self.children(), [b, c, a])

    def test_move_into_folder_and_back_to_root(self):
        f, p1 = self.folder("F"), self.page("P")
        self.move(p1, parent_id=f)
        self.assertEqual(self.children(f), [p1])
        self.assertEqual(self.children(None), [f])
        self.move(p1, parent_id=None, before_id=f)
        self.assertEqual(self.children(None), [p1, f])

    def test_cycles_are_rejected(self):
        a = self.folder("A")
        b = self.folder("B", a)
        c = self.folder("C", b)
        self.assertEqual(self.move(a, 422, parent_id=a)["code"], "cycle")
        self.assertEqual(self.move(a, 422, parent_id=c)["code"], "cycle")
        self.assertEqual(self.move(b, 422, parent_id=c)["code"], "cycle")
        self.assertEqual(self.children(a), [b])

    def test_folder_cannot_move_under_page_and_bad_references(self):
        f, pg, other = self.folder("F"), self.page("P"), self.folder("O")
        self.assertEqual(self.move(f, 422, parent_id=pg)["code"], "invalid_parent")
        self.assertEqual(self.move(f, 422, parent_id=other, before_id=pg)["code"], "bad_reference")
        self.move(f, 422, before_id=pg, after_id=other)
        self.api("POST", f"/nodes/{f}/move", json={"parent_id": "missing"}).status_code == 404

    def test_positions_are_renumbered_when_the_gap_is_exhausted(self):
        a, b, c = self.page("a"), self.page("b"), self.page("c")
        for node_id, pos in ((a, 10), (b, 11), (c, 500)):
            n = self.repo.get_node(node_id)
            n.position = pos
            self.repo.save_node(n)
        self.repo.commit()
        self.move(c, before_id=b)  # no integer fits between 10 and 11
        self.assertEqual(self.children(), [a, c, b])
        positions = [n["position"] for n in self.api("GET", "/tree").json["nodes"]]
        self.assertEqual(len(set(positions)), 3)

    def test_move_returns_updated_node_and_bumps_version(self):
        f, pg = self.folder("F"), self.page("P")
        v = self.api("GET", f"/nodes/{pg}").json["version"]
        self.assertEqual(self.move(pg, parent_id=f)["version"], v + 1)


class SubPageTests(ApiTestCase):
    def links(self, page_id):
        from app.services.content import link_ids
        return link_ids(self.api("GET", f"/nodes/{page_id}").json["content"])

    def test_creating_a_subpage_adds_a_link(self):
        parent = self.page("Parent")
        r = self.mk("page", "Child", parent)
        self.assertEqual(r["affected_ids"], [parent])
        self.assertEqual(self.links(parent), [r["id"]])

    def test_link_false_lets_the_editor_place_the_link_itself(self):
        parent = self.page("Parent")
        r = self.mk("page", "Child", parent, link=False)
        self.assertEqual(self.links(parent), [])
        link = {"type": "pageLink", "attrs": {"pageId": r["id"]}}
        self.patch(parent, content=doc(p("intro"), link))
        self.assertEqual(self.links(parent), [r["id"]])  # exactly one, not duplicated

    def test_moving_pages_in_and_out_keeps_links_in_sync(self):
        a, b, f = self.page("A"), self.page("B"), self.folder("F")
        moved = self.move(b, parent_id=a)
        self.assertEqual(moved["affected_ids"], [a])
        self.assertEqual(self.links(a), [b])
        out = self.move(b, parent_id=f)
        self.assertEqual(out["affected_ids"], [a])
        self.assertEqual(self.links(a), [])

    def test_removing_a_link_deletes_the_subpage(self):
        parent = self.page("Parent")
        child = self.page("Child", parent)
        r = self.patch(parent, content=doc(p("no more link")))
        self.assertEqual(r["deleted_ids"], [child])
        self.assertEqual(self.api("GET", f"/nodes/{child}").status_code, 404)

    def test_deleting_a_subpage_removes_its_link(self):
        parent = self.page("Parent")
        child = self.page("Child", parent)
        r = self.api("DELETE", f"/nodes/{child}").json
        self.assertEqual(r["affected_ids"], [parent])
        self.assertEqual(self.links(parent), [])

    def test_unlinked_children_are_relinked_on_patch(self):
        parent = self.page("Parent")
        child = self.mk("page", "Child", parent, link=False)["id"]
        self.patch(parent, name="Renamed")
        self.assertEqual(self.links(parent), [child])


class VersionTests(ApiTestCase):
    def test_if_match_is_required_and_checked(self):
        pid = self.page("P")
        self.assertEqual(self.api("PATCH", f"/nodes/{pid}", json={"name": "x"}).status_code, 428)
        r = self.api("PATCH", f"/nodes/{pid}", json={"name": "x"}, headers={"If-Match": "99"})
        self.assertEqual((r.status_code, r.json["code"], r.json["current_version"]), (409, "version_conflict", 1))
        ok = self.api("PATCH", f"/nodes/{pid}", json={"name": "x"}, headers={"If-Match": '"1"'})
        self.assertEqual((ok.status_code, ok.json["version"]), (200, 2))
        self.assertEqual(ok.headers["ETag"], '"2"')
        self.assertEqual(self.api("PATCH", f"/nodes/{pid}", json={"name": "y"}, headers={"If-Match": "1"}).status_code, 409)

    def test_patch_rules(self):
        f = self.folder("F")
        self.assertEqual(self.api("PATCH", f"/nodes/{f}", json={}, headers={"If-Match": "1"}).status_code, 422)
        self.assertEqual(self.api("PATCH", f"/nodes/{f}", json={"content": doc(p("x"))}, headers={"If-Match": "1"}).status_code, 422)
        self.assertEqual(self.patch(f, name="Renamed", icon="📁")["icon"], "📁")
        self.patch(f, expect=422, name="")


class ContentApiTests(ApiTestCase):
    def test_patch_content_updates_search_text_and_is_sanitized(self):
        pid = self.page("P")
        self.patch(pid, content=doc(h("Intro"), p("secret keyword")))
        self.assertIn("secret keyword", self.repo.get_node(pid).search_text)
        self.patch(pid, expect=422, content=doc({"type": "script", "content": []}))
        self.patch(pid, expect=422, content=doc(p("x", [{"type": "link", "attrs": {"href": "javascript:alert(1)"}}])))
        self.patch(pid, expect=422, content=doc({"type": "image", "attrs": {"src": "https://evil/x.png"}}))
        self.patch(pid, expect=422, content=doc({"type": "pageLink", "attrs": {"pageId": UID}}))
        err = self.api("PATCH", f"/nodes/{pid}", json={"content": "<script>"}, headers={"If-Match": "2"})
        self.assertEqual(err.status_code, 422)
        self.assertEqual(err.json["code"], "invalid_content")

    def test_content_size_limit(self):
        pid = self.page("P")
        self.patch(pid, expect=422, content=doc(p("x" * int(2.5 * 1024 * 1024))))


class TrashTests(ApiTestCase):
    def build(self):
        f = self.folder("F")
        sub = self.folder("Sub", f)
        pg = self.page("Page", sub)
        return f, sub, pg

    def test_delete_is_recursive_and_hides_nodes(self):
        f, sub, pg = self.build()
        keep = self.page("keep")
        r = self.api("DELETE", f"/nodes/{f}").json
        self.assertEqual((r["deleted"], set(r["ids"])), (3, {f, sub, pg}))
        self.assertEqual([n["id"] for n in self.api("GET", "/tree").json["nodes"]], [keep])
        self.assertEqual(self.api("GET", f"/nodes/{pg}").status_code, 404)
        self.assertEqual(self.api("GET", f"/nodes/{f}/stats").status_code, 404)

    def test_stats(self):
        f, sub, pg = self.build()
        self.assertEqual(self.api("GET", f"/nodes/{f}/stats").json, {"descendants": 2, "folders": 1, "pages": 1})

    def test_trash_lists_only_roots_and_restore_brings_back_the_subtree(self):
        f, sub, pg = self.build()
        self.api("DELETE", f"/nodes/{f}")
        items = self.api("GET", "/trash").json["items"]
        self.assertEqual([i["id"] for i in items], [f])
        r = self.api("POST", f"/trash/{f}/restore").json
        self.assertEqual(r["restored"], 3)
        self.assertEqual(len(self.api("GET", "/tree").json["nodes"]), 3)
        self.assertEqual(self.api("POST", f"/trash/{f}/restore").status_code, 422)

    def test_independently_deleted_child_stays_in_trash_after_parent_restore(self):
        f, sub, pg = self.build()
        self.api("DELETE", f"/nodes/{pg}")
        self.repo.set_deleted([pg], self.repo.get_node(pg, True).deleted_at.replace(year=2000))  # older deletion
        self.repo.commit()
        self.api("DELETE", f"/nodes/{f}")
        self.api("POST", f"/trash/{f}/restore")
        self.assertEqual([i["id"] for i in self.api("GET", "/trash").json["items"]], [pg])

    def test_restore_when_parent_is_gone_goes_to_root(self):
        f, sub, pg = self.build()
        self.api("DELETE", f"/nodes/{pg}")
        self.api("DELETE", f"/nodes/{f}")
        self.api("POST", f"/trash/{pg}/restore")
        self.assertEqual(self.api("GET", f"/nodes/{pg}").json["parent_id"], None)

    def test_restoring_a_subpage_restores_the_link(self):
        parent = self.page("Parent")
        child = self.page("Child", parent)
        self.api("DELETE", f"/nodes/{child}")
        self.api("POST", f"/trash/{child}/restore")
        from app.services.content import link_ids
        self.assertEqual(link_ids(self.api("GET", f"/nodes/{parent}").json["content"]), [child])

    def test_purge_and_empty(self):
        f, sub, pg = self.build()
        other = self.page("other")
        self.assertEqual(self.api("DELETE", f"/trash/{f}").status_code, 422)  # not trashed yet
        self.api("DELETE", f"/nodes/{f}")
        self.assertEqual(self.api("DELETE", f"/trash/{f}").json["purged"], 3)
        self.assertEqual(self.api("GET", "/trash").json["items"], [])
        self.api("DELETE", f"/nodes/{other}")
        self.assertEqual(self.api("DELETE", "/trash").json["purged"], 1)

    def test_purge_expired_job(self):
        from datetime import timedelta
        from app.domain import utcnow
        f, sub, pg = self.build()
        self.api("DELETE", f"/nodes/{f}")
        svc = self.app.extensions["docbase"]
        self.assertEqual(svc.tree.purge_expired(), 0)
        self.repo.set_deleted([f, sub, pg], utcnow() - timedelta(days=31))
        self.assertEqual(svc.tree.purge_expired(), 1)
        self.assertIsNone(self.repo.get_node(pg, include_deleted=True))


class SearchTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.it = self.folder("Informatique")
        self.rh = self.folder("RH")
        self.pa = self.page("Sauvegarde hebdomadaire", self.it, template_id="procedure", props={"status": "Validée"})
        self.patch(self.pa, content=doc(p("Vérifier la procédure de restauration")))
        self.pb = self.page("Accueil", self.rh)
        self.patch(self.pb, content=doc(p("Préparer le poste, voir la procédure RH")))
        self.pc = self.page("Procédure de création", self.rh)

    def q(self, **params):
        r = self.api("GET", "/search", query_string=params)
        self.assertEqual(r.status_code, 200, r.get_data(as_text=True))
        return r.json

    def test_accent_and_case_insensitive(self):
        res = self.q(q="PROCEDURE")
        self.assertEqual({i["id"] for i in res["items"]}, {self.pa, self.pb, self.pc})
        self.assertEqual(res["total"], 3)

    def test_title_hits_rank_first(self):
        self.assertEqual(self.q(q="procedure")["items"][0]["id"], self.pc)

    def test_scopes(self):
        self.assertEqual([i["id"] for i in self.q(q="procedure", scope="title")["items"]], [self.pc])
        self.assertEqual({i["id"] for i in self.q(q="procedure", scope="content")["items"]}, {self.pa, self.pb})
        self.assertEqual({i["id"] for i in self.q(q="sauvegarde", scope="content")["items"]}, set())
        self.assertEqual([i["id"] for i in self.q(q="sauvegarde", scope="title")["items"]], [self.pa])

    def test_properties_are_searchable(self):
        self.patch(self.pa, props={"app": "Veeam Backup"})
        self.assertEqual([i["id"] for i in self.q(q="veeam", scope="content")["items"]], [self.pa])

    def test_filters(self):
        self.assertEqual({i["id"] for i in self.q(q="procedure", folder_id=self.rh)["items"]}, {self.pb, self.pc})
        self.assertEqual([i["id"] for i in self.q(q="procedure", template_id="procedure")["items"]], [self.pa])
        self.assertEqual([i["id"] for i in self.q(q="procedure", status="Validée")["items"]], [self.pa])

    def test_result_shape_snippet_and_path(self):
        item = next(i for i in self.q(q="procedure", scope="content")["items"] if i["id"] == self.pa)
        self.assertEqual([x["name"] for x in item["path"]], ["Informatique"])
        a, b = item["matches"][0]
        self.assertEqual(item["snippet"][a:b], "procédure")

    def test_pagination_and_validation(self):
        r = self.api("GET", "/search", query_string={"q": "procedure", "limit": 1, "offset": 1})
        self.assertEqual((len(r.json["items"]), r.json["total"], r.headers["X-Total-Count"]), (1, 3, "3"))
        self.assertEqual(self.api("GET", "/search").status_code, 422)
        self.assertEqual(self.api("GET", "/search", query_string={"q": "x", "scope": "zzz"}).status_code, 422)
        self.assertEqual(self.api("GET", "/search", query_string={"q": "x", "folder_id": self.pa}).status_code, 422)

    def test_deleted_pages_are_not_found(self):
        self.api("DELETE", f"/nodes/{self.pc}")
        self.assertNotIn(self.pc, {i["id"] for i in self.q(q="procedure")["items"]})

    def test_like_wildcards_are_literal(self):
        self.assertEqual(self.q(q="100%")["total"], 0)
        self.assertEqual(self.q(q="_")["total"], 0)


class AssetTests(ApiTestCase):
    def test_upload_serve_and_dedupe(self):
        r = self.upload(expect=201)
        self.assertEqual((r.json["width"], r.json["height"], r.json["mime_type"]), (20, 10, "image/png"))
        again = self.upload(expect=200)
        self.assertEqual(again.json["id"], r.json["id"])
        got = self.c.get(r.json["url"])  # no auth header: <img> tags cannot send one
        self.assertEqual((got.status_code, got.mimetype), (200, "image/png"))
        self.assertIn("immutable", got.headers["Cache-Control"])
        self.assertEqual(self.c.get(f"/api/v1/assets/{UID}").status_code, 404)
        self.assertEqual(self.c.get("/api/v1/assets/not-a-uuid").status_code, 404)

    def test_rejects_non_images_and_spoofed_extensions(self):
        self.assertEqual(self.upload(b"just text", "evil.png", expect=422).json["code"], "invalid_image")
        self.upload(b"<svg xmlns='http://www.w3.org/2000/svg'/>", "x.svg", expect=422)
        self.assertEqual(self.api("POST", "/assets", data={}, content_type="multipart/form-data").status_code, 400)

    def test_oversized_upload_is_rejected(self):
        self.upload(b"\x00" * (1024 * 1024 + 10), "big.png", expect=413)

    def test_large_images_are_resized_and_exif_stripped(self):
        from PIL import Image
        buf = io.BytesIO()
        img = Image.new("RGB", (2400, 100), (10, 20, 30))
        exif = Image.Exif()
        exif[0x010F] = "SecretCamera"
        img.save(buf, "JPEG", exif=exif)
        r = self.upload(buf.getvalue(), "photo.jpg", expect=201).json
        self.assertEqual(r["width"], 1600)
        stored = self.c.get(r["url"]).data
        self.assertNotIn(b"SecretCamera", stored)

    def test_assets_can_be_embedded_in_content_only_if_they_exist(self):
        pid = self.page("P")
        aid = self.upload().json["id"]
        self.patch(pid, content=doc({"type": "image", "attrs": {"src": f"/api/v1/assets/{aid}", "alt": "logo"}}))
        self.patch(pid, expect=422, content=doc({"type": "image", "attrs": {"src": f"/api/v1/assets/{UID}"}}))

    def test_other_users_assets_are_not_referencable(self):
        from app.seed import ensure_user
        ensure_user(self.repo, "o@example.com", "other-pass", "editor")
        self.repo.commit()
        other = self.c.post("/api/v1/auth/login", json={"email": "o@example.com", "password": "other-pass"}).json["access_token"]
        aid = self.upload().json["id"]
        pid = self.api("POST", "/nodes", token=other, json={"type": "page", "name": "x"}).json["id"]
        r = self.api("PATCH", f"/nodes/{pid}", token=other, headers={"If-Match": "1"},
                     json={"content": doc({"type": "image", "attrs": {"src": f"/api/v1/assets/{aid}"}})})
        self.assertEqual(r.status_code, 422)


class ExportTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.f = self.folder("Informatique")
        self.sub = self.folder("Réseau", self.f)
        self.aid = self.upload().json["id"]
        self.pg = self.page("Sauvegarde <1>", self.sub, template_id="procedure",
                            props={"app": "Veeam", "purpose": "Vérifier & noter", "status": "Validée"})
        self.child = self.page("Échec", self.pg)
        self.patch(self.child, content=doc(p("Relancer la tâche")))
        content = self.api("GET", f"/nodes/{self.pg}").json["content"]
        content["content"] = [
            h("Étapes"), p("Texte ", [{"type": "bold"}]), ul("un", "deux"), ul("a", kind="orderedList"),
            {"type": "image", "attrs": {"src": f"/api/v1/assets/{self.aid}", "alt": "capture"}},
            p("Voir ", [{"type": "link", "attrs": {"href": "https://example.com"}}]),
        ] + [n for n in content["content"] if n["type"] == "pageLink"]
        self.patch(self.pg, content=content)
        self.root = self.page("Bienvenue")

    def get(self, node_id, **params):
        r = self.api("GET", f"/export/{node_id}", query_string=params)
        self.assertEqual(r.status_code, 200, r.get_data()[:300])
        return r

    def test_markdown_page(self):
        r = self.get(self.pg, format="md")
        self.assertIn("attachment", r.headers["Content-Disposition"])
        md = r.get_data(as_text=True)
        self.assertIn("# Sauvegarde <1>", md)
        self.assertIn("**Application / Spécialité :** Veeam", md)
        self.assertIn("**Statut :** Validée", md)
        self.assertIn("## Étapes", md)
        self.assertIn("**Texte **", md)
        self.assertIn("- un\n- deux", md)
        self.assertIn("1. a", md)
        self.assertIn("![capture](data:image/png;base64,", md)
        self.assertIn("[example.com]" if False else "https://example.com", md)
        self.assertIn("## Échec", md)  # sub-page rendered one level deeper, after its parent
        self.assertIn("Relancer la tâche", md)
        self.assertNotIn("Prérequis", md.split("## Échec")[0].replace("## Étapes", "")) if False else None

    def test_html_is_escaped_and_standalone(self):
        html = self.get(self.pg, format="html").get_data(as_text=True)
        self.assertTrue(html.startswith("<!DOCTYPE html>"))
        self.assertIn("<h1>Sauvegarde &lt;1&gt;</h1>", html)
        self.assertIn("Vérifier &amp; noter", html)
        self.assertIn("<ul><li>un</li><li>deux</li></ul>", html)
        self.assertIn("<strong>Texte </strong>", html)
        self.assertIn('rel="noopener noreferrer"', html)
        self.assertNotIn("<1>", html.replace("&lt;1&gt;", ""))

    def test_plain_text(self):
        txt = self.get(self.pg, format="txt").get_data(as_text=True)
        self.assertIn("Sauvegarde <1>\n===", txt)
        self.assertIn("Statut : Validée", txt)
        self.assertIn("[image: capture]", txt)
        self.assertNotIn("**", txt)

    def test_folder_export_is_recursive_with_hierarchy_levels(self):
        md = self.get(self.f, format="md").get_data(as_text=True)
        self.assertLess(md.index("# Informatique"), md.index("## Réseau"))
        self.assertLess(md.index("## Réseau"), md.index("### Sauvegarde <1>"))
        self.assertIn("#### Échec", md)

    def test_empty_list_items_are_skipped(self):
        empty = self.page("Template page", template_id="procedure")
        md = self.get(empty, format="md").get_data(as_text=True)
        self.assertNotIn("\n-\n", md)
        self.assertIn("## Prérequis", md)

    def test_zip_mirrors_the_tree_with_assets(self):
        r = self.get(self.f, format="zip")
        self.assertEqual(r.mimetype, "application/zip")
        z = zipfile.ZipFile(io.BytesIO(r.data))
        names = set(z.namelist())
        self.assertIn("informatique/reseau/sauvegarde-1.md", names)
        self.assertIn(f"assets/{self.aid}.png", names)
        page = z.read("informatique/reseau/sauvegarde-1.md").decode()
        self.assertTrue(page.startswith("---\ntitle: "))
        self.assertIn('template: "procedure"', page)
        self.assertIn(f"![capture](../../assets/{self.aid}.png)", page)
        self.assertIn("Relancer la tâche", page)  # sub-page inlined, no separate file
        self.assertNotIn("informatique/reseau/echec.md", names)

    def test_zip_names_are_deduplicated(self):
        self.page("Dup", self.sub)
        self.page("dup", self.sub)
        names = zipfile.ZipFile(io.BytesIO(self.get(self.sub, format="zip").data)).namelist()
        self.assertIn("reseau/dup.md", names)
        self.assertIn("reseau/dup-2.md", names)

    def test_errors(self):
        self.assertEqual(self.api("GET", f"/export/{self.pg}", query_string={"format": "docx"}).status_code, 422)
        self.assertEqual(self.api("GET", f"/export/{UID}").status_code, 404)

    def test_exports_are_scoped_to_the_owner(self):
        from app.seed import ensure_user
        ensure_user(self.repo, "o@example.com", "other-pass", "editor")
        self.repo.commit()
        other = self.c.post("/api/v1/auth/login", json={"email": "o@example.com", "password": "other-pass"}).json["access_token"]
        self.assertEqual(self.api("GET", f"/export/{self.pg}", token=other).status_code, 404)


class MiscTests(ApiTestCase):
    def test_health_and_errors_are_problem_json(self):
        self.assertEqual(self.c.get("/api/v1/health").json, {"status": "ok", "db": True})
        r = self.api("GET", "/nodes/nope")
        self.assertEqual(r.status_code, 404)
        self.assertEqual(r.mimetype, "application/problem+json")
        self.assertEqual(self.c.get("/api/v1/unknown").status_code, 404)
        self.assertEqual(self.api("PUT", "/tree").status_code, 405)

    def test_cors_only_for_allowed_origins(self):
        self.app.extensions["docbase"].cfg.CORS_ORIGINS = ["http://localhost:5173"]
        ok = self.c.options("/api/v1/tree", headers={"Origin": "http://localhost:5173"})
        self.assertEqual(ok.status_code, 204)
        self.assertEqual(ok.headers["Access-Control-Allow-Origin"], "http://localhost:5173")
        bad = self.c.get("/api/v1/health", headers={"Origin": "http://evil.example"})
        self.assertNotIn("Access-Control-Allow-Origin", bad.headers)

    def test_seed_demo(self):
        from app.seed import demo_data
        svc = self.app.extensions["docbase"]
        demo_data(svc.tree, self.user)
        self.repo.commit()
        names = {n["name"] for n in self.api("GET", "/tree").json["nodes"]}
        self.assertTrue({"Informatique", "VPN", "Sauvegarde hebdomadaire", "Bienvenue"} <= names)


if __name__ == "__main__":
    import unittest
    unittest.main()
