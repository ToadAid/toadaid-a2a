"""A2A-P0C-DOOR-A1: static HTTP/refusal tests with a synthetic dashboard stand-in.

Actual compiled React/subpath behavior is separately qualified by Playwright.
"""
import http.client
import json
from pathlib import Path
import shutil
import tempfile
import threading
import unittest

from agent_web.public_hub import ROOT, HEADERS, assemble, digest, load_release, make_server
from observatory.model import canonical_json


class PublicHubTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='agent-hub-http-')
        cls.base = Path(cls.temp.name)
        dashboard = cls.base / 'dashboard-build'
        (dashboard / 'assets').mkdir(parents=True)
        (dashboard / 'index.html').write_text('<!doctype html><html><title>Synthetic fixture</title><script src="./assets/index-12345678.js"></script></html>')
        (dashboard / 'assets/index-12345678.js').write_text('/* synthetic static test asset */')
        (dashboard / 'assets/index-12345678.css').write_text('body{color:green}')
        shutil.copyfile(ROOT / 'apps/observatory-dashboard/src/assets/keepers/blue-toby.png', dashboard / 'assets/blue-toby-12345678.png')
        (dashboard / 'favicon.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg"></svg>')
        (dashboard / 'icons.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg"></svg>')
        (dashboard / '_headers').write_text('metadata must not be served')
        (dashboard / '404.html').write_text('obsolete dashboard fallback')
        cls.output = cls.base / 'release'
        cls.manifest = assemble(cls.output, dashboard, 'agent-hub-unit-fixture')
        cls.grove_route = next(route for route in cls.manifest['routes'] if route.startswith('/assets/living-grove-'))
        cls.sha = digest((cls.output / 'release-manifest.json').read_bytes())
        cls.server = make_server(cls.output, cls.sha, allow_preview=True)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown(); cls.thread.join(); cls.server.server_close(); cls.temp.cleanup()

    def request(self, path, method='GET', headers=None):
        client = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=3)
        client.request(method, path, headers=headers or {})
        result = client.getresponse()
        status, values, body = result.status, dict(result.getheaders()), result.read()
        client.close()
        return status, values, body

    def test_home_dashboard_and_markdown_are_distinct_public_resources(self):
        for path, content in [('/', b'One pond.'), ('/dashboard/?view=activity', b'Synthetic fixture'), ('/pond/guide.md', b'# Welcome to ToadAid Agent Pond')]:
            status, headers, body = self.request(path)
            self.assertEqual(status, 200); self.assertIn(content, body)
            self.assertNotIn('Set-Cookie', headers); self.assertNotIn('Access-Control-Allow-Origin', headers)
        self.assertEqual(self.request('/pond/guide.md')[1]['Content-Type'], 'text/markdown; charset=utf-8')
        self.assertNotIn(b'<!doctype', self.request('/pond/guide.md')[2])

    def test_actual_headers_cover_html_markdown_js_css_images_and_errors(self):
        paths = ['/', '/pond/guide.md', self.grove_route, '/dashboard/assets/index-12345678.js', '/dashboard/assets/index-12345678.css', '/dashboard/assets/blue-toby-12345678.png', '/favicon.svg', '/missing']
        for path in paths:
            _, headers, _ = self.request(path)
            for key, value in HEADERS.items(): self.assertEqual(headers[key], value, (path, key))
        self.assertEqual(self.request('/dashboard/assets/index-12345678.js')[1]['Content-Type'], 'text/javascript; charset=utf-8')
        self.assertIn('immutable', self.request('/dashboard/assets/index-12345678.js')[1]['Cache-Control'])
        self.assertEqual(self.request('/')[1]['Cache-Control'], 'no-store')
        self.assertEqual(self.request(self.grove_route)[1]['Content-Type'], 'image/webp')
        self.assertIn('immutable', self.request(self.grove_route)[1]['Cache-Control'])

    def test_no_spa_fallback_for_unknown_private_or_protocol_paths(self):
        for path in ['/missing/deep/', '/dashboard/missing/', '/dashboard/_headers', '/.well-known/agent-card.json', '/pond/apply', '/api/agents', '/.git/config', '/.env', '/release-manifest.json', '/runtime/public_hub.py']:
            status, _, body = self.request(path)
            self.assertEqual(status, 404, path); self.assertNotIn(b'Synthetic fixture', body)
        for path in ['/%2e%2e/.env', '/a/../.env', '/%2fapi']:
            self.assertEqual(self.request(path)[0], 400, path)

    def test_mutation_methods_never_create_an_application_or_agent_api(self):
        for method in ['POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS', 'TRACE']:
            status, headers, body = self.request('/pond/apply', method)
            self.assertEqual(status, 405); self.assertEqual(headers['Allow'], 'GET, HEAD')
            self.assertNotIn('Set-Cookie', headers); self.assertIn(b'no mutation API', body)

    def test_head_redirect_and_origin_host_validation(self):
        status, headers, body = self.request('/pond/guide.md', 'HEAD')
        self.assertEqual(status, 200); self.assertEqual(body, b''); self.assertGreater(int(headers['Content-Length']), 1)
        status, headers, _ = self.request('/dashboard?view=security')
        self.assertEqual(status, 308); self.assertEqual(headers['Location'], '/dashboard/?view=security')
        self.assertEqual(self.request('/', headers={'Host': 'foreign.example.test'})[0], 421)
        self.assertEqual(self.request('/', headers={'Host': 'agent.toadaid.org', 'Cookie': 'synthetic-private=must-not-echo'})[0], 200)
        self.assertNotIn(b'must-not-echo', self.request('/', headers={'Cookie': 'synthetic-private=must-not-echo'})[2])

    def test_release_integrity_and_production_dirty_source_guard(self):
        with self.assertRaises(ValueError): load_release(self.output, '0' * 64)
        copy = self.base / 'tampered'
        shutil.copytree(self.output, copy)
        (copy / 'public/dashboard/assets/index-12345678.js').write_text('tampered')
        with self.assertRaises(ValueError): load_release(copy, self.sha)
        (copy / 'public/dashboard/assets/index-12345678.js').unlink()
        with self.assertRaises(FileNotFoundError): load_release(copy, self.sha)
        preview = self.base / 'uncommitted'
        shutil.copytree(self.output, preview)
        manifest = dict(self.manifest, sourceDirty=True)
        raw = (canonical_json(manifest) + '\n').encode()
        (preview / 'release-manifest.json').write_bytes(raw)
        with self.assertRaisesRegex(ValueError, 'Uncommitted'): make_server(preview, digest(raw))

    def test_immutable_release_inventory_and_authentic_branding(self):
        compile((self.output / 'runtime/public_hub.py').read_bytes(), 'standalone-runtime', 'exec')
        self.assertTrue(self.manifest['syntheticOnly'])
        self.assertTrue(all(value is False for value in self.manifest['authorityFlags'].values()))
        self.assertEqual(self.manifest['blueTobySourceSha256'], digest((ROOT / 'apps/observatory-dashboard/src/assets/keepers/blue-toby.png').read_bytes()))
        self.assertEqual(self.manifest['routes'][self.grove_route]['sha256'], '7421abcd531b2ed60c5251ca17bcfe6f585c75d3b2fb53698cd3b965b455f6e9')
        self.assertEqual(self.request(self.grove_route)[2], (ROOT / 'apps/agent-hub/public/living-grove.webp').read_bytes())
        self.assertNotIn('/dashboard/_headers', self.manifest['routes'])
        self.assertNotIn('/dashboard/404.html', self.manifest['routes'])
        with self.assertRaises(ValueError): assemble(self.output, self.base / 'dashboard-build', 'overwrite-is-forbidden')
