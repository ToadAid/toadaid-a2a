"""P0-WEB-02: explicitly started loopback-only synthetic content-negotiation fixture.

NOT a deployed website, A2A gateway, lore export, action service or identity system.
All formats render the same projected fields of a deliberately fictional record.
"""
import argparse
import html
import json
import re
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

PATH = "/fixture/synthetic-lore-resource"
MAX_ACCEPT_BYTES = 512
SOURCE = (Path(__file__).resolve().parents[1] /
          "contracts/agent-web/examples/synthetic-lore-resource.v0.json")
PUBLIC_FIELDS = ("recordId", "status", "title", "summary", "claims", "provenance")
FORMATS = ("text/html", "text/markdown", "application/json")
MIME = {
    "text/html": "text/html; charset=utf-8",
    "text/markdown": "text/markdown; charset=utf-8",
    "application/json": "application/json; charset=utf-8",
}
QVALUE = re.compile(r"(?:0(?:\.[0-9]{0,3})?|1(?:\.0{0,3})?)\Z")


class FixtureError(ValueError):
    pass


def public_record():
    """Fail closed unless the source stays synthetic and non-publishable."""
    item = json.loads(SOURCE.read_text(encoding="utf-8"))
    if (item.get("kind") != "toadaid-synthetic-lore-resource-example"
            or item.get("status") != "SYNTHETIC-NONCANONICAL-NOT-PUBLISHED"
            or item.get("realDeed") is not False
            or item.get("canonicalLore") is not False
            or item.get("publicPublicationAuthorized") is not False
            or item.get("privateDataIncluded") is not False
            or item.get("indexingAllowed") is not False
            or not isinstance(item.get("claims"), list)
            or not isinstance(item.get("provenance"), list)):
        raise FixtureError("source no longer qualifies as synthetic test material")
    return {key: item[key] for key in PUBLIC_FIELDS}


def negotiate(accept):
    """Small deterministic subset of HTTP Accept, with explicit refusal."""
    if accept is None or not accept.strip():
        accept = "*/*"
    if not isinstance(accept, str) or len(accept.encode("utf-8")) > MAX_ACCEPT_BYTES:
        raise FixtureError("invalid or oversized Accept")
    ranges = []
    for segment in accept.split(","):
        tokens = [part.strip() for part in segment.split(";")]
        media = tokens[0].lower()
        if not media or media.count("/") != 1 or len(tokens) > 2:
            raise FixtureError("malformed Accept")
        if not re.fullmatch(r"[a-z*.+-]+/[a-z*.+-]+", media):
            raise FixtureError("malformed media type")
        quality = 1.0
        if len(tokens) == 2:
            if not tokens[1].lower().startswith("q="):
                raise FixtureError("unsupported media parameter")
            raw_q = tokens[1][2:]
            if not QVALUE.fullmatch(raw_q):
                raise FixtureError("invalid q value")
            quality = float(raw_q)
        specificity = (0 if media == "*/*" else 1 if media.endswith("/*") else 2)
        ranges.append((media, quality, specificity))
    # Most-specific range determines quality for each supported representation.
    candidates = []
    for priority, wanted in enumerate(FORMATS):
        relevant = [(specificity, quality) for media, quality, specificity in ranges
                    if media == wanted or media == "*/*" or
                    (media.endswith("/*") and wanted.startswith(media[:-1]))]
        if not relevant:
            continue
        high_specificity = max(v[0] for v in relevant)
        quality = max(q for specificity, q in relevant if specificity == high_specificity)
        if quality > 0:
            candidates.append((quality, -priority, wanted))
    if not candidates:
        return None
    return max(candidates)[2]


def encode_view(item):
    payload = json.dumps(item, sort_keys=True, indent=2, ensure_ascii=False)
    return payload


def representation(item, media):
    """Same projected JSON facts in every representation, never alternate truth."""
    payload = encode_view(item)
    if media == "application/json":
        return (payload + "\n").encode("utf-8")
    if media == "text/markdown":
        # Dynamically choose a fence that cannot occur in the JSON payload.
        longest = max((len(m.group()) for m in re.finditer(r"`+", payload)), default=0)
        fence = "`" * max(3, longest + 1)
        return (f"# {item['title']}\n\n{item['summary']}\n\n"
                "Synthetic example only; not a real deed, canonical lore, or public publication.\n\n"
                f"{fence}json\n{payload}\n{fence}\n").encode("utf-8")
    if media == "text/html":
        title = html.escape(item["title"], quote=True)
        summary = html.escape(item["summary"], quote=True)
        safe_json = html.escape(payload, quote=True)
        return (
            "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
            f"<title>{title}</title></head><body><main>"
            f"<h1>{title}</h1><p>{summary}</p>"
            "<p>Fictional example only; not a real deed, canonical lore or public publication.</p>"
            f"<pre id=\"resource-json\">{safe_json}</pre>"
            "</main></body></html>\n"
        ).encode("utf-8")
    raise FixtureError("unsupported format")


class LoopbackFixture(HTTPServer):
    allow_reuse_address = False

    def __init__(self, port=0):
        super().__init__(("127.0.0.1", port), FixtureHandler)
        if self.server_address[0] != "127.0.0.1":
            self.server_close()
            raise FixtureError("non-loopback bind refused")

    def get_request(self):
        socket, address = super().get_request()
        socket.settimeout(3.0)
        return socket, address


class FixtureHandler(BaseHTTPRequestHandler):
    server_version = "ToadAidSyntheticPublisher/0.1"
    sys_version = ""

    def log_message(self, _format, *args):
        return  # Avoid logging potentially sensitive, untrusted request-derived data.

    def _send(self, status, body, content_type):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Vary", "Accept")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'none'; base-uri 'none'")
        self.send_header("X-Robots-Tag", "noindex, nofollow")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _read_only(self):
        if self.path != PATH:
            self._send(404, b"not found\n", "text/plain; charset=utf-8")
            return
        accepts = self.headers.get_all("Accept", [])
        if len(accepts) > 1:
            self._send(400, b"invalid Accept\n", "text/plain; charset=utf-8")
            return
        try:
            media = negotiate(accepts[0] if accepts else None)
        except FixtureError:
            self._send(400, b"invalid Accept\n", "text/plain; charset=utf-8")
            return
        if media is None:
            self._send(406, b"no acceptable representation\n", "text/plain; charset=utf-8")
            return
        try:
            data = representation(public_record(), media)
        except (FixtureError, OSError, KeyError, ValueError, TypeError):
            self._send(503, b"synthetic source unavailable\n", "text/plain; charset=utf-8")
            return
        self._send(200, data, MIME[media])

    do_GET = _read_only
    do_HEAD = _read_only

    def do_POST(self):
        self._send(405, b"method not allowed\n", "text/plain; charset=utf-8")
        self.close_connection = True

    do_PUT = do_POST
    do_PATCH = do_POST
    do_DELETE = do_POST
    do_OPTIONS = do_POST


def main(argv=None):
    p = argparse.ArgumentParser(description="Explicit localhost-only synthetic publishing fixture; NOT DEPLOYED")
    p.add_argument("--port", type=int, default=0)
    args = p.parse_args(argv)
    # Validate synthetic data before opening a socket.
    public_record()
    with LoopbackFixture(args.port) as server:
        print("LOCAL_SYNTHETIC_NOT_DEPLOYED http://127.0.0.1:%s%s" %
              (server.server_address[1], PATH), flush=True)
        server.serve_forever(poll_interval=0.05)


if __name__ == "__main__":
    main()
