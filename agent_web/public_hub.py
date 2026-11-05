"""A2A-P0C-DOOR-A1: verified loopback static hosting, no API or live feed.

Build input is explicit public source and the synthetic Observatory build only.
"""
from __future__ import annotations
import argparse
from hashlib import sha256
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import threading
from urllib.parse import urlsplit
from observatory.model import canonical_json
ROOT = Path(__file__).resolve().parents[1]
HEADERS = {'Content-Security-Policy': "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'none'; object-src 'none'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'", 'X-Content-Type-Options': 'nosniff', 'X-Frame-Options': 'DENY', 'Referrer-Policy': 'no-referrer', 'Permissions-Policy': 'accelerometer=(), camera=(), geolocation=(), gyroscope=(), magnetometer=(), microphone=(), payment=(), usb=()', 'Cross-Origin-Resource-Policy': 'same-origin'}
TYPES = {'.html': 'text/html; charset=utf-8', '.md': 'text/markdown; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.css': 'text/css; charset=utf-8', '.svg': 'image/svg+xml', '.png': 'image/png', '.webp': 'image/webp', '.woff2': 'font/woff2'}

def digest(data):
    return sha256(data).hexdigest()

def assemble(output: Path, dashboard: Path, release_id: str):
    """Explicit inputs, no overwrite, private-source crawling or network calls."""
    if not re.fullmatch('[a-z0-9][a-z0-9-]{2,80}', release_id) or output.exists():
        raise ValueError('New output directory and valid release identity required')
    for name in ('index.html', 'favicon.svg', 'icons.svg'):
        if not (dashboard / name).is_file() or (dashboard / name).is_symlink():
            raise ValueError('Qualified dashboard build required')
    if not (dashboard / 'assets').is_dir():
        raise ValueError('Dashboard assets required')
    files = {}

    def publish(route, data):
        relative = route.lstrip('/')
        ext = PurePosixPath(relative).suffix
        if not relative or '..' in PurePosixPath(relative).parts or route in files or (ext not in TYPES) or (len(data) > 10 * 1024 * 1024):
            raise ValueError('Invalid/duplicate public artifact')
        files[route] = {'path': 'public/' + relative, 'bytes': len(data), 'sha256': digest(data), 'type': TYPES[ext]}
        target = output / 'public' / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    home = ROOT / 'apps/agent-hub/public'
    toby = (ROOT / 'apps/observatory-dashboard/src/assets/keepers/blue-toby.png').read_bytes()
    css = (home / 'pond.css').read_bytes()
    grove = (home / 'living-grove.webp').read_bytes()
    built_toby = list((dashboard / 'assets').glob('blue-toby-*.png'))
    if len(built_toby) != 1 or digest(built_toby[0].read_bytes()) != digest(toby):
        raise ValueError('Authentic Blue Toby build mismatch')
    toby_route = '/dashboard/assets/' + built_toby[0].name
    css_route = '/assets/pond-' + digest(css)[:16] + '.css'
    publish(css_route, css)
    grove_route = '/assets/living-grove-' + digest(grove)[:16] + '.webp'
    publish(grove_route, grove)
    index = (home / 'index.html').read_text().replace('{{TOBY_ASSET}}', toby_route).replace('{{POND_CSS}}', css_route).replace('{{GROVE_ASSET}}', grove_route)
    if '{{' in index:
        raise ValueError('Unresolved public asset reference')
    publish('/index.html', index.encode())
    publish('/pond/guide.md', (home / 'pond/guide.md').read_bytes())
    publish('/favicon.svg', (dashboard / 'favicon.svg').read_bytes())
    for path in sorted(dashboard.rglob('*')):
        if path.is_symlink():
            raise ValueError('Dashboard symlinks forbidden')
        if not path.is_file():
            continue
        rel = path.relative_to(dashboard).as_posix()
        if rel in ('404.html', '_headers'):
            continue
        if rel not in ('index.html', 'favicon.svg', 'icons.svg') and (not rel.startswith('assets/')):
            raise ValueError('Unexpected dashboard artifact')
        publish('/dashboard/' + rel, path.read_bytes())
    publish('/404.html', b'<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>404 - Agent Pond</title><body><main><h1>404 - Route not found</h1><p>This static Agent Pond has no enrollment, Agent Card or live protocol API.</p><a href="/">Return to Agent Pond</a></main></body></html>')
    routes = dict(sorted(files.items()))
    source = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    dirty = bool(subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT, text=True).strip())
    runtime = Path(__file__).read_bytes()
    standalone = runtime.replace(b'from observatory.model import canonical_json', b'def canonical_json(value):\n return json.dumps(value,sort_keys=True,ensure_ascii=True,separators=(",",":"),allow_nan=False)', 1)
    (output / 'runtime').mkdir()
    (output / 'runtime/public_hub.py').write_bytes(standalone)
    manifest = {'format': 'toadaid.agent-hub.static.v1', 'releaseId': release_id, 'sourceCommit': source, 'sourceDirty': dirty, 'headers': HEADERS, 'routes': routes, 'blueTobySourceSha256': digest(toby), 'runtimeSha256': digest(standalone), 'runtimeSourceSha256': digest(runtime), 'contentRootSha256': digest(canonical_json(routes).encode()), 'syntheticOnly': True, 'authorityFlags': {'executionAuthorized': False, 'publicationAuthorized': False, 'deploymentAuthorized': False, 'agentRegistrationActive': False, 'publicDirectoryExposed': False}}
    raw = (canonical_json(manifest) + '\n').encode()
    (output / 'release-manifest.json').write_bytes(raw)
    (output / 'release-manifest.sha256').write_text(digest(raw) + '  release-manifest.json\n')
    return manifest

