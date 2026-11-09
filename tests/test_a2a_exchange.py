import http.client
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest

from agent_web.local_probe import Journal, LocalServer, RPC_PATH
from agent_web.envelope import _canonical_json, _hash_payload

def create_envelope_request(sender, recipient, seq, mid, text, session_id="session-exchange-1"):
    current_time_ms = int(time.time() * 1000)
    content_parts = {"text": text, "mediaType": "text/plain"}
    payload_hash = _hash_payload(content_parts)
    
    metadata = {
        "protocolVersion": "a2a-p1a-v0",
        "sessionId": session_id,
        "messageId": mid,
        "senderAgentId": sender,
        "recipientAgentId": recipient,
        "sequence": seq,
        "kind": "TURN",
        "createdAt": current_time_ms - 1000,
        "expiresAt": current_time_ms + 10000,
        "payloadHash": payload_hash
    }
    
    env = {
        "metadata": metadata,
        "contentParts": content_parts,
        "signature": f"synthetic_signature_for_{sender}",
        "authoritySource": "NONE",
        "executionEligible": False
    }
    
    # Wrap in JSON-RPC
    return {
        "jsonrpc": "2.0",
        "id": f"jsonrpc-{seq}",
        "method": "SendMessage",
        "params": {
            "envelope": env
        }
    }


def provision_sessions_file(journal_dir):
    sessions_data = {
        "session-exchange-1": {
            "sessionId": "session-exchange-1",
            "state": "OPEN",
            "participants": {"agent-a": {"agentId": "agent-a"}, "agent-b": {"agentId": "agent-b"}},
            "maxMessageBytes": 8192,
            "maxTurns": 1000,
            "currentSequence": 0,
            "seenMessageIds": {}
        },
        "session-zero-exec-1": {
            "sessionId": "session-zero-exec-1",
            "state": "OPEN",
            "participants": {"agent-a": {"agentId": "agent-a"}, "agent-b": {"agentId": "agent-b"}},
            "maxMessageBytes": 8192,
            "maxTurns": 1000,
            "currentSequence": 0,
            "seenMessageIds": {}
        },
        "session-zero-exec-2": {
            "sessionId": "session-zero-exec-2",
            "state": "OPEN",
            "participants": {"agent-a": {"agentId": "agent-a"}, "agent-b": {"agentId": "agent-b"}},
            "maxMessageBytes": 8192,
            "maxTurns": 1000,
            "currentSequence": 0,
            "seenMessageIds": {}
        },
        "session-replay-1": {
            "sessionId": "session-replay-1",
            "state": "OPEN",
            "participants": {"agent-a": {"agentId": "agent-a"}, "agent-b": {"agentId": "agent-b"}},
            "maxMessageBytes": 8192,
            "maxTurns": 1000,
            "currentSequence": 0,
            "seenMessageIds": {}
        },
        "session-auth-1": {
            "sessionId": "session-auth-1",
            "state": "OPEN",
            "participants": {"agent-a": {"agentId": "agent-a"}, "agent-b": {"agentId": "agent-b"}},
            "maxMessageBytes": 8192,
            "maxTurns": 1000,
            "currentSequence": 0,
            "seenMessageIds": {}
        },
        "session-fail-1": {
            "sessionId": "session-fail-1",
            "state": "OPEN",
            "participants": {"agent-a": {"agentId": "agent-a"}, "agent-b": {"agentId": "agent-b"}},
            "maxMessageBytes": 8192,
            "maxTurns": 1000,
            "currentSequence": 0,
            "seenMessageIds": {}
        },
        "session-unreg-1": {
            "sessionId": "session-unreg-1",
            "state": "OPEN",
            "participants": {"agent-unregistered": {"agentId": "agent-unregistered"}, "agent-b": {"agentId": "agent-b"}},
            "maxMessageBytes": 8192,
            "maxTurns": 1000,
            "currentSequence": 0,
            "seenMessageIds": {}
        }
    }
    (journal_dir / "sessions.json").write_text(json.dumps(sessions_data))


