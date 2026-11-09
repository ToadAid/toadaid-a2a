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
import threading
import time
from urllib.parse import urlsplit
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


from agent_web.envelope import validate_envelope, EnvelopeRefusal
from admission.gate import (
    ADAPTER_ID_MAX_CHARS,
    RegisteredAgentGate,
    synthetic_caller_credential,
    synthetic_caller_verifier,
    synthetic_registration_adapter,
    AdmissionJournal,
    ParticipationRefused,
    AdmissionRefused
)
from admission.lifecycle import synthetic_lifecycle_source
from observatory.model import ObservatoryRefusal
from agent_web.conversation import CONVERSATION_HANDLERS
import datetime

# Opaque synthetic caller credentials — fixtures, NOT real identities.
_CRED_A = synthetic_caller_credential("fixture-caller-a")
_CRED_B = synthetic_caller_credential("fixture-caller-b")

# Explicit mapping of permitted transport-level synthetic bearer tokens to credentials.
# Only explicitly provisioned labels are accepted; unknown labels are never dynamically created.
# NOTE: Public fixture strings and synthetic credentials are NOT real authentication secrets.
_PROVISIONED_CREDENTIALS = {
    "fixture-caller-a": _CRED_A,
    "fixture-caller-b": _CRED_B,
}

_ADMISSION_DECISIONS = {
    "agent-a": {
        "kind": "toadaid-a2a-registration-decision",
        "agentRef": "agent-a", "tenantRef": "tenant-alpha", "ownerRef": "owner-alpha",
        "registrationStatus": "registered", "credentialGeneration": 1, "revocationEpoch": 1,
        "framework": "unspecified", "adapterId": "synthetic-offline-registration-adapter",
        "decisionObservedAtUtc": "2026-11-09T00:00:00Z", "evidenceExpiresAtUtc": "2026-11-09T01:00:00Z",
        "participationScopes": ["a2a-message-receive", "a2a-message-send"],
        "authorityFlags": {
            "executionAuthorized": False, "toolUseAuthorized": False, "paymentAuthorized": False,
            "deploymentAuthorized": False, "agentRegistrationChangeAuthorized": False, "publicDirectoryExposed": False
        }
    },
    "agent-b": {
        "kind": "toadaid-a2a-registration-decision",
        "agentRef": "agent-b", "tenantRef": "tenant-alpha", "ownerRef": "owner-beta",
        "registrationStatus": "registered", "credentialGeneration": 1, "revocationEpoch": 1,
        "framework": "unspecified", "adapterId": "synthetic-offline-registration-adapter",
        "decisionObservedAtUtc": "2026-11-09T00:00:00Z", "evidenceExpiresAtUtc": "2026-11-09T01:00:00Z",
        "participationScopes": ["a2a-message-receive", "a2a-message-send"],
        "authorityFlags": {
            "executionAuthorized": False, "toolUseAuthorized": False, "paymentAuthorized": False,
            "deploymentAuthorized": False, "agentRegistrationChangeAuthorized": False, "publicDirectoryExposed": False
        }
    }
}

_LIFECYCLE_STATES = {
    "agent-a": {
        "kind": "toadaid-a2a-credential-lifecycle-state",
        "agentRef": "agent-a", "tenantRef": "tenant-alpha", "ownerRef": "owner-alpha",
        "lifecycleStatus": "registered", "currentCredentialGeneration": 1, "currentRevocationEpoch": 1,
        "observedAtUtc": "2026-11-09T00:00:00Z"
    },
    "agent-b": {
        "kind": "toadaid-a2a-credential-lifecycle-state",
        "agentRef": "agent-b", "tenantRef": "tenant-alpha", "ownerRef": "owner-beta",
        "lifecycleStatus": "registered", "currentCredentialGeneration": 1, "currentRevocationEpoch": 1,
        "observedAtUtc": "2026-11-09T00:00:00Z"
    }
}