def load_release(root: Path, expected: str):
    raw = (root / 'release-manifest.json').read_bytes()
    if digest(raw) != expected:
        raise ValueError('Manifest checksum mismatch')
    m = json.loads(raw)
    if m.get('format') != 'toadaid.agent-hub.static.v1' or m.get('headers') != HEADERS:
        raise ValueError('Unsupported static policy')
    if m.get('syntheticOnly') is not True or m.get('authorityFlags') != {'executionAuthorized': False, 'publicationAuthorized': False, 'deploymentAuthorized': False, 'agentRegistrationActive': False, 'publicDirectoryExposed': False}:
        raise ValueError('Synthetic invariants required')
    if digest((root / 'runtime/public_hub.py').read_bytes()) != m['runtimeSha256']:
        raise ValueError('Runtime integrity mismatch')
    if digest(canonical_json(m['routes']).encode()) != m['contentRootSha256']:
        raise ValueError('Inventory mismatch')
    assets = {}
    for route, row in m['routes'].items():
        path = root / row['path']
        if not route.startswith('/') or row['path'] != 'public' + route or '..' in PurePosixPath(route).parts:
            raise ValueError('Invalid static route')
        if path.is_symlink() or not path.resolve().is_relative_to((root / 'public').resolve()):
            raise ValueError('Static file escaped release')
        data = path.read_bytes()
        if digest(data) != row['sha256'] or len(data) != row['bytes'] or row['type'] != TYPES.get(path.suffix):
            raise ValueError('Artifact integrity mismatch')
        assets[route] = (data, row['type'])
    if not all((r in assets for r in ('/index.html', '/dashboard/index.html', '/pond/guide.md', '/404.html'))):
        raise ValueError('Required surfaces absent')
    return (m, assets)

