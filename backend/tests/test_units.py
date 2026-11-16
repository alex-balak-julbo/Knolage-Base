import unittest

from app.services import content as C
from app.services.ordering import position_between
from app.services.search import snippet
from app.textutil import fold, slugify
from tests.helpers import doc, h, p, ul

UID = "11111111-1111-4111-8111-111111111111"


class ContentTests(unittest.TestCase):
    def test_valid_document_roundtrip(self):
        d = doc(h("Titre", 1), p("Bonjour", [{"type": "bold"}, {"type": "link", "attrs": {"href": "https://a.b"}}]),
                ul("a", "b"), ul("x", kind="orderedList"))
        out = C.validate_doc(d)
        self.assertEqual(out["content"][1]["content"][0]["marks"][1]["attrs"]["href"], "https://a.b")

    def test_rejects_unknown_node_and_mark(self):
        with self.assertRaises(C.ContentError):
            C.validate_doc(doc({"type": "script"}))
        with self.assertRaises(C.ContentError):
            C.validate_doc(doc(p("x", [{"type": "color", "attrs": {"c": "red"}}])))

    def test_rejects_unsafe_links(self):
        for href in ("javascript:alert(1)", "data:text/html,x", "//evil.com", "vbscript:x"):
            with self.assertRaises(C.ContentError, msg=href):
                C.validate_doc(doc(p("x", [{"type": "link", "attrs": {"href": href}}])))

    def test_image_src_must_be_local_asset(self):
        img = lambda src: doc({"type": "image", "attrs": {"src": src}})
        with self.assertRaises(C.ContentError):
            C.validate_doc(img("https://evil.com/x.png"))
        with self.assertRaises(C.ContentError):
            C.validate_doc(img("data:image/png;base64,AAAA"))
        C.validate_doc(img(f"/api/v1/assets/{UID}"))
        with self.assertRaises(C.ContentError):
            C.validate_doc(img(f"/api/v1/assets/{UID}"), asset_ok=lambda i: False)

    def test_structure_limits(self):
        with self.assertRaises(C.ContentError):
            C.validate_doc(doc(h("x", 3)))  # level 3 not allowed
        with self.assertRaises(C.ContentError):
            C.validate_doc({"type": "doc", "content": [{"type": "listItem"}]})  # wrong parent
        with self.assertRaises(C.ContentError):
            C.validate_doc(doc(p("x" * 200)), max_bytes=100)
        deep = {"type": "bulletList", "content": [{"type": "listItem", "content": []}]}
        node = deep
        for _ in range(12):
            inner = {"type": "bulletList", "content": [{"type": "listItem", "content": []}]}
            node["content"][0]["content"] = [inner]
            node = inner
        with self.assertRaises(C.ContentError):
            C.validate_doc(doc(deep))

    def test_text_attributes_are_whitelisted(self):
        out = C.validate_doc(doc({"type": "paragraph", "attrs": {"style": "x"}, "content": [
            {"type": "text", "text": "a", "onclick": "x"}]}))
        self.assertNotIn("attrs", out["content"][0])
        self.assertNotIn("onclick", out["content"][0]["content"][0])

    def test_extract_text_and_links(self):
        d = doc(h("Titre"), p("Un"), ul("a", "b"), {"type": "pageLink", "attrs": {"pageId": UID}})
        self.assertEqual(C.extract_text(d), "Titre\nUn\na\nb")
        self.assertEqual(C.link_ids(d), [UID])
        self.assertEqual(C.link_ids(C.remove_links(d, [UID])), [])
        self.assertEqual(C.link_ids(C.append_link(C.empty_doc(), UID)), [UID])


class OrderingTests(unittest.TestCase):
    def test_position_between(self):
        self.assertEqual(position_between(None, None), 1024)
        self.assertEqual(position_between(None, 1024), 0)
        self.assertEqual(position_between(1024, None), 2048)
        self.assertEqual(position_between(1024, 2048), 1536)
        self.assertIsNone(position_between(5, 6))
        self.assertIsNone(position_between(5, 5))


class TextTests(unittest.TestCase):
    def test_fold(self):
        self.assertEqual(fold("Procédure ÉTÉ"), "procedure ete")
        self.assertEqual(slugify("Création d’un compte !"), "creation-d-un-compte")
        self.assertEqual(slugify("???"), "untitled")

    def test_snippet_offsets_survive_accents(self):
        text = "x" * 100 + " La Procédure de sauvegarde " + "y" * 100
        sn, matches = snippet(text, "procedure")
        self.assertEqual(len(matches), 1)
        a, b = matches[0]
        self.assertEqual(sn[a:b], "Procédure")
        self.assertTrue(sn.startswith("…") and sn.endswith("…"))


if __name__ == "__main__":
    unittest.main()
