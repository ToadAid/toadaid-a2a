"""Qualify every assembled public byte through a disposable HTTP origin.

Offline, no credentials or external network. This is not CDN/deployment evidence.
"""
import argparse
import http.client
import json
from pathlib import Path
import re
import threading
from agent_web.public_hub import HEADERS, digest, make_server


def qualify(root, checksum):
    server = make_server(root, checksum)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    receipts = []
    try:
        def request(path, method='GET'):
            connection = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=5)
            connection.request(method, path)
            response = connection.getresponse()
            data = response.read()
            headers = dict(response.getheaders())
            for key, value in HEADERS.items():
                assert headers.get(key) == value, (path, key)
            assert not any(key.lower() in ('set-cookie', 'access-control-allow-origin') for key in headers)
            connection.close()
            return response.status, headers, data
        for route, row in server.release_manifest['routes'].items():
            status, headers, data = request(route)
            assert status == 200 and digest(data) == row['sha256'] and headers['Content-Type'] == row['type'], route
            if row['type'].startswith(('text/', 'image/svg')):
                assert not re.search(rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY|\bgh[pousr]_[A-Za-z0-9]{30,}|\bsb_secret_[A-Za-z0-9_-]{20,}', data), route
            receipts.append({'route': route, 'status': status, 'type': headers['Content-Type'], 'sha256': digest(data), 'securityHeaders': True})
        for route in ('/', '/dashboard/', '/pond/guide.md'):
            assert request(route)[0] == 200
        for route in ('/.well-known/agent-card.json', '/pond/apply', '/api/agents', '/dashboard/missing/', '/dashboard/assets/missing.js', '/.env', '/runtime/public_hub.py', '/release-manifest.json'):
            assert request(route)[0] == 404, route
        for method in ('POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS', 'TRACE', 'CONNECT'):
            assert request('/pond/apply', method)[0] == 405, method
        return {'scope': 'disposable-loopback-only-not-production', 'releaseId': server.release_manifest['releaseId'],
            'sourceCommit': server.release_manifest['sourceCommit'], 'manifestSha256': checksum, 'assets': receipts,
            'reservedPathsRefused': True, 'mutationsRefused': True, 'privateKeyPatternScan': 'no matches',
            'syntheticOnly': True, 'productionDeploymentVerified': False}
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--release', required=True, type=Path)
    parser.add_argument('--manifest-sha256', required=True)
    parser.add_argument('--receipt', required=True, type=Path)
    args = parser.parse_args()
    result = qualify(args.release, args.manifest_sha256)
    with args.receipt.open('x') as handle:
        json.dump(result, handle, indent=2)
        handle.write('\n')
    print(json.dumps({'releaseId': result['releaseId'], 'assetsQualified': len(result['assets']), 'receipt': str(args.receipt)}))


if __name__ == '__main__':
    main()