_CALLER_BINDINGS = {
    _CRED_A: {"agentRef": "agent-a", "tenantRef": "tenant-alpha", "ownerRef": "owner-alpha"},
    _CRED_B: {"agentRef": "agent-b", "tenantRef": "tenant-alpha", "ownerRef": "owner-beta"}
}

def strict_synthetic_verifier(metadata, signature, sender_id):
    """Explicitly injected test-only verifier checking expected synthetic credentials."""
    expected = f"synthetic_signature_for_{sender_id}"
    return signature == expected

def build_synthetic_gate(clock=None):
    if clock is None:
        clock = lambda: datetime.datetime.now(datetime.timezone.utc)
        
    now = clock()
    # Observation must be within LIFECYCLE_MAX_OBSERVATION_AGE_SECONDS (300s)
    observed = (now - datetime.timedelta(seconds=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    expires = (now + datetime.timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    
    import copy
    fresh_decisions = copy.deepcopy(_ADMISSION_DECISIONS)
    fresh_states = copy.deepcopy(_LIFECYCLE_STATES)
    
    for d in fresh_decisions.values():
        d["decisionObservedAtUtc"] = observed
        d["evidenceExpiresAtUtc"] = expires
        
    for s in fresh_states.values():
        s["observedAtUtc"] = observed

    return RegisteredAgentGate(
        trusted_registration_adapter=synthetic_registration_adapter(fresh_decisions),
        trusted_caller_verifier=synthetic_caller_verifier(_CALLER_BINDINGS),
        trusted_lifecycle_source=synthetic_lifecycle_source(fresh_states),
        now=clock,
        journal=AdmissionJournal()
    )

def _request_parts(request):
    """Conservative subset: validates raw legacy payload or extracts envelope."""
    if not isinstance(request, dict) or request.get("jsonrpc") != "2.0":
        raise Refusal("invalid JSON-RPC request")
    if not _valid_id(request.get("id")) or request.get("method") != "SendMessage":
        raise Refusal("unsupported or invalid RPC operation")
    if set(request) - {"jsonrpc", "id", "method", "params"}:
        raise Refusal("unexpected RPC envelope field")
    params = request.get("params")
    
    if not isinstance(params, dict):
        raise Refusal("only new-message requests are supported")
        
    # Dual-mode support: check if it's using the new A2A envelope wrapping
    if "envelope" in params:
        env_dict = params["envelope"]
        if not isinstance(env_dict, dict):
            raise Refusal("envelope must be an object")
        return None, env_dict

    # Legacy fallback for existing tests
    if set(params) != {"message"}:
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
    return message_id, None


def validate_destination_url(url):
    """Refuse unknown or non-loopback destinations."""
    if not isinstance(url, str):
        raise Refusal("destination URL must be a string")
    try:
        parsed = urlsplit(url)
    except Exception as exc:
        raise Refusal("invalid destination URL") from exc

    if parsed.scheme != "http" or parsed.hostname != "127.0.0.1":
        raise Refusal("destination must be explicit loopback http://127.0.0.1:<port>/a2a")
    if parsed.username or parsed.password:
        raise Refusal("userinfo in destination URL refused")
    if parsed.port is None or not (0 < parsed.port <= 65535):
        raise Refusal("destination must specify a valid port")
    if parsed.path.rstrip("/") != RPC_PATH:
        raise Refusal("invalid RPC destination path")
    return url


def _extract_conversation_text(content_parts):
    """Extract and strictly validate text part when a conversation handler is active.

    Requires an appropriately bounded string text part.
    Rejects null, numeric, boolean, list, empty, and other non-string text values.
    """
    raw_text = None
    if isinstance(content_parts, dict):
        if "text" not in content_parts:
            raise Refusal("conversation handler requires text field in content parts")
        raw_text = content_parts["text"]
    elif isinstance(content_parts, list):
        if len(content_parts) != 1 or not isinstance(content_parts[0], dict):
            raise Refusal("conversation handler requires single text part object in list")
        if "text" not in content_parts[0]:
            raise Refusal("conversation handler requires text field in content parts")
        raw_text = content_parts[0]["text"]
    else:
        raise Refusal("invalid content parts structure for conversation handler")

    if type(raw_text) is not str:
        raise Refusal("conversation handler requires string text value")
    if not (0 < len(raw_text) <= MAX_INPUT_CHARS):
        raise Refusal("conversation handler requires non-empty text within bounds")
    return raw_text


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
            
        self._sessions = {}
        sessions_file = root / "sessions.json"
        if sessions_file.exists():
            try:
                import json
                self._sessions = json.loads(sessions_file.read_text())
            except Exception as exc:
                raise Refusal("invalid sessions.json") from exc
                
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

    def get_session(self, session_id):
        return self._sessions.get(session_id)

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
            if not isinstance(event, dict):
                raise Refusal("invalid journal fields")
            keys = set(event)
            if keys not in ({"messageId", "requestHash", "response", "prev", "digest"},
                            {"messageId", "requestHash", "response", "prev", "digest", "envelopeState"}):
                raise Refusal("invalid journal fields")
                
            payload_keys = [k for k in ("messageId", "requestHash", "response", "prev", "envelopeState") if k in event]
            payload = {k: event[k] for k in payload_keys}
            expected = hashlib.sha256(_canonical(payload)).hexdigest()
            if event["prev"] != self._last_hash or event["digest"] != expected:
                raise Refusal("journal chain integrity failure")
            message_id = event["messageId"]
            if not isinstance(message_id, str) or message_id in self._seen:
                raise Refusal("journal duplicate messageId")
            if not isinstance(event["requestHash"], str) or not isinstance(event["response"], dict):
                raise Refusal("invalid journal payload")
                
            if "envelopeState" in event:
                state = event["envelopeState"]
                if not isinstance(state, dict) or set(state) != {"sessionId", "sequence", "metadataHash"}:
                    raise Refusal("invalid envelope state")
                session_id = state["sessionId"]
                seq = state["sequence"]
                meta_hash = state["metadataHash"]
                if not isinstance(session_id, str) or not session_id:
                    raise Refusal("invalid envelope state sessionId")
                if type(seq) is not int or seq <= 0:
                    raise Refusal("invalid envelope state sequence")
                if not isinstance(meta_hash, str) or not meta_hash:
                    raise Refusal("invalid envelope state metadataHash")
                    
                session = self._sessions.get(session_id)
                if not session:
                    raise Refusal("journal references unprovisioned session")
                if session.get("currentSequence", 0) != seq - 1:
                    raise Refusal("journal envelope sequence gap or out of order")
                seen = session.setdefault("seenMessageIds", {})
                session["currentSequence"] = seq
                seen[message_id] = meta_hash

            self._seen[message_id] = (event["requestHash"], event["response"])
            self._last_hash = expected

    def response_for(self, request, message_id, envelope_state=None, reply_text=None, incoming_text=None):
        if self._poisoned:
            raise Refusal("journal not available after write failure")
            
        params = request["params"]
        if "envelope" in params:
            request_hash = hashlib.sha256(_canonical(params["envelope"])).hexdigest()
        else:
            request_hash = hashlib.sha256(_canonical(params["message"])).hexdigest()
            
        if message_id in self._seen:
            old_hash, old_response = self._seen[message_id]
            if request_hash != old_hash:
                raise Refusal("conflicting replay messageId")
            return old_response
        # Generate response using handler if provided, else default ACK
        text_content = reply_text if reply_text is not None else ACK
        answer = {"message": {"messageId": str(uuid.uuid4()), "contextId": str(uuid.uuid4()),
                              "role": "ROLE_AGENT", "parts": [{"text": text_content, "mediaType": "text/plain"}]}}
        if incoming_text is not None:
            answer["receivedText"] = incoming_text
        event = {"messageId": message_id, "requestHash": request_hash,
                 "response": answer, "prev": self._last_hash}
        if envelope_state:
            event["envelopeState"] = envelope_state
            
        payload_keys = [k for k in ("messageId", "requestHash", "response", "prev", "envelopeState") if k in event]
        payload = {k: event[k] for k in payload_keys}
        digest = hashlib.sha256(_canonical(payload)).hexdigest()
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

    def record_outbound(self, session_id, envelope, metadata_hash=None):
        """Legitimate local outgoing-state mechanism: records outbound envelope in session and journal."""
        if self._poisoned:
            raise Refusal("journal not available after write failure")

        metadata = envelope.get("metadata", {})
        message_id = metadata.get("messageId")
        seq = metadata.get("sequence")
        if not isinstance(message_id, str) or not message_id:
            raise Refusal("invalid outbound messageId")
        if type(seq) is not int or seq <= 0:
            raise Refusal("invalid outbound sequence")

        session = self.get_session(session_id)
        if not session:
            raise Refusal("session not provisioned")
        if session.get("state") != "OPEN":
            raise Refusal("session not open")
        if seq != session.get("currentSequence", 0) + 1:
            raise Refusal("outbound sequence out of order")
        if seq > session.get("maxTurns", 0):
            raise Refusal("max turns exceeded")

        from agent_web.envelope import _hash_metadata
        if metadata_hash is None:
            metadata_hash = _hash_metadata(metadata)

        envelope_state = {
            "sessionId": session_id,
            "sequence": seq,
            "metadataHash": metadata_hash,
        }

        request_hash = hashlib.sha256(_canonical(envelope)).hexdigest()
        content_parts = envelope.get("contentParts", {})
        text_content = content_parts.get("text", "") if isinstance(content_parts, dict) else ""
        answer = {"outbound": True, "messageId": message_id, "text": text_content}
        event = {
            "messageId": message_id,
            "requestHash": request_hash,
            "response": answer,
            "prev": self._last_hash,
            "envelopeState": envelope_state,
        }

        payload_keys = [k for k in ("messageId", "requestHash", "response", "prev", "envelopeState") if k in event]
        payload = {k: event[k] for k in payload_keys}
        digest = hashlib.sha256(_canonical(payload)).hexdigest()
        event["digest"] = digest
        line = _canonical(event) + b"\n"

        if os.fstat(self._fd).st_size + len(line) > MAX_JOURNAL_BYTES:
            raise Refusal("journal size bound exceeded")
        try:
            if os.write(self._fd, line) != len(line):
                raise OSError("partial journal write")
            os.fsync(self._fd)
        except OSError as exc:
            self._poisoned = True
            raise Refusal("journal write refused") from exc

        self._last_hash = digest
        self._seen[message_id] = (request_hash, answer)
        session["currentSequence"] = seq
        session.setdefault("seenMessageIds", {})[message_id] = metadata_hash
        return event

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

    def __init__(
        self,
        journal,
        port=0,
        gate=None,
        handler=None,
        agent_id=None,
        peer_url=None,
        autonomous=False,
    ):
        self.journal = journal
        self.gate = gate if gate is not None else build_synthetic_gate()
        self.handler = handler
        self.agent_id = agent_id
        self.peer_url = peer_url
        self.autonomous = autonomous
        self.transcript = []
        super().__init__(("127.0.0.1", port), LocalHandler)
        if self.server_address[0] != "127.0.0.1":
            self.server_close()
            raise Refusal("server binding escaped loopback")

    def send_outbound_turn(
        self,
        session_id,
        text,
        seq,
        recipient_id,
        in_reply_to=None,
        correlation_id="corr-pond-1",
        dest_url=None,
    ):
        if not self.agent_id:
            raise Refusal("server has no configured agent_id for outbound sends")
        url = dest_url or self.peer_url
        if not url:
            raise Refusal("no destination URL configured")

        validated_url = validate_destination_url(url)

        from agent_web.conversation import create_envelope_turn, post_envelope_rpc

        msg_id = f"msg-{self.agent_id}-turn-{seq}"
        req = create_envelope_turn(
            sender=self.agent_id,
            recipient=recipient_id,
            seq=seq,
            mid=msg_id,
            text=text,
            session_id=session_id,
            correlation_id=correlation_id,
            in_reply_to=in_reply_to,
        )

        own_port = self.server_address[1]
        req["params"]["envelope"]["metadata"]["replyToUrl"] = f"http://127.0.0.1:{own_port}/a2a"

        cred = "fixture-caller-a" if self.agent_id == "agent-a" else "fixture-caller-b"

        # Record outbound in local journal
        self.journal.record_outbound(session_id, req["params"]["envelope"])
        speaker_label = "Agent A" if self.agent_id == "agent-a" else "Agent B"
        self.transcript.append((speaker_label, text))

        parsed = urlsplit(validated_url)
        try:
            status, resp = post_envelope_rpc(parsed.port, req, cred=cred)
        except Exception as exc:
            raise Refusal(f"outbound delivery failed: {exc}") from exc
            
        if status != 200:
            err = resp.get("error", {}).get("message", "outbound delivery refused")
            raise Refusal(f"outbound delivery failed: {err}")
        return status, resp

    def initiate_conversation(
        self,
        session_id="session-pond-1",
        prompt_text=None,
        recipient_id="agent-b",
        dest_url=None,
    ):
        from agent_web.conversation import POND_PROMPT_INITIAL
        text = prompt_text if prompt_text is not None else POND_PROMPT_INITIAL
        return self.send_outbound_turn(
            session_id=session_id,
            text=text,
            seq=1,
            recipient_id=recipient_id,
            dest_url=dest_url,
        )


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
            message_id, env_dict = _request_parts(request)
            
            if env_dict is not None:
                metadata = env_dict.get("metadata")
                if not isinstance(metadata, dict):
                    raise Refusal("envelope missing or invalid metadata")
                    
                session_id = metadata.get("sessionId")
                if not isinstance(session_id, str):
                    raise Refusal("invalid or missing sessionId")
                    
                session_manifest = self.server.journal.get_session(session_id)
                if not session_manifest:
                    raise Refusal("session not provisioned")
                    
                import copy
                test_manifest = copy.deepcopy(session_manifest)
                
                try:
                    res = validate_envelope(_canonical(env_dict), test_manifest, strict_synthetic_verifier)
                except EnvelopeRefusal as e:
                    raise Refusal(f"envelope refusal: {str(e)}")
                    
                message_id = res["envelope"]["metadata"]["messageId"]
                sender_id = res["envelope"]["metadata"]["senderAgentId"]
                recipient_id = res["envelope"]["metadata"]["recipientAgentId"]
                
                # Verify admission gate
                auth_header = self.headers.get("Authorization")
                if not auth_header or not auth_header.startswith("Bearer "):
                    raise Refusal("missing or invalid authorization header")
                cred_label = auth_header[7:].strip()
                if not cred_label:
                    raise Refusal("empty caller credential")
                if len(cred_label) > ADAPTER_ID_MAX_CHARS:
                    raise Refusal("oversized caller credential")
                if cred_label not in _PROVISIONED_CREDENTIALS:
                    raise Refusal("unknown or unauthorized caller credential")
                caller_cred = _PROVISIONED_CREDENTIALS[cred_label]
                
                # Synthetic timestamps for evidence bounds checking relative to the gate's clock
                now_utc = self.server.gate.now().strftime("%Y-%m-%dT%H:%M:%SZ")
                
                correlation_id = metadata.get("correlationId", "corr-test")
                sender_request = {
                    "agentRef": sender_id, "tenantRef": "tenant-alpha",
                    "ownerRef": "owner-alpha" if sender_id == "agent-a" else "owner-beta",
                    "participationScope": "a2a-message-send",
                    "messageId": message_id, "correlationId": correlation_id,
                    "occurredAtUtc": now_utc,
                    "message": {"messageType": "conversation_message", "body": "x"}
                }
                recipient_context = {
                    "agentRef": recipient_id, "tenantRef": "tenant-alpha",
                    "ownerRef": "owner-alpha" if recipient_id == "agent-a" else "owner-beta",
                }
                try:
                    self.server.gate.route(sender_request, recipient_context, caller_cred)
                except (ParticipationRefused, AdmissionRefused, ObservatoryRefusal) as e:
                    raise Refusal(f"agent admission gate refused participation: {str(e)}")
                    
                envelope_state = {
                    "sessionId": session_id,
                    "sequence": res["envelope"]["metadata"]["sequence"],
                    "metadataHash": res["metadataHash"]
                }
                
                # Check for prompt-dependent conversation handler
                reply_text = None
                incoming_text = ""
                if getattr(self.server, "handler", None) is not None:
                    incoming_text = _extract_conversation_text(env_dict.get("contentParts"))
                    reply_text = self.server.handler(incoming_text, sender_id, recipient_id)
                
                response = self.server.journal.response_for(
                    request,
                    message_id,
                    envelope_state,
                    reply_text=reply_text,
                    incoming_text=incoming_text if env_dict is not None else None,
                )
                
                # Atomic state commit upon successful journal write
                session_manifest.update(test_manifest)
                
                # Record in server transcript
                speaker_label = "Agent A" if sender_id == "agent-a" else "Agent B"
                self.server.transcript.append((speaker_label, incoming_text))
            else:
                response = self.server.journal.response_for(request, message_id)
                
        except Refusal as exc:
            self._send(400, {"jsonrpc": "2.0", "id": None,
                             "error": {"code": -32602, "message": str(exc)}})
            return
            
        self._send(200, {"jsonrpc": "2.0", "id": request["id"], "result": response})
        
        # Autonomous conversation loop: send next outbound turn if configured
        if env_dict is not None and getattr(self.server, "autonomous", False):
            turn_idx = res["envelope"]["metadata"]["sequence"]
            max_turns = session_manifest.get("maxTurns", 0)
            if turn_idx < max_turns and reply_text:
                reply_to_url = env_dict.get("metadata", {}).get("replyToUrl") or getattr(self.server, "peer_url", None)
                if reply_to_url:
                    def dispatch_next():
                        time.sleep(0.01)
                        try:
                            self.server.send_outbound_turn(
                                session_id=session_id,
                                text=reply_text,
                                seq=turn_idx + 1,
                                recipient_id=sender_id,
                                in_reply_to=message_id,
                                correlation_id=correlation_id,
                                dest_url=reply_to_url
                            )
                        except Exception:
                            pass
                    threading.Thread(target=dispatch_next, daemon=True).start()

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
    parser.add_argument("--agent-id", choices=["agent-a", "agent-b"], default=None,
                        help="synthetic agent personality for conversation demonstration")
    parser.add_argument("--peer-url", type=str, default=None,
                        help="loopback endpoint of peer agent")
    parser.add_argument("--autonomous", action="store_true",
                        help="enable autonomous multi-turn conversation response loop")
    parser.add_argument("--initiate", action="store_true",
                        help="initiate conversation upon startup")
    parser.add_argument("--session-id", default="session-pond-1",
                        help="conversation session ID")
    options = parser.parse_args(argv)
    journal = Journal(options.journal_dir)
    handler = CONVERSATION_HANDLERS.get(options.agent_id) if options.agent_id else None
    try:
        with LocalServer(
            journal,
            options.port,
            handler=handler,
            agent_id=options.agent_id,
            peer_url=options.peer_url,
            autonomous=options.autonomous,
        ) as server:
            print("LOCAL_ONLY_NOT_DEPLOYED http://127.0.0.1:%d%s" % (server.server_address[1], CARD_PATH),
                  flush=True)
            if options.initiate:
                def do_init():
                    time.sleep(0.05)
                    try:
                        server.initiate_conversation(session_id=options.session_id, dest_url=options.peer_url)
                    except Exception:
                        pass
                threading.Thread(target=do_init, daemon=True).start()
            server.serve_forever(poll_interval=0.05)
    finally:
        journal.close()


if __name__ == "__main__":
    main()
