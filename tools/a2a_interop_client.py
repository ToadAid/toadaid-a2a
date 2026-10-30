"""Independent-process, loopback-only A2A JSON-RPC interoperability smoke client.

This CLI never imports server code, contacts non-loopback hosts or asserts official
TCK conformance. It is a test consumer for the explicit P0B-B fixed-ack probe.
"""
import argparse
import http.client
import json
from urllib.parse import urlsplit
import uuid

MAX_RESPONSE_BYTES = 65536
CARD_PATH = "/.well-known/agent-card.json"
RPC_PATH = "/a2a"
EXPECTED_ACK = "Local-only A2A probe acknowledged; no tools, AI model, or execution authority."


class InteropError(ValueError):
    """Controlled refusal without echoing untrusted response data."""


def _unique_fields(items):
    result = {}
    for key, value in items:
        if key in result:
            raise InteropError("duplicate response JSON field")
        result[key] = value
    return result


def _decode(raw):
    if not isinstance(raw, bytes) or len(raw) > MAX_RESPONSE_BYTES:
        raise InteropError("response exceeded bounds")
    try:
        result = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_fields,
                            parse_constant=lambda _: (_ for _ in ()).throw(InteropError("invalid JSON number")))
    except InteropError:
        raise
    except (UnicodeError, json.JSONDecodeError, ValueError, RecursionError) as exc:
        raise InteropError("invalid response JSON") from exc
    if not isinstance(result, dict):
        raise InteropError("expected JSON object")
    return result


def _local_port(url):
    try:
        parsed = urlsplit(url)
        if (parsed.scheme != "http" or parsed.hostname != "127.0.0.1"
                or parsed.username is not None or parsed.password is not None
                or parsed.path not in ("", "/") or parsed.query or parsed.fragment
                or parsed.port is None or not 0 < parsed.port <= 65535):
            raise InteropError("only explicit IPv4 loopback origin allowed")
        if parsed.netloc != f"127.0.0.1:{parsed.port}":
            raise InteropError("no aliases, userinfo, or alternate authorities")
        return parsed.port
    except ValueError as exc:
        raise InteropError("invalid loopback origin") from exc


def _exchange(port, method, path, body=None, headers=None):
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
    try:
        connection.request(method, path, body=body, headers=headers or {})
        response = connection.getresponse()
        raw = response.read(MAX_RESPONSE_BYTES + 1)
        media = response.getheader("Content-Type", "").split(";", 1)[0].lower().strip()
        if media != "application/json":
            raise InteropError("unexpected response media type")
        return response.status, _decode(raw)
    except (OSError, TimeoutError, http.client.HTTPException) as exc:
        raise InteropError("loopback exchange failed") from exc
    finally:
        connection.close()


def _card_is_honest(card, port):
    expected_url = f"http://127.0.0.1:{port}{RPC_PATH}"
    interfaces = card.get("supportedInterfaces")
    if not isinstance(interfaces, list) or interfaces != [
        {"url": expected_url, "protocolBinding": "JSONRPC", "protocolVersion": "1.0"}
    ]:
        raise InteropError("Agent Card advertised an unexpected interface")
    skills = card.get("skills")
    if (not isinstance(skills, list) or len(skills) != 1
            or not isinstance(skills[0], dict) or skills[0].get("id") != "local-fixed-ack"):
        raise InteropError("unexpected advertised skill")
    capabilities = card.get("capabilities")
    if not isinstance(capabilities, dict) or any(
        capabilities.get(key) is not False
        for key in ("streaming", "pushNotifications", "extendedAgentCard")
    ):
        raise InteropError("unsupported advanced capability advertised")
    if card.get("name") != "ToadAid local probe (NOT DEPLOYED)":
        raise InteropError("wrong local fixture identity")
    if card.get("securitySchemes") or card.get("securityRequirements"):
        raise InteropError("unverified authentication claim in card")


def _request(message_id, rpc_id, method="SendMessage"):
    return {
        "jsonrpc": "2.0", "id": rpc_id, "method": method,
        "params": {"message": {"messageId": message_id, "role": "ROLE_USER",
                               "parts": [{"text": "Independent client hello", "mediaType": "text/plain"}]}}
    }


def _call(port, request):
    body = json.dumps(request, ensure_ascii=True, separators=(",", ":")).encode("utf-8")
    return _exchange(port, "POST", RPC_PATH, body, {
        "Content-Type": "application/json", "A2A-Version": "1.0"
    })


def _check_success(response, rpc_id):
    if response.get("jsonrpc") != "2.0" or type(response.get("id")) is not str or response["id"] != rpc_id:
        raise InteropError("response ID or JSON-RPC version mismatch")
    if "error" in response or set(response) != {"jsonrpc", "id", "result"}:
        raise InteropError("unexpected JSON-RPC response envelope")
    payload = response.get("result")
    if not isinstance(payload, dict) or set(payload) != {"message"}:
        raise InteropError("unexpected response payload type")
    message = payload["message"]
    if not isinstance(message, dict) or message.get("role") != "ROLE_AGENT":
        raise InteropError("response not from agent role")
    if not isinstance(message.get("messageId"), str) or not message["messageId"]:
        raise InteropError("missing response message ID")
    if not isinstance(message.get("contextId"), str) or not message["contextId"]:
        raise InteropError("missing response context ID")
    if message.get("parts") != [{"text": EXPECTED_ACK, "mediaType": "text/plain"}]:
        raise InteropError("response deviated from static, non-executable skill")


def check_interop(origin):
    """Perform independent discovery, request, replay and refusal over real HTTP."""
    port = _local_port(origin)
    status, card = _exchange(port, "GET", CARD_PATH)
    if status != 200:
        raise InteropError("discovery did not succeed")
    _card_is_honest(card, port)

    message_id, rpc_id = str(uuid.uuid4()), "independent-interop-1"
    request = _request(message_id, rpc_id)
    status, response = _call(port, request)
    if status != 200:
        raise InteropError("SendMessage refused valid interop request")
    _check_success(response, rpc_id)

    replay_status, replay = _call(port, request)
    if replay_status != 200 or replay != response:
        raise InteropError("idempotent replay changed response")

    unsupported = _request(str(uuid.uuid4()), "independent-interop-unsupported", "GetTask")
    denied_status, denied = _call(port, unsupported)
    if (denied_status != 400 or denied.get("jsonrpc") != "2.0"
            or not isinstance(denied.get("error"), dict)
            or "result" in denied):
        raise InteropError("unsupported RPC operation was not refused")

    return {
        "status": "LOCAL_INTEROP_SMOKE_PASS_NOT_TCK",
        "checks": ["discovery", "JSONRPC SendMessage", "same-message replay", "unsupported operation refused"],
        "network": "127.0.0.1 only",
        "fullA2AConformance": False,
        "deploymentAuthorized": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Local-only A2A cross-process interoperability smoke; NOT official TCK")
    parser.add_argument("--origin", required=True, help="http://127.0.0.1:<port> only")
    args = parser.parse_args(argv)
    try:
        result = check_interop(args.origin)
    except InteropError as exc:
        print("LOCAL_INTEROP_REFUSED: " + str(exc))
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
