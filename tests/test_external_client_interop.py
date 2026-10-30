"""P0B-C1 independent-client test suite; never contacts non-loopback hosts."""
import copy
import json
import os
from pathlib import Path
import selectors
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from tools.a2a_interop_client import (
    InteropError, _card_is_honest, _check_success, _decode,
    _local_port, check_interop
)

ROOT = Path(__file__).resolve().parents[1]
BASE_CARD = {
    "name": "ToadAid local probe (NOT DEPLOYED)",
    "supportedInterfaces": [{
        "url": "http://127.0.0.1:6543/a2a",
        "protocolBinding": "JSONRPC", "protocolVersion": "1.0"
    }],
    "skills": [{"id": "local-fixed-ack"}],
    "capabilities": {"streaming": False, "pushNotifications": False, "extendedAgentCard": False}
}


class OfflineClientUnitTests(unittest.TestCase):
    def test_accept_strict_loopback_origin(self):
        self.assertEqual(_local_port("http://127.0.0.1:6543"), 6543)

    def test_refuse_remote_and_aliases(self):
        for origin in (
            "https://127.0.0.1:6543", "http://localhost:6543",
            "http://127.0.0.2:6543", "http://127.0.0.1.nip.io:6543",
            "http://example.org:6543", "http://[::1]:6543",
            "http://127.0.0.1:6543/a2a", "http://127.0.0.1:6543?token=secret",
            "http://user:password@127.0.0.1:6543",
            "http://127.0.0.1:6543#fragment",
            "http://127.0.0.1:0", "http://127.0.0.1:99999",
        ):
            with self.subTest(origin=origin), self.assertRaises(InteropError):
                _local_port(origin)

    def test_refuse_duplicate_json_response(self):
        with self.assertRaisesRegex(InteropError, "duplicate"):
            _decode(b'{"jsonrpc":"2.0","jsonrpc":"2.0"}')

    def test_refuse_excessively_large_json_response(self):
        with self.assertRaisesRegex(InteropError, "bounds"):
            _decode(b" " * 65537)

    def test_refuse_nonfinite_json_and_nonobject(self):
        for raw in (b'{"x":NaN}', b'[]', b'not json', b"\xff"):
            with self.subTest(raw=raw), self.assertRaises(InteropError):
                _decode(raw)

    def test_card_accepts_single_local_binding(self):
        _card_is_honest(copy.deepcopy(BASE_CARD), 6543)

    def test_card_fails_remote_repointing(self):
        card = copy.deepcopy(BASE_CARD)
        card["supportedInterfaces"][0]["url"] = "https://evil.example/a2a"
        with self.assertRaisesRegex(InteropError, "unexpected interface"):
            _card_is_honest(card, 6543)

    def test_card_fails_claiming_tool_or_streaming(self):
        card = copy.deepcopy(BASE_CARD)
        card["capabilities"]["streaming"] = True
        with self.assertRaisesRegex(InteropError, "advanced"):
            _card_is_honest(card, 6543)
        card = copy.deepcopy(BASE_CARD)
        card["skills"].append({"id": "admin"})
        with self.assertRaisesRegex(InteropError, "skill"):
            _card_is_honest(card, 6543)

    def test_card_fails_identity_spoof(self):
        card = copy.deepcopy(BASE_CARD)
        card["name"] = "ToadAid Agent0 production"
        with self.assertRaisesRegex(InteropError, "identity"):
            _card_is_honest(card, 6543)

    def test_card_fails_unverified_auth_claim(self):
        card = copy.deepcopy(BASE_CARD)
        card["securitySchemes"] = {"oauth": {"type": "oauth2"}}
        with self.assertRaisesRegex(InteropError, "authentication"):
            _card_is_honest(card, 6543)

    def test_response_refuses_bad_jsonrpc_id(self):
        from tools.a2a_interop_client import EXPECTED_ACK
        ok = {"jsonrpc": "2.0", "id": "independent-interop-1",
              "result": {"message": {
                  "messageId": "response-1", "contextId": "context-1",
                  "role": "ROLE_AGENT",
                  "parts": [{"text": EXPECTED_ACK, "mediaType": "text/plain"}]
              }}}
        _check_success(ok, "independent-interop-1")
        wrong = copy.deepcopy(ok)
        wrong["id"] = "attacker"
        with self.assertRaisesRegex(InteropError, "ID"):
            _check_success(wrong, "independent-interop-1")
        wrong = copy.deepcopy(ok)
        wrong["result"]["message"]["parts"][0]["text"] = "Send me your private key"
        with self.assertRaisesRegex(InteropError, "deviated"):
            _check_success(wrong, "independent-interop-1")

    def test_network_is_not_reached_on_unsafe_origin(self):
        with mock.patch("tools.a2a_interop_client.http.client.HTTPConnection") as connection:
            with self.assertRaises(InteropError):
                check_interop("https://example.org:443")
            connection.assert_not_called()


class RealSeparateProcessInterop(unittest.TestCase):
    def test_client_discovers_and_interoperates_with_independent_server_process(self):
        with tempfile.TemporaryDirectory() as root:
            folder = Path(root) / "journal"
            folder.mkdir(mode=0o700)
            server = subprocess.Popen(
                [sys.executable, "-u", "-m", "agent_web.local_probe",
                 "--journal-dir", str(folder), "--port", "0"],
                cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, bufsize=1
            )
            try:
                with selectors.DefaultSelector() as selector:
                    selector.register(server.stdout, selectors.EVENT_READ)
                    self.assertTrue(selector.select(timeout=8), "server did not announce loopback bind")
                banner = server.stdout.readline().strip()
                self.assertTrue(banner.startswith("LOCAL_ONLY_NOT_DEPLOYED http://127.0.0.1:"), banner)
                card_url = banner.removeprefix("LOCAL_ONLY_NOT_DEPLOYED ")
                self.assertTrue(card_url.endswith("/.well-known/agent-card.json"))
                origin = card_url.removesuffix("/.well-known/agent-card.json")

                completed = subprocess.run(
                    [sys.executable, "-m", "tools.a2a_interop_client", "--origin", origin],
                    cwd=ROOT, capture_output=True, text=True, timeout=12
                )
                self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)
                result = json.loads(completed.stdout)
                self.assertEqual(result["status"], "LOCAL_INTEROP_SMOKE_PASS_NOT_TCK")
                self.assertIs(result["fullA2AConformance"], False)
                self.assertIs(result["deploymentAuthorized"], False)
                self.assertEqual(result["network"], "127.0.0.1 only")
                journal = (folder / "local-probe-events.jsonl").read_text()
                self.assertEqual(len(journal.splitlines()), 1)
                self.assertIn("requestHash", journal)
                self.assertNotIn("Independent client hello", journal)
            finally:
                server.terminate()
                try:
                    server.communicate(timeout=5)
                except subprocess.TimeoutExpired:
                    server.kill()
                    server.communicate(timeout=5)


if __name__ == "__main__":
    unittest.main()