class A2AExchangeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        
        self.dir_a = Path(self.tmp.name) / "agent-a"
        self.dir_a.mkdir(mode=0o700)
        provision_sessions_file(self.dir_a)
        self.journal_a = Journal(self.dir_a)
        self.server_a = LocalServer(self.journal_a)
        self.thread_a = threading.Thread(target=self.server_a.serve_forever, daemon=True)
        self.thread_a.start()
        
        self.dir_b = Path(self.tmp.name) / "agent-b"
        self.dir_b.mkdir(mode=0o700)
        provision_sessions_file(self.dir_b)
        self.journal_b = Journal(self.dir_b)
        self.server_b = LocalServer(self.journal_b)
        self.thread_b = threading.Thread(target=self.server_b.serve_forever, daemon=True)
        self.thread_b.start()

    def tearDown(self):
        self.server_a.shutdown()
        self.thread_a.join(timeout=2)
        self.server_a.server_close()
        self.journal_a.close()
        
        self.server_b.shutdown()
        self.thread_b.join(timeout=2)
        self.server_b.server_close()
        self.journal_b.close()
        
        self.tmp.cleanup()

    def rpc(self, server, payload, cred="fixture-caller-a", headers=None):
        conn = http.client.HTTPConnection("127.0.0.1", server.server_address[1], timeout=2)
        try:
            req_headers = {"Content-Type": "application/json", "A2A-Version": "1.0"}
            if cred is not None:
                req_headers["Authorization"] = f"Bearer {cred}"
            if headers:
                req_headers.update(headers)
            conn.request("POST", RPC_PATH, json.dumps(payload).encode(), req_headers)
            response = conn.getresponse()
            data = json.loads(response.read())
            return response.status, data
        finally:
            conn.close()

    def test_exchange_rejects_malformed_envelope_metadata(self):
        req = create_envelope_request("agent-a", "agent-b", 1, "msg-1", "Hello")
        
        # Missing metadata
        del req["params"]["envelope"]["metadata"]
        status, resp = self.rpc(self.server_b, req)
        self.assertEqual(status, 400)
        self.assertIn("envelope missing or invalid metadata", resp["error"]["message"])
        
        # Invalid metadata type
        req["params"]["envelope"]["metadata"] = ["not a dict"]
        status2, resp2 = self.rpc(self.server_b, req)
        self.assertEqual(status2, 400)
        self.assertIn("envelope missing or invalid metadata", resp2["error"]["message"])
        
        # Missing sessionId
        req["params"]["envelope"]["metadata"] = {"protocolVersion": "a2a-p1a-v0"}
        status3, resp3 = self.rpc(self.server_b, req)
        self.assertEqual(status3, 400)
        self.assertIn("invalid or missing sessionId", resp3["error"]["message"])
        
        # Null sessionId
        req["params"]["envelope"]["metadata"] = {"protocolVersion": "a2a-p1a-v0", "sessionId": None}
        status4, resp4 = self.rpc(self.server_b, req)
        self.assertEqual(status4, 400)
        self.assertIn("invalid or missing sessionId", resp4["error"]["message"])

    def test_journal_recovery_rejects_malformed_envelope_state(self):
        req_1 = create_envelope_request("agent-a", "agent-b", 1, "msg-rec-mal", "Initial", session_id="session-exchange-1")
        self.rpc(self.server_b, req_1)

        self.server_b.shutdown()
        self.thread_b.join(timeout=2)
        self.server_b.server_close()
        self.journal_b.close()
        
        path = self.dir_b / "local-probe-events.jsonl"
        raw = path.read_bytes()
        
        import hashlib
        # We need to manually fix the digest since we are tampering with the payload
        def tamper_journal(find_bytes, replace_bytes):
            tampered_str = raw.replace(find_bytes, replace_bytes)
            # Recompute digest for the tampered jsonl
            try:
                event = json.loads(tampered_str)
                payload_keys = [k for k in ("messageId", "requestHash", "response", "prev", "envelopeState") if k in event]
                payload = {k: event[k] for k in payload_keys}
                expected = hashlib.sha256(_canonical_json(payload)).hexdigest()
                event["digest"] = expected
                return _canonical_json(event) + b"\n"
            except Exception:
                return tampered_str

        # 1. Invalid sequence type (boolean instead of int)
        bad_seq = tamper_journal(b'"sequence":1', b'"sequence":true')
        path.write_bytes(bad_seq)
        with self.assertRaisesRegex(Exception, "invalid envelope state sequence"):
            Journal(self.dir_b)
            
        # 2. Missing metadataHash
        bad_hash = tamper_journal(b'"metadataHash"', b'"missingHash"')
        path.write_bytes(bad_hash)
        with self.assertRaisesRegex(Exception, "invalid envelope state"):
            Journal(self.dir_b)
            
        # Restore for teardown
        path.write_bytes(raw)

    def test_journal_recovery_reconstructs_sequence_and_replay(self):
        req_1 = create_envelope_request("agent-a", "agent-b", 1, "msg-rec-1", "Initial", session_id="session-exchange-1")
        status_1, resp_1 = self.rpc(self.server_b, req_1)
        self.assertEqual(status_1, 200)

        # Stop server B and recreate the Journal from the same directory to simulate restart
        self.server_b.shutdown()
        self.thread_b.join(timeout=2)
        self.server_b.server_close()
        self.journal_b.close()
        
        self.journal_b = Journal(self.dir_b)
        self.server_b = LocalServer(self.journal_b)
        self.thread_b = threading.Thread(target=self.server_b.serve_forever, daemon=True)
        self.thread_b.start()
        
        # Exact idempotent replay of seq 1 should still be rejected (recovery worked)
        status_2, resp_2 = self.rpc(self.server_b, req_1)
        self.assertEqual(status_2, 400)
        self.assertIn("OUT_OF_ORDER_SEQUENCE", resp_2["error"]["message"])
        
        # Out of order attempt (seq 1 again with different message)
        req_bad = create_envelope_request("agent-a", "agent-b", 1, "msg-rec-1-alt", "Alt", session_id="session-exchange-1")
        status_bad, resp_bad = self.rpc(self.server_b, req_bad)
        self.assertEqual(status_bad, 400)
        self.assertIn("OUT_OF_ORDER_SEQUENCE", resp_bad["error"]["message"])

        # Accept seq 2 normally after recovery
        req_2 = create_envelope_request("agent-a", "agent-b", 2, "msg-rec-2", "Next", session_id="session-exchange-1")
        status_3, resp_3 = self.rpc(self.server_b, req_2)
        self.assertEqual(status_3, 200)

    def test_agent_a_to_b_to_a_exchange(self):
        # 1. Agent A sends to Agent B (Sequence 1)
        req_1 = create_envelope_request("agent-a", "agent-b", 1, "msg-1", "Hello from A")
        status_1, resp_1 = self.rpc(self.server_b, req_1, cred="fixture-caller-a")
        self.assertEqual(status_1, 200)
        
        # Simulate A recording its own outgoing message locally by just writing to its journal directly
        self.journal_a.get_session("session-exchange-1")["currentSequence"] = 1
        
        # 2. Agent B replies to Agent A (Sequence 2)
        req_2 = create_envelope_request("agent-b", "agent-a", 2, "msg-2", "Reply from B")
        status_2, resp_2 = self.rpc(self.server_a, req_2, cred="fixture-caller-b")
        self.assertEqual(status_2, 200)
        
        # Simulate B recording its own outgoing message locally
        self.journal_b.get_session("session-exchange-1")["currentSequence"] = 2
        
        # 3. Agent A replies back to Agent B (Sequence 3)
        req_3 = create_envelope_request("agent-a", "agent-b", 3, "msg-3", "Acknowledge reply")
        status_3, resp_3 = self.rpc(self.server_b, req_3, cred="fixture-caller-a")
        self.assertEqual(status_3, 200)

    def test_unregistered_agent_is_refused_admission(self):
        req_unreg = create_envelope_request("agent-unregistered", "agent-b", 1, "msg-unreg", "Hello from unknown", session_id="session-unreg-1")
        status_unreg, resp_unreg = self.rpc(self.server_b, req_unreg)
        self.assertEqual(status_unreg, 400)
        self.assertIn("agent admission gate refused participation", resp_unreg["error"]["message"])

    def test_forged_sender_identity_refused(self):
        # Envelope says Agent A, but transport layer authenticates as Agent B
        req_forged = create_envelope_request("agent-a", "agent-b", 1, "msg-forgery", "I am totally A", session_id="session-exchange-1")
        status, resp = self.rpc(self.server_b, req_forged, cred="fixture-caller-b")
        self.assertEqual(status, 400)
        self.assertIn("CALLER_IDENTITY_MISMATCH", resp["error"]["message"])
        
    def test_missing_credential_refused_no_advance(self):
        req = create_envelope_request("agent-a", "agent-b", 1, "msg-missing-cred", "Hello", session_id="session-exchange-1")
        # No Authorization header
        status, resp = self.rpc(self.server_b, req, cred=None)
        self.assertEqual(status, 400)
        self.assertIn("missing or invalid authorization header", resp["error"]["message"])
        # Sequence and journal must not advance
        self.assertEqual(self.journal_b.get_session("session-exchange-1")["currentSequence"], 0)
        self.assertEqual((self.dir_b / "local-probe-events.jsonl").read_bytes(), b"")

    def test_empty_credential_refused_no_advance(self):
        req = create_envelope_request("agent-a", "agent-b", 1, "msg-empty-cred", "Hello", session_id="session-exchange-1")
        status, resp = self.rpc(self.server_b, req, cred="")
        self.assertEqual(status, 400)
        self.assertIn("empty caller credential", resp["error"]["message"])
        self.assertEqual(self.journal_b.get_session("session-exchange-1")["currentSequence"], 0)
        self.assertEqual((self.dir_b / "local-probe-events.jsonl").read_bytes(), b"")

    def test_unknown_credential_refused_no_advance(self):
        req = create_envelope_request("agent-a", "agent-b", 1, "msg-unknown-cred", "Hello", session_id="session-exchange-1")
        status, resp = self.rpc(self.server_b, req, cred="unknown-unprovisioned-caller")
        self.assertEqual(status, 400)
        self.assertIn("unknown or unauthorized caller credential", resp["error"]["message"])
        self.assertEqual(self.journal_b.get_session("session-exchange-1")["currentSequence"], 0)
        self.assertEqual((self.dir_b / "local-probe-events.jsonl").read_bytes(), b"")

    def test_oversized_credential_refused_no_advance(self):
        req = create_envelope_request("agent-a", "agent-b", 1, "msg-oversized-cred", "Hello", session_id="session-exchange-1")
        status, resp = self.rpc(self.server_b, req, cred="x" * 200)
        self.assertEqual(status, 400)
        self.assertIn("oversized caller credential", resp["error"]["message"])
        self.assertEqual(self.journal_b.get_session("session-exchange-1")["currentSequence"], 0)
        self.assertEqual((self.dir_b / "local-probe-events.jsonl").read_bytes(), b"")

    def test_revoked_or_suspended_agent_refused(self):
        # Mutate the trusted lifecycle source in Agent B's gate to simulate Agent A suspension
        old_source = self.server_b.gate.trusted_lifecycle_source
        def suspended_source(query):
            if query.get("agentRef") == "agent-a":
                return {"lifecycleStatus": "suspended", "currentCredentialGeneration": 1, "currentRevocationEpoch": 1, "observedAtUtc": self.server_b.gate.now().strftime("%Y-%m-%dT%H:%M:%SZ"), "agentRef": "agent-a", "tenantRef": "tenant-alpha", "ownerRef": "owner-alpha", "kind": "toadaid-a2a-credential-lifecycle-state"}
            return old_source(query)
        self.server_b.gate.trusted_lifecycle_source = suspended_source
        
        req = create_envelope_request("agent-a", "agent-b", 1, "msg-suspended", "Let me in", session_id="session-exchange-1")
        status, resp = self.rpc(self.server_b, req, cred="fixture-caller-a")
        self.assertEqual(status, 400)
        self.assertIn("LIFECYCLE_STATUS_SUSPENDED", resp["error"]["message"])

    def test_expired_registration_evidence_refused(self):
        # Mutate the registration adapter to simulate expired evidence for Agent A
        old_adapter = self.server_b.gate.trusted_registration_adapter
        def expired_adapter(query):
            decision = old_adapter(query)
            if decision and decision.get("agentRef") == "agent-a":
                # Must be after observation otherwise EVIDENCE_EXPIRY_NOT_AFTER_OBSERVATION
                # Set observed to 2000-01-01 and expiry to 2000-01-02
                decision["decisionObservedAtUtc"] = "2000-01-01T00:00:00Z"
                decision["evidenceExpiresAtUtc"] = "2000-01-02T00:00:00Z"
            return decision
        self.server_b.gate.trusted_registration_adapter = expired_adapter
        
        req = create_envelope_request("agent-a", "agent-b", 1, "msg-expired", "Let me in", session_id="session-exchange-1")
        status, resp = self.rpc(self.server_b, req, cred="fixture-caller-a")
        self.assertEqual(status, 400)
        self.assertIn("REGISTRATION_EVIDENCE_EXPIRED", resp["error"]["message"])

    def test_exchange_enforces_zero_execution_authority(self):
        req = create_envelope_request("agent-a", "agent-b", 1, "msg-x1", "Execute this", session_id="session-zero-exec-1")
        req["params"]["envelope"]["executionEligible"] = True
        status, resp = self.rpc(self.server_b, req)
        
        self.assertEqual(status, 400)
        self.assertIn("EXECUTION_ELIGIBLE_MUST_BE_FALSE", resp["error"]["message"])
        
        req2 = create_envelope_request("agent-a", "agent-b", 1, "msg-x2", "Execute this", session_id="session-zero-exec-2")
        req2["params"]["envelope"]["authoritySource"] = "AGENT"
        status2, resp2 = self.rpc(self.server_b, req2)
        
        self.assertEqual(status2, 400)
        self.assertIn("AUTHORITY_SOURCE_MUST_BE_NONE", resp2["error"]["message"])

    def test_exchange_detects_replay(self):
        req_1 = create_envelope_request("agent-a", "agent-b", 1, "msg-1", "Initial", session_id="session-replay-1")
        status_1, _ = self.rpc(self.server_b, req_1)
        self.assertEqual(status_1, 200)
        
        # Replay of an older sequence is rejected as out of order before checking idempotency
        status_2, resp_2 = self.rpc(self.server_b, req_1)
        self.assertEqual(status_2, 400)
        self.assertIn("OUT_OF_ORDER_SEQUENCE", resp_2["error"]["message"])

    def test_exchange_detects_failed_authentication(self):
        req = create_envelope_request("agent-a", "agent-b", 1, "msg-1", "Hello", session_id="session-auth-1")
        req["params"]["envelope"]["signature"] = "invalid_sig"
        
        status, resp = self.rpc(self.server_b, req)
        self.assertEqual(status, 400)
        self.assertIn("INVALID_SIGNATURE", resp["error"]["message"])

    def test_failed_journal_write_aborts_sequence_advance(self):
        req = create_envelope_request("agent-a", "agent-b", 1, "msg-fail", "Fail me", session_id="session-fail-1")
        
        import unittest.mock as mock
        with mock.patch("agent_web.local_probe.os.write", side_effect=OSError("disk full")):
            status, resp = self.rpc(self.server_b, req)
            self.assertEqual(status, 400)
            self.assertIn("journal write refused", resp["error"]["message"])
            
        # The sequence should NOT have advanced because the atomic update is post-journal.
        # Repeating the identical request sequence 1 should succeed once the disk issue is "resolved".
        # We need to restart the journal since it marks itself as poisoned on failure.
        self.journal_b.close()
        self.server_b.journal = Journal(self.dir_b)
        
        status2, resp2 = self.rpc(self.server_b, req)
        self.assertEqual(status2, 200)

    def test_independent_subprocess_exchange(self):
        import subprocess
        import sys
        
        dir_c = Path(self.tmp.name) / "agent-c"
        dir_c.mkdir(mode=0o700)
        provision_sessions_file(dir_c)
        
        dir_d = Path(self.tmp.name) / "agent-d"
        dir_d.mkdir(mode=0o700)
        provision_sessions_file(dir_d)

        # Start agent c
        proc_c = subprocess.Popen(
            [sys.executable, "-m", "agent_web.local_probe", "--journal-dir", str(dir_c), "--port", "0"],
            stdout=subprocess.PIPE,
            text=True
        )
        port_c = None
        for line in proc_c.stdout:
            if "LOCAL_ONLY_NOT_DEPLOYED" in line:
                port_c = int(line.split("http://127.0.0.1:")[1].split("/")[0])
                break

        # Start agent d
        proc_d = subprocess.Popen(
            [sys.executable, "-m", "agent_web.local_probe", "--journal-dir", str(dir_d), "--port", "0"],
            stdout=subprocess.PIPE,
            text=True
        )
        port_d = None
        for line in proc_d.stdout:
            if "LOCAL_ONLY_NOT_DEPLOYED" in line:
                port_d = int(line.split("http://127.0.0.1:")[1].split("/")[0])
                break

        try:
            self.assertIsNotNone(port_c)
            self.assertIsNotNone(port_d)
            
            # Use dummy server objects just to reuse self.rpc
            class DummyServer: pass
            server_c = DummyServer()
            server_c.server_address = ("127.0.0.1", port_c)
            
            server_d = DummyServer()
            server_d.server_address = ("127.0.0.1", port_d)

            # C sends to D (Sequence 1)
            req_1 = create_envelope_request("agent-a", "agent-b", 1, "msg-1", "Initial", session_id="session-exchange-1")
            status_1, resp_1 = self.rpc(server_d, req_1, cred="fixture-caller-a")
            self.assertEqual(status_1, 200)
            ack_msg_id = resp_1["result"]["message"]["messageId"]

            # C's own loopback records the outbound Seq 1 locally
            status_c1, _ = self.rpc(server_c, req_1, cred="fixture-caller-a")
            self.assertEqual(status_c1, 200)

            # D replies to C (Sequence 2)
            req_2 = create_envelope_request("agent-b", "agent-a", 2, "msg-2", f"In reply to {ack_msg_id}", session_id="session-exchange-1")
            status_2, resp_2 = self.rpc(server_c, req_2, cred="fixture-caller-b")
            self.assertEqual(status_2, 200)

        finally:
            proc_c.terminate()
            proc_c.wait()
            proc_d.terminate()
            proc_d.wait()


if __name__ == "__main__":
    unittest.main()
