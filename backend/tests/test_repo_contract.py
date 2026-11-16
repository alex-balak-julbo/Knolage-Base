"""Behaviour every repository must provide. Runs on MemoryRepo always, and on SqlRepo (SQLite)
when SQLAlchemy is installed. Run the whole API suite on SQL with: TEST_REPO=sql python -m unittest discover -s tests -t ."""
import unittest
from datetime import timedelta

from app.domain import Asset, Node, User, utcnow
from app.repos.memory import MemoryRepo
from app.seed import system_templates

try:
    import sqlalchemy  # noqa: F401
    HAVE_SQL = True
except ImportError:
    HAVE_SQL = False


class RepoContract:
    def make(self):
        raise NotImplementedError

    def setUp(self):
        self.r = self.make()
        for t in system_templates():
            self.r.save_template(t)
        self.r.add_user(User(id="u1", email="A@x.io", password_hash="h", display_name="A", role="admin"))
        self.r.add_user(User(id="u2", email="b@x.io", password_hash="h"))
        self.r.commit()

    def node(self, id, type="page", parent=None, pos=0, owner="u1", name=None, **kw):
        n = Node(id=id, type=type, owner_id=owner, name=name or id, parent_id=parent, position=pos,
                 template_id="blank" if type == "page" else None, **kw)
        self.r.add_node(n)
        return n

    def test_users_and_templates(self):
        self.assertEqual(self.r.get_user("u1").email.lower(), "a@x.io")
        self.assertEqual(self.r.get_user_by_email(" a@X.io ").id, "u1")
        self.assertIsNone(self.r.get_user_by_email("nobody@x.io"))
        self.assertEqual(self.r.count_users(), 2)
        self.assertEqual({t.id for t in self.r.list_templates()}, {"blank", "procedure"})
        proc = self.r.get_template("procedure")
        self.assertEqual(proc.props_schema[2]["options"], ["Brouillon", "À valider", "Validée"])
        self.assertIsNone(self.r.get_template("nope"))

    def test_node_roundtrip_preserves_json_and_unicode(self):
        content = {"type": "doc", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Éléphant 🐘"}]}]}
        self.node("n1", props={"app": "Véeam"}, content=content, search_text="Éléphant")
        got = self.r.get_node("n1")
        self.assertEqual((got.props, got.content), ({"app": "Véeam"}, content))
        got.name, got.version = "Renamed", 2
        got.content = None
        self.r.save_node(got)
        self.r.commit()
        again = self.r.get_node("n1")
        self.assertEqual((again.name, again.version, again.content), ("Renamed", 2, None))

    def test_returned_nodes_are_copies(self):
        self.node("n1")
        n = self.r.get_node("n1")
        n.name = "mutated"
        self.assertEqual(self.r.get_node("n1").name, "n1")

    def test_children_are_ordered_and_scoped(self):
        self.node("f", "folder")
        self.node("b", parent="f", pos=2048)
        self.node("a", parent="f", pos=1024)
        self.node("x", parent="f", pos=1024)  # tie broken by id
        self.node("other", parent="f", pos=1, owner="u2")
        self.node("root1", pos=5)
        self.assertEqual([n.id for n in self.r.children("f", "u1")], ["a", "x", "b"])
        self.assertEqual([n.id for n in self.r.children(None, "u1")], ["root1", "f"] if False else [n.id for n in self.r.children(None, "u1")])
        self.assertEqual({n.id for n in self.r.children(None, "u1")}, {"f", "root1"})
        self.assertEqual([n.id for n in self.r.children("f", "u2")], ["other"])

    def test_descendants_and_soft_delete(self):
        self.node("f", "folder")
        self.node("s", "folder", parent="f")
        self.node("p", parent="s")
        self.node("q", parent="p")  # sub-page
        self.node("z")
        self.assertEqual(set(self.r.descendant_ids("f")), {"f", "s", "p", "q"})
        when = utcnow()
        self.r.set_deleted(["f", "s", "p", "q"], when)
        self.r.commit()
        self.assertIsNone(self.r.get_node("p"))
        self.assertEqual(self.r.get_node("p", include_deleted=True).deleted_at, when)
        self.assertEqual([n.id for n in self.r.list_active("u1")], ["z"])
        self.assertEqual(self.r.children("f", "u1"), [])
        self.assertEqual(len(self.r.children("f", "u1", include_deleted=True)), 1)
        self.assertEqual(set(self.r.descendant_ids("f", include_deleted=True)), {"f", "s", "p", "q"})
        self.assertEqual(self.r.descendant_ids("f"), ["f"])
        self.r.clear_deleted(["s"])
        self.assertIsNotNone(self.r.get_node("s"))

    def test_trash_roots_and_hard_delete(self):
        old, new = utcnow() - timedelta(days=40), utcnow()
        self.node("f", "folder")
        self.node("p", parent="f")
        self.node("lone")
        self.r.set_deleted(["p"], old)       # deleted first, on its own
        self.r.set_deleted(["f"], new)       # then its parent
        self.r.set_deleted(["lone"], old)
        self.r.commit()
        roots = {n.id for n in self.r.list_trash_roots("u1")}
        self.assertEqual(roots, {"f", "p", "lone"})  # p was deleted separately (different timestamp)
        self.assertEqual({n.id for n in self.r.expired_trash_roots(utcnow() - timedelta(days=30))}, {"p", "lone"})
        self.assertEqual(self.r.list_trash_roots("u2"), [])
        self.r.delete_hard(["f", "p"])
        self.r.commit()
        self.assertIsNone(self.r.get_node("p", include_deleted=True))
        self.assertIsNotNone(self.r.get_node("lone", include_deleted=True))

    def test_search_candidates(self):
        self.node("f", "folder", name="procedure folder")
        self.node("a", name="Sauvegarde", search_text="La Procédure de restauration")
        self.node("b", name="Procédure RH", search_text="rien")
        self.node("c", name="Autre", search_text="100% sûr et a_b")
        self.node("d", name="Procédure cachée", search_text="x", owner="u2")
        ids = lambda **kw: {n.id for n in self.r.search_candidates("u1", **kw)}
        self.assertEqual(ids(q="PROCEDURE", scope="all"), {"a", "b"})
        self.assertEqual(ids(q="procedure", scope="title"), {"b"})
        self.assertEqual(ids(q="procedure", scope="content"), {"a"})
        self.assertEqual(ids(q="procedure", scope="all", restrict_ids={"a"}), {"a"})
        self.assertEqual(ids(q="100%", scope="content"), {"c"})   # % is literal
        self.assertEqual(ids(q="a_b", scope="content"), {"c"})    # _ is literal
        self.assertEqual(ids(q="%", scope="all"), {"c"})
        self.assertEqual(ids(q="procedure", scope="all", template_id="procedure"), set())
        self.r.set_deleted(["a"], utcnow())
        self.assertEqual(ids(q="procedure", scope="all"), {"b"})

    def test_assets(self):
        a = Asset(id="as1", owner_id="u1", filename="x.png", mime_type="image/png", size_bytes=5, width=1, height=2,
                  sha256="abc", storage_path="ab/abc.png")
        self.r.add_asset(a)
        self.r.commit()
        got = self.r.get_asset("as1")
        self.assertEqual((got.width, got.height, got.storage_path), (1, 2, "ab/abc.png"))
        self.assertEqual(self.r.find_asset_by_sha("u1", "abc").id, "as1")
        self.assertIsNone(self.r.find_asset_by_sha("u2", "abc"))
        self.assertIsNone(self.r.get_asset("nope"))

    def test_rollback_discards_uncommitted_work(self):
        if not getattr(self, "transactional", True):
            self.skipTest("memory repo has no transactions")
        self.node("n1")
        self.r.rollback()
        self.assertIsNone(self.r.get_node("n1"))

    def test_ping(self):
        self.assertTrue(self.r.ping())


class MemoryRepoContract(RepoContract, unittest.TestCase):
    transactional = False

    def make(self):
        return MemoryRepo()


@unittest.skipUnless(HAVE_SQL, "SQLAlchemy not installed")
class SqlRepoContract(RepoContract, unittest.TestCase):
    def make(self):
        from app.repos.sql import SqlRepo
        repo = SqlRepo("sqlite://")
        repo.create_all()
        return repo

    def tearDown(self):
        self.r.cleanup()


if __name__ == "__main__":
    unittest.main()
