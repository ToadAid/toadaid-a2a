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
        "signature": "valid_synthetic_sig",
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


class A2AExchangeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        
        self.dir_a = Path(self.tmp.name) / "agent-a"
        self.dir_a.mkdir(mode=0o700)
        self.journal_a = Journal(self.dir_a)
        self.server_a = LocalServer(self.journal_a)
        self.thread_a = threading.Thread(target=self.server_a.serve_forever, daemon=True)
        self.thread_a.start()
        
        self.dir_b = Path(self.tmp.name) / "agent-b"
        self.dir_b.mkdir(mode=0o700)
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

    def rpc(self, server, payload):
        conn = http.client.HTTPConnection("127.0.0.1", server.server_address[1], timeout=2)
        try:
            conn.request("POST", RPC_PATH, json.dumps(payload).encode(),
                         {"Content-Type": "application/json", "A2A-Version": "1.0"})
            response = conn.getresponse()
            data = json.loads(response.read())
            return response.status, data
        finally:
            conn.close()

    def test_agent_a_to_b_to_a_exchange(self):
        # 1. Agent A sends to Agent B (Sequence 1)
        req_1 = create_envelope_request("agent-a", "agent-b", 1, "msg-1", "Hello from A")
        status_1, resp_1 = self.rpc(self.server_b, req_1)
        self.assertEqual(status_1, 200)
        self.assertIn("result", resp_1)
        self.assertIn("messageId", resp_1["result"]["message"]) # Acknowledged by B's probe
        
        # 2. Agent B replies to Agent A (Sequence 2)
        req_2 = create_envelope_request("agent-b", "agent-a", 2, "msg-2", "Reply from B")
        status_2, resp_2 = self.rpc(self.server_a, req_2)
        self.assertEqual(status_2, 200)
        self.assertIn("result", resp_2)
        self.assertIn("messageId", resp_2["result"]["message"]) # Acknowledged by A's probe
        
        # 3. Agent A replies back to Agent B (Sequence 3)
        req_3 = create_envelope_request("agent-a", "agent-b", 3, "msg-3", "Acknowledge reply")
        status_3, resp_3 = self.rpc(self.server_b, req_3)
        self.assertEqual(status_3, 200)
        self.assertIn("result", resp_3)

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


if __name__ == "__main__":
    unittest.main()
