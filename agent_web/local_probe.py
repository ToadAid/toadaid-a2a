"""P0B-B: explicitly started, loopback-only A2A 1.0 JSON-RPC probe.

This is NOT Agent0, an authenticated gateway, a public endpoint or a TCK-certified server.
The sole SendMessage skill replies with a fixed static acknowledgment, after a bounded
private append-only journal has been fsynced. No models, MCP, wallets or external I/O.
"""

import argparse
import fcntl
import hashlib
import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
import stat
import uuid

MAX_REQUEST_BYTES = 8192
MAX_INPUT_CHARS = 1024
MAX_JOURNAL_BYTES = 2 * 1024 * 1024  # fail closed rather than fill developer host
CARD_PATH = "/.well-known/agent-card.json"
RPC_PATH = "/a2a"
ACK = "Local-only A2A probe acknowledged; no tools, AI model, or execution authority."


class Refusal(ValueError):
    """Unsafe or invalid local-probe input."""


def _canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(",", ":")).encode("ascii")


def _json_no_duplicates(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise Refusal("duplicate JSON object field")
        value[key] = item
    return value


def _parse(raw):
    if not isinstance(raw, bytes) or len(raw) > MAX_REQUEST_BYTES:
        raise Refusal("request exceeds size bound")
    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=_json_no_duplicates,
                          parse_constant=lambda _: (_ for _ in ()).throw(Refusal("non-finite JSON number")))
    except Refusal:
        raise
    except (UnicodeError, json.JSONDecodeError, ValueError, RecursionError) as exc:
        raise Refusal("invalid JSON") from exc


def _valid_id(value):
    return (type(value) in (str, int) and not isinstance(value, bool)
            and (isinstance(value, int) or 0 < len(value) <= 64))


def _request_parts(request):
    """Conservative subset: one plain text part, no task/context continuation."""
    if not isinstance(request, dict) or request.get("jsonrpc") != "2.0":
        raise Refusal("invalid JSON-RPC request")
    if not _valid_id(request.get("id")) or request.get("method") != "SendMessage":
        raise Refusal("unsupported or invalid RPC operation")
    if set(request) - {"jsonrpc", "id", "method", "params"}:
        raise Refusal("unexpected RPC envelope field")
    params = request.get("params")
    if not isinstance(params, dict) or set(params) != {"message"}:
        raise Refusal("only new-message requests are supported")
    message = params["message"]
    if not isinstance(message, dict) or set(message) != {"messageId", "role", "parts"}:
        raise Refusal("unsupported message shape")
    message_id = message["messageId"]
    if not isinstance(message_id, str) or not 0 < len(message_id) <= 128:
        raise Refusal("invalid messageId")
    if message["role"] != "ROLE_USER":
        raise Refusal("only ROLE_USER is accepted")
    parts = message["parts"]
    if not isinstance(parts, list) or len(parts) != 1:
        raise Refusal("only one text part is supported")
    part = parts[0]
    if not isinstance(part, dict) or not set(part).issubset({"text", "mediaType"}):
        raise Refusal("only text parts supported")
    if part.get("mediaType", "text/plain") != "text/plain":
        raise Refusal("unsupported media type")
    text = part.get("text")
    if not isinstance(text, str) or not 0 < len(text) <= MAX_INPUT_CHARS:
        raise Refusal("invalid text part")
    return message_id


def agent_card(port):
    """Advertise only the real loopback JSON-RPC skill; never use Host header."""
    if type(port) is not int or not 0 < port <= 65535:
        raise Refusal("invalid loopback port")
    return {
        "name": "ToadAid local probe (NOT DEPLOYED)",
        "description": "Explicitly started localhost-only fixed-response test; not Agent0 or a public service.",
        "supportedInterfaces": [{"url": f"http://127.0.0.1:{port}{RPC_PATH}",
                                 "protocolBinding": "JSONRPC", "protocolVersion": "1.0"}],
        "version": "0.0.1-local",
        "capabilities": {"streaming": False, "pushNotifications": False,
                         "extendedAgentCard": False},
        "defaultInputModes": ["text/plain"],
        "defaultOutputModes": ["text/plain"],
        "skills": [{"id": "local-fixed-ack", "name": "Local fixed acknowledgment",
                    "description": "Returns a static acknowledgment for a single bounded text message; no tasks or tools.",
                    "tags": ["local-only", "synthetic", "read-only"]}],
    }