def make_server(root: Path, expected: str, port: int=0, allow_preview: bool=False):
    m, assets = load_release(root, expected)
    if m.get('sourceDirty') is not False and (not allow_preview):
        raise ValueError('Uncommitted preview cannot run as a production release')

    class Handler(BaseHTTPRequestHandler):
        server_version = 'ToadAidStatic/1'
        sys_version = ''

        def log_message(self, *_args):
            pass

        def respond(self, status, data=b'', content_type='text/plain; charset=utf-8', location=None, cache='no-store'):
            self.send_response(status)
            for name, value in HEADERS.items():
                self.send_header(name, value)
            self.send_header('Content-Type', content_type)
            self.send_header('Cache-Control', cache)
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Connection', 'close')
            if status == 405:
                self.send_header('Allow', 'GET, HEAD')
            if location:
                self.send_header('Location', location)
            self.end_headers()
            if self.command != 'HEAD':
                self.wfile.write(data)
            self.close_connection = True

        def send_error(self, code, message=None, explain=None):
            return self.respond(code, b'Request unavailable')

        def do_GET(self):
            host = self.headers.get('Host', '')
            if host not in ('agent.toadaid.org', f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}'):
                return self.respond(421, b'Unrecognized static host')
            try:
                value = urlsplit(self.path)
            except ValueError:
                return self.respond(400, b'Invalid static path')
            if value.scheme or value.netloc or len(self.path) > 2048 or ('%' in value.path) or ('\\' in value.path) or ('..' in value.path) or ('//' in value.path):
                return self.respond(400, b'Invalid static path')
            if value.path == '/dashboard':
                return self.respond(308, location='/dashboard/' + ('?' + value.query if value.query else ''))
            route = {'/': '/index.html', '/dashboard/': '/dashboard/index.html'}.get(value.path, value.path)
            found = assets.get(route)
            if found is None:
                return self.respond(404, *assets['/404.html'])
            immutable = re.fullmatch('/(?:dashboard/)?assets/[^/]+-[A-Za-z0-9_-]{8,}\\.[a-z0-9]+', route)
            return self.respond(200, *found, cache='public, max-age=31536000, immutable' if immutable else 'no-store')
        do_HEAD = do_GET

        def do_POST(self):
            return self.respond(405, b'This public site has no mutation API')
        do_PUT = do_POST
        do_PATCH = do_POST
        do_DELETE = do_POST
        do_OPTIONS = do_POST
        do_TRACE = do_POST
        do_CONNECT = do_POST

    class StaticServer(ThreadingHTTPServer):
        slots = threading.BoundedSemaphore(16)

        def process_request(self, request, address):
            if not self.slots.acquire(blocking=False):
                self.shutdown_request(request)
                return
            try:
                super().process_request(request, address)
            except BaseException:
                self.slots.release()
                raise

        def process_request_thread(self, request, address):
            try:
                super().process_request_thread(request, address)
            finally:
                self.slots.release()

        def get_request(self):
            sock, address = super().get_request()
            sock.settimeout(10)
            return (sock, address)
    server = StaticServer(('127.0.0.1', port), Handler)
    server.daemon_threads = True
    server.release_manifest = m
    return server

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    build = commands.add_parser('build')
    build.add_argument('--output', type=Path, required=True)
    build.add_argument('--release-id', required=True)
    serve = commands.add_parser('serve')
    serve.add_argument('--release', type=Path, required=True)
    serve.add_argument('--manifest-sha256', required=True)
    serve.add_argument('--port', type=int, default=4328)
    serve.add_argument('--preview', action='store_true')
    args = parser.parse_args()
    if args.command == 'build':
        m = assemble(args.output, ROOT / 'apps/observatory-dashboard/dist', args.release_id)
        print(canonical_json({'releaseId': m['releaseId'], 'files': len(m['routes']), 'sourceCommit': m['sourceCommit'], 'sourceDirty': m['sourceDirty']}))
    else:
        if not 0 <= args.port <= 65535:
            parser.error('Invalid loopback port')
        with make_server(args.release, args.manifest_sha256, args.port, args.preview) as server:
            print(canonical_json({'port': server.server_port, 'releaseId': server.release_manifest['releaseId']}), flush=True)
            server.serve_forever()
if __name__ == '__main__':
    main()
