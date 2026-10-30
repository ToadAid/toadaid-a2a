"""P0B-B real loopback HTTP tests; no public socket, models or tooling."""
import http.client
import json
from pathlib import Path
import stat
import tempfile
import threading
import unittest
from unittest import mock

from agent_web.local_probe import (ACK, CARD_PATH, RPC_PATH, MAX_REQUEST_BYTES,
                                   Journal, LocalServer, Refusal, agent_card)


def req(mid="m-1", content="Hello"):
    return {"jsonrpc": "2.0", "id": "jsonrpc-1", "method": "SendMessage",
            "params": {"message": {"messageId": mid, "role": "ROLE_USER",
                                   "parts": [{"text": content, "mediaType": "text/plain"}]}}}


class RealLoopbackTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name) / "operator"
        self.dir.mkdir(mode=0o700)
        self.journal = Journal(self.dir)
        self.server = LocalServer(self.journal)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.thread.join(timeout=2)
        self.server.server_close()
        self.journal.close()
        self.tmp.cleanup()

    def call(self, method, path, body=None, headers=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.server.server_address[1], timeout=2)
        try:
            conn.request(method, path, body=body, headers=headers or {})
            response = conn.getresponse()
            payload = response.read()
            return response.status, dict(response.getheaders()), json.loads(payload)
        finally:
            conn.close()

    def rpc(self, payload=None, headers=None):
        return self.call("POST", RPC_PATH, json.dumps(req() if payload is None else payload).encode(),
                         {"Content-Type": "application/json", "A2A-Version": "1.0", **(headers or {})})

    def test_loopback_only_bind_and_card(self):
        self.assertEqual(self.server.server_address[0], "127.0.0.1")
        status, headers, card = self.call("GET", CARD_PATH)
        self.assertEqual(status, 200)
        self.assertEqual(card, agent_card(self.server.server_address[1]))
        self.assertEqual(card["supportedInterfaces"][0]["protocolBinding"], "JSONRPC")
        self.assertEqual(card["supportedInterfaces"][0]["protocolVersion"], "1.0")
        self.assertTrue(card["supportedInterfaces"][0]["url"].startswith("http://127.0.0.1:"))
        self.assertNotIn("securitySchemes", card)
        self.assertFalse(card["capabilities"]["streaming"])
        self.assertEqual(len(card["skills"]), 1)
        self.assertEqual(headers["Cache-Control"], "no-store")

    def test_only_static_message_after_fsync_journal(self):
        status, _, body = self.rpc()
        self.assertEqual(status, 200)
        self.assertEqual(body["id"], "jsonrpc-1")
        self.assertEqual(set(body["result"]), {"message"})
        m = body["result"]["message"]
        self.assertEqual(m["role"], "ROLE_AGENT")
        self.assertEqual(m["parts"], [{"text": ACK, "mediaType": "text/plain"}])
        self.assertTrue(m["messageId"])
        self.assertTrue(m["contextId"])
        journal_file = self.dir / "local-probe-events.jsonl"
        self.assertTrue(journal_file.exists())
        self.assertEqual(stat.S_IMODE(journal_file.stat().st_mode), 0o600)
        entries = journal_file.read_text().splitlines()
        self.assertEqual(len(entries), 1)
        self.assertNotIn("Hello", entries[0])
        self.assertIn("requestHash", entries[0])

    def test_idempotent_same_message_id_no_second_journal_entry(self):
        _, _, first = self.rpc()
        _, _, second = self.rpc()
        self.assertEqual(first, second)
        self.assertEqual(len((self.dir / "local-probe-events.jsonl").read_text().splitlines()), 1)

    def test_conflicting_replay_refused(self):
        self.assertEqual(self.rpc()[0], 200)
        alt = req(content="different")
        status, _, result = self.rpc(alt)
        self.assertEqual(status, 400)
        self.assertIn("conflicting replay", result["error"]["message"])
        self.assertEqual(len((self.dir / "local-probe-events.jsonl").read_text().splitlines()), 1)

    def test_restart_reconstructs_reply_and_detects_replay(self):
        self.assertEqual(self.rpc()[0], 200)
        expected = self.rpc()[2]
        self.journal.close()  # simulate stopped process before journal replay
        second = Journal(self.dir)
        try:
            self.assertEqual(second.response_for(req(), "m-1"), expected["result"])
            with self.assertRaisesRegex(Refusal, "conflicting replay"):
                second.response_for(req(content="no"), "m-1")
        finally:
            second.close()

    def test_tampered_journal_refuses_restart(self):
        self.rpc()
        path = self.dir / "local-probe-events.jsonl"
        raw = path.read_bytes()
        path.write_bytes(raw.replace(b"Local-only", b"Tamper-only"))
        self.journal.close()
        with self.assertRaisesRegex(Refusal, "integrity failure"):
            Journal(self.dir)

    def test_incomplete_journal_refuses_restart(self):
        self.rpc()
        path = self.dir / "local-probe-events.jsonl"
        path.write_bytes(path.read_bytes()[:-1])
        self.journal.close()
        with self.assertRaisesRegex(Refusal, "incomplete"):
            Journal(self.dir)

    def test_unknown_path_no_data(self):
        self.assertEqual(self.call("GET", "/api/keys")[0], 404)
        self.assertEqual(self.call("GET", "/.well-known/agent-card.json?x=y")[0], 404)
        self.assertEqual(self.call("POST", "/private")[0], 404)

    def test_no_write_http_methods(self):
        for method in ("PUT", "DELETE", "PATCH", "OPTIONS"):
            with self.subTest(method=method):
                self.assertEqual(self.call(method, RPC_PATH)[0], 405)

    def test_host_header_cannot_change_card_url(self):
        status, _, card = self.call("GET", CARD_PATH, headers={"Host": "evil.example"})
        self.assertEqual(status, 200)
        self.assertIn("127.0.0.1", card["supportedInterfaces"][0]["url"])
        self.assertNotIn("evil.example", json.dumps(card))

    def test_header_no_version_is_refused(self):
        status, _, body = self.call("POST", RPC_PATH, json.dumps(req()).encode(),
                                    {"Content-Type": "application/json"})
        self.assertEqual(status, 400)
        self.assertIn("version", body["error"]["message"])

    def test_old_version_is_refused(self):
        self.assertEqual(self.rpc(headers={"A2A-Version": "0.3"})[0], 400)

    def test_invalid_media_type(self):
        self.assertEqual(self.rpc(headers={"Content-Type": "text/plain"})[0], 415)

    def test_duplicate_field_refused(self):
        raw = b'{"jsonrpc":"2.0","jsonrpc":"2.0","id":1,"method":"SendMessage"}'
        self.assertEqual(self.call("POST", RPC_PATH, raw, {"Content-Type":"application/json", "A2A-Version":"1.0"})[0], 400)

    def test_oversized_payload_refused(self):
        self.assertEqual(self.call("POST", RPC_PATH, b" " * (MAX_REQUEST_BYTES + 1),
                                   {"Content-Type":"application/json", "A2A-Version":"1.0"})[0], 413)

    def test_no_response_to_nontext_or_task_continuation(self):
        for key, value in (("taskId", "task-1"), ("contextId", "context-1"), ("metadata", {"execute": True})):
            with self.subTest(key=key):
                modified = req(mid="m-" + key)
                modified["params"]["message"][key] = value
                self.assertEqual(self.rpc(modified)[0], 400)
        bad = req()
        bad["params"]["message"]["parts"] = [{"url": "https://example.org/secret"}]
        self.assertEqual(self.rpc(bad)[0], 400)
        self.assertFalse((self.dir / "local-probe-events.jsonl").read_text())

    def test_no_unsupported_rpc(self):
        x = req()
        x["method"] = "GetTask"
        self.assertEqual(self.rpc(x)[0], 400)
        self.assertFalse((self.dir / "local-probe-events.jsonl").read_text())

    def test_private_journal_dir_required(self):
        x = Path(self.tmp.name) / "world"
        x.mkdir(mode=0o755)
        with self.assertRaisesRegex(Refusal, "0700"):
            Journal(x)

    def test_second_active_writer_refused(self):
        with self.assertRaisesRegex(Refusal, "active writer"):
            Journal(self.dir)

    def test_symlink_journal_refused(self):
        self.rpc()
        source = self.dir / "local-probe-events.jsonl"
        source.rename(self.dir / "stored")
        source.symlink_to(self.dir / "stored")
        with self.assertRaises(OSError):
            Journal(self.dir)

    def test_extreme_numeric_json_refused_not_crash(self):
        raw = b'{"jsonrpc":"2.0","id":' + b'9' * 5000 + b',"method":"SendMessage"}'
        status, _, result = self.call("POST", RPC_PATH, raw,
                                      {"Content-Type": "application/json", "A2A-Version": "1.0"})
        self.assertEqual(status, 400)
        self.assertIn("error", result)

    def test_excessive_json_nesting_refused_not_crash(self):
        raw = b'[' * 1300 + b'0' + b']' * 1300
        status, _, result = self.call("POST", RPC_PATH, raw,
                                      {"Content-Type": "application/json", "A2A-Version": "1.0"})
        self.assertEqual(status, 400)
        self.assertIn("error", result)

    def test_bad_json_id_no_journal(self):
        x = req()
        x["id"] = True
        self.assertEqual(self.rpc(x)[0], 400)
        self.assertFalse((self.dir / "local-probe-events.jsonl").read_text())

    def test_journal_io_failure_does_not_emit_success(self):
        with mock.patch("agent_web.local_probe.os.fsync", side_effect=OSError("test disk failed")):
            status, _, result = self.rpc()
        self.assertEqual(status, 400)
        self.assertNotIn("result", result)
        self.assertEqual(self.rpc(req(mid="new"))[0], 400)


if __name__ == "__main__":
    unittest.main()
