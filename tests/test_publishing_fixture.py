"""P0-WEB-02: actual loopback HTTP content negotiation and synthetic parity checks."""
import html
import http.client
import json
from pathlib import Path
import re
import tempfile
import threading
import unittest
from unittest import mock

from agent_web.publishing_fixture import (
    FixtureError, LoopbackFixture, PATH, PUBLIC_FIELDS, negotiate,
    public_record, representation
)


class NegotiationUnitTests(unittest.TestCase):
    def test_default_representation(self):
        self.assertEqual(negotiate(None), "text/html")
        self.assertEqual(negotiate("*/*"), "text/html")

    def test_explicit_markdown_and_json(self):
        self.assertEqual(negotiate("text/markdown"), "text/markdown")
        self.assertEqual(negotiate("application/json"), "application/json")

    def test_weighted_preferences(self):
        self.assertEqual(negotiate("text/html;q=0.2, text/markdown;q=0.9"), "text/markdown")
        self.assertEqual(negotiate("application/json;q=1, text/markdown;q=0.8"), "application/json")

    def test_specific_zero_quality_overrides_wildcard(self):
        self.assertEqual(negotiate("text/*;q=1, text/markdown;q=0"), "text/html")

    def test_unacceptable_returns_none(self):
        self.assertIsNone(negotiate("application/xml"))
        self.assertIsNone(negotiate("text/html;q=0, text/markdown;q=0, application/json;q=0"))

    def test_invalid_and_oversized_accept_refused(self):
        invalid = ("text/html;q=1.1", "text/html;q=-1", "text/html;q=nan",
                   "text/html; charset=utf-8", "text/html;q=0.1234",
                   "text/html;;q=0.2", ",text/html", "text/html," + "a" * 600)
        for value in invalid:
            with self.subTest(value=value[:45]), self.assertRaises(FixtureError):
                negotiate(value)

    def test_projection_excludes_private_extras(self):
        with tempfile.TemporaryDirectory() as tmp:
            original = json.loads(
                (Path(__file__).resolve().parents[1] /
                 "contracts/agent-web/examples/synthetic-lore-resource.v0.json").read_text()
            )
            original["privateSecret"] = "SENTINEL_MUST_NOT_PUBLISH"
            source = Path(tmp) / "synthetic.json"
            source.write_text(json.dumps(original))
            with mock.patch("agent_web.publishing_fixture.SOURCE", source):
                view = public_record()
            self.assertNotIn("privateSecret", view)
            self.assertEqual(set(view), set(PUBLIC_FIELDS))
            for media in ("text/html", "text/markdown", "application/json"):
                self.assertNotIn("SENTINEL_MUST_NOT_PUBLISH", representation(view, media).decode())

    def test_non_synthetic_input_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            original = json.loads(
                (Path(__file__).resolve().parents[1] /
                 "contracts/agent-web/examples/synthetic-lore-resource.v0.json").read_text()
            )
            original["realDeed"] = True
            source = Path(tmp) / "unsafe.json"
            source.write_text(json.dumps(original))
            with mock.patch("agent_web.publishing_fixture.SOURCE", source):
                with self.assertRaisesRegex(FixtureError, "synthetic"):
                    public_record()


class HTTPRepresentationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = LoopbackFixture(0)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.thread.join(timeout=3)
        cls.server.server_close()

    def call(self, method="GET", path=PATH, accept=None, headers=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.server.server_address[1], timeout=3)
        try:
            final = dict(headers or {})
            if accept is not None:
                final["Accept"] = accept
            conn.request(method, path, headers=final)
            reply = conn.getresponse()
            return reply.status, dict(reply.getheaders()), reply.read()
        finally:
            conn.close()

    def test_listens_only_on_loopback(self):
        self.assertEqual(self.server.server_address[0], "127.0.0.1")

    def test_three_representations_have_same_exact_public_json(self):
        expected = public_record()
        j_status, j_head, j_raw = self.call(accept="application/json")
        md_status, md_head, md_raw = self.call(accept="text/markdown")
        h_status, h_head, h_raw = self.call(accept="text/html")
        self.assertEqual((j_status, md_status, h_status), (200, 200, 200))
        self.assertEqual(json.loads(j_raw), expected)
        markdown = md_raw.decode("utf-8")
        match = re.search(r"`{3,}json\n(.*?)\n`{3,}", markdown, re.DOTALL)
        self.assertIsNotNone(match)
        self.assertEqual(json.loads(match.group(1)), expected)
        markup = h_raw.decode("utf-8")
        match = re.search(r'<pre id="resource-json">(.*?)</pre>', markup, re.DOTALL)
        self.assertIsNotNone(match)
        self.assertEqual(json.loads(html.unescape(match.group(1))), expected)
        for heads, typ in ((j_head, "application/json"), (md_head, "text/markdown"),
                           (h_head, "text/html")):
            self.assertTrue(heads["Content-Type"].startswith(typ))
            self.assertEqual(heads["Vary"], "Accept")
            self.assertEqual(heads["Cache-Control"], "no-store")
            self.assertEqual(heads["X-Robots-Tag"], "noindex, nofollow")
            self.assertEqual(heads["X-Content-Type-Options"], "nosniff")
        for value in (j_raw, md_raw, h_raw):
            self.assertNotIn(b"SENTINEL_MUST_NOT_PUBLISH", value)
            self.assertNotIn(b"publicPublicationAuthorized", value)

    def test_html_escapes_untrusted_title(self):
        source = public_record()
        source["title"] = '<img src=x onerror="alert(1)">'
        markup = representation(source, "text/html").decode()
        self.assertIn("&lt;img", markup)
        self.assertNotIn("<img src=", markup)

    def test_default_html_without_accept(self):
        status, headers, body = self.call()
        self.assertEqual(status, 200)
        self.assertTrue(headers["Content-Type"].startswith("text/html"))
        self.assertIn(b"Fictional", body)

    def test_head_matches_content_length_without_body(self):
        for media in ("text/html", "text/markdown", "application/json"):
            with self.subTest(media=media):
                status, heads, body = self.call("HEAD", accept=media)
                self.assertEqual(status, 200)
                self.assertEqual(body, b"")
                self.assertEqual(heads["Content-Length"],
                                 str(len(representation(public_record(), media))))

    def test_json_preference_with_q(self):
        status, headers, body = self.call(accept="text/html;q=0.4, application/json;q=0.9")
        self.assertEqual(status, 200)
        self.assertTrue(headers["Content-Type"].startswith("application/json"))
        self.assertEqual(json.loads(body), public_record())

    def test_unsupported_format_returns_406(self):
        status, heads, body = self.call(accept="application/xml")
        self.assertEqual(status, 406)
        self.assertEqual(heads["Vary"], "Accept")
        self.assertNotIn(b"Fictional", body)

    def test_malformed_accept_returns_400(self):
        status, _, body = self.call(accept="text/markdown;q=2")
        self.assertEqual(status, 400)
        self.assertNotIn(b"recordId", body)

    def test_oversized_accept_returns_400(self):
        self.assertEqual(self.call(accept="text/html," + "x" * 550)[0], 400)

    def test_unknown_routes_no_information(self):
        for route in ("/.well-known/agent-card.json", "/llms.txt",
                      "/siteai.json", "/actions/request-capability", PATH + "?raw=1"):
            with self.subTest(route=route):
                status, _, body = self.call(path=route)
                self.assertEqual(status, 404)
                self.assertNotIn(b"Fictional", body)

    def test_methods_cannot_change_state(self):
        for method in ("POST", "PUT", "PATCH", "DELETE", "OPTIONS"):
            with self.subTest(method=method):
                self.assertEqual(self.call(method=method)[0], 405)

    def test_host_header_does_not_change_source(self):
        status, headers, body = self.call(accept="application/json",
                                          headers={"Host": "hostile.example"})
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body), public_record())
        self.assertNotIn(b"hostile.example", body)


if __name__ == "__main__":
    unittest.main()