class Journal:
    """Bounded private replay journal; fail closed on tamper/incomplete state."""

    def __init__(self, directory):
        root = Path(directory)
        if not root.is_absolute() or root.resolve(strict=False) != root:
            raise Refusal("journal directory must be an absolute symlink-free path")
        if root.is_symlink() or not root.is_dir():
            raise Refusal("journal directory must be a real directory")
        meta = root.stat(follow_symlinks=False)
        if not stat.S_ISDIR(meta.st_mode) or meta.st_uid != os.getuid() or stat.S_IMODE(meta.st_mode) != 0o700:
            raise Refusal("journal directory must be owned by operator with mode 0700")
        self._path = root / "local-probe-events.jsonl"
        flags = os.O_RDWR | os.O_APPEND | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0)
        self._fd = os.open(self._path, flags, 0o600)
        self._closed = False
        self._poisoned = False
        try:
            try:
                fcntl.flock(self._fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise Refusal("journal already has an active writer") from exc
            meta = os.fstat(self._fd)
            if not stat.S_ISREG(meta.st_mode) or meta.st_uid != os.getuid() or stat.S_IMODE(meta.st_mode) != 0o600:
                raise Refusal("journal must be owned regular file mode 0600")
            self._seen = {}
            self._last_hash = "0" * 64
            self._load()
        except BaseException:
            os.close(self._fd)
            self._closed = True
            raise

    def _load(self):
        size = os.fstat(self._fd).st_size
        if size > MAX_JOURNAL_BYTES:
            raise Refusal("journal size limit exceeded")
        os.lseek(self._fd, 0, os.SEEK_SET)
        raw = b""
        while len(raw) < size:
            chunk = os.read(self._fd, size - len(raw))
            if not chunk:
                raise Refusal("journal changed during read")
            raw += chunk
        if raw and not raw.endswith(b"\n"):
            raise Refusal("incomplete journal record")
        for line in raw.splitlines():
            try:
                event = _parse(line)
            except Refusal as exc:
                raise Refusal("invalid journal record") from exc
            if not isinstance(event, dict) or set(event) != {"messageId", "requestHash", "response", "prev", "digest"}:
                raise Refusal("invalid journal fields")
            payload = {k: event[k] for k in ("messageId", "requestHash", "response", "prev")}
            expected = hashlib.sha256(_canonical(payload)).hexdigest()
            if event["prev"] != self._last_hash or event["digest"] != expected:
                raise Refusal("journal chain integrity failure")
            message_id = event["messageId"]
            if not isinstance(message_id, str) or message_id in self._seen:
                raise Refusal("journal duplicate messageId")
            if not isinstance(event["requestHash"], str) or not isinstance(event["response"], dict):
                raise Refusal("invalid journal payload")
            self._seen[message_id] = (event["requestHash"], event["response"])
            self._last_hash = expected

    def response_for(self, request, message_id):
        if self._poisoned:
            raise Refusal("journal not available after write failure")
        request_hash = hashlib.sha256(_canonical(request["params"]["message"])).hexdigest()
        if message_id in self._seen:
            old_hash, old_response = self._seen[message_id]
            if request_hash != old_hash:
                raise Refusal("conflicting replay messageId")
            return old_response
        # No prompt-dependent response: no model, tools or interpretation.
        answer = {"message": {"messageId": str(uuid.uuid4()), "contextId": str(uuid.uuid4()),
                              "role": "ROLE_AGENT", "parts": [{"text": ACK, "mediaType": "text/plain"}]}}
        event = {"messageId": message_id, "requestHash": request_hash,
                 "response": answer, "prev": self._last_hash}
        digest = hashlib.sha256(_canonical(event)).hexdigest()
        event["digest"] = digest
        line = _canonical(event) + b"\n"
        if os.fstat(self._fd).st_size + len(line) > MAX_JOURNAL_BYTES:
            raise Refusal("journal size bound exceeded")
        try:
            # One synchronous operator-local server, single writer.
            if os.write(self._fd, line) != len(line):
                raise OSError("partial journal write")
            os.fsync(self._fd)  # append *before* response is delivered
        except OSError as exc:
            self._poisoned = True
            raise Refusal("journal write refused") from exc
        self._last_hash = digest
        self._seen[message_id] = (request_hash, answer)
        return answer

    def close(self):
        if not self._closed:
            os.close(self._fd)
            self._closed = True


class LocalServer(HTTPServer):
    allow_reuse_address = False

    def get_request(self):
        connection, address = super().get_request()
        connection.settimeout(3.0)
        return connection, address

    def __init__(self, journal, port=0):
        self.journal = journal
        super().__init__(("127.0.0.1", port), LocalHandler)
        if self.server_address[0] != "127.0.0.1":
            self.server_close()
            raise Refusal("server binding escaped loopback")


class LocalHandler(BaseHTTPRequestHandler):
    server_version = "ToadAidLocalProbe/0.1"
    sys_version = ""

    def log_message(self, _format, *args):
        # Deliberately discard request-derived log output.
        return

    def _send(self, status, payload, *, cache="no-store"):
        body = _canonical(payload)
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", cache)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path != CARD_PATH:
            self._send(404, {"error": "not found"})
            return
        self._send(200, agent_card(self.server.server_address[1]))

    def do_POST(self):
        if self.path != RPC_PATH:
            self._send(404, {"error": "not found"})
            return
        if self.headers.get("Transfer-Encoding") is not None:
            self._send(400, {"error": "streaming request bodies not supported"})
            return
        length = self.headers.get("Content-Length")
        if length is None or not length.isascii() or not length.isdecimal() or len(length) > 6:
            self._send(411, {"error": "bounded Content-Length required"})
            return
        count = int(length)
        if count == 0 or count > MAX_REQUEST_BYTES:
            self._send(413, {"error": "request body exceeds bound"})
            self.close_connection = True
            return
        if self.headers.get("Content-Type", "").lower().split(";", 1)[0].strip() != "application/json":
            self._send(415, {"error": "JSON required"})
            self.close_connection = True
            return
        if self.headers.get("A2A-Version") != "1.0":
            self._send(400, {"jsonrpc": "2.0", "id": None,
                             "error": {"code": -32001, "message": "A2A version not supported"}})
            self.close_connection = True
            return
        raw = self.rfile.read(count)
        try:
            request = _parse(raw)
            message_id = _request_parts(request)
            response = self.server.journal.response_for(request, message_id)
        except Refusal as exc:
            self._send(400, {"jsonrpc": "2.0", "id": None,
                             "error": {"code": -32602, "message": str(exc)}})
            return
        self._send(200, {"jsonrpc": "2.0", "id": request["id"], "result": response})

    def do_PUT(self):
        self._send(405, {"error": "method not allowed"})

    do_DELETE = do_PUT
    do_PATCH = do_PUT
    do_OPTIONS = do_PUT


def main(argv=None):
    parser = argparse.ArgumentParser(description="EXPLICIT LOCAL TEST ONLY, never a public gateway")
    parser.add_argument("--journal-dir", type=Path, required=True,
                        help="existing operator-owned mode 0700 directory (outside public repo)")
    parser.add_argument("--port", type=int, default=0, help="loopback port; 0 chooses free ephemeral port")
    options = parser.parse_args(argv)
    journal = Journal(options.journal_dir)
    try:
        with LocalServer(journal, options.port) as server:
            print("LOCAL_ONLY_NOT_DEPLOYED http://127.0.0.1:%d%s" % (server.server_address[1], CARD_PATH),
                  flush=True)
            server.serve_forever(poll_interval=0.05)
    finally:
        journal.close()


if __name__ == "__main__":
    main()
