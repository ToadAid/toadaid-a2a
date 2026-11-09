"""A2A-GEM-005: Comprehensive verification of two-frog synthetic agent conversation."""
import http.client
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest

from agent_web.local_probe import Journal, LocalServer, RPC_PATH
from agent_web.conversation import (
    POND_PROMPT_INITIAL,
    create_envelope_turn,
    format_transcript,
    pond_handler_a,
    pond_handler_b,
    post_envelope_rpc,
    provision_conversation_session,
    run_conversation_between_ports,
)


class TwoFrogsConversationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir_a = Path(self.tmp.name) / "agent-a"
        self.dir_b = Path(self.tmp.name) / "agent-b"
        provision_conversation_session(self.dir_a, "session-pond-1", max_turns=10)
        provision_conversation_session(self.dir_b, "session-pond-1", max_turns=10)

    def tearDown(self):
        self.tmp.cleanup()

    def test_two_frogs_conversation_four_turns_transcript(self):
        """1 & 2. Run two distinct subprocesses and verify exact 4-turn connected transcript."""
        proc_a = subprocess.Popen(
            [sys.executable, "-m", "agent_web.local_probe", "--journal-dir", str(self.dir_a), "--port", "0", "--agent-id", "agent-a"],
            stdout=subprocess.PIPE,
            text=True,
        )
        port_a = None
        for line in proc_a.stdout:
            if "LOCAL_ONLY_NOT_DEPLOYED" in line:
                port_a = int(line.split("http://127.0.0.1:")[1].split("/")[0])
                break

        proc_b = subprocess.Popen(
            [sys.executable, "-m", "agent_web.local_probe", "--journal-dir", str(self.dir_b), "--port", "0", "--agent-id", "agent-b"],
            stdout=subprocess.PIPE,
            text=True,
        )
        port_b = None
        for line in proc_b.stdout:
            if "LOCAL_ONLY_NOT_DEPLOYED" in line:
                port_b = int(line.split("http://127.0.0.1:")[1].split("/")[0])
                break

        try:
            self.assertIsNotNone(port_a)
            self.assertIsNotNone(port_b)

            turns, transcript = run_conversation_between_ports(
                port_a, port_b, session_id="session-pond-1", max_turns=4
            )

            expected_transcript = (
                "Agent A: Hello, Agent B. Welcome to Agent Pond!\n"
                "Agent B: Hello, Agent A. What shall we discuss?\n"
                "Agent A: Let's explore Tobyworld.\n"
                "Agent B: Let's begin at the Go Pond!"
            )
            self.assertEqual(transcript, expected_transcript)
            self.assertEqual(len(turns), 4)

            # Verify connected sequence numbers and responses
            self.assertEqual(turns[0], ("Agent A", "Hello, Agent B. Welcome to Agent Pond!"))
            self.assertEqual(turns[1], ("Agent B", "Hello, Agent A. What shall we discuss?"))
            self.assertEqual(turns[2], ("Agent A", "Let's explore Tobyworld."))
            self.assertEqual(turns[3], ("Agent B", "Let's begin at the Go Pond!"))

            # Verify journals on both agents recorded all turns
            lines_a = (self.dir_a / "local-probe-events.jsonl").read_text().splitlines()
            lines_b = (self.dir_b / "local-probe-events.jsonl").read_text().splitlines()
            self.assertEqual(len(lines_a), 4)
            self.assertEqual(len(lines_b), 4)

        finally:
            proc_a.terminate()
            proc_a.wait()
            proc_b.terminate()
            proc_b.wait()

    def test_identity_forgery_during_conversation(self):
        """Identity forgery is refused: sender claim does not match transport caller."""
        journal_b = Journal(self.dir_b)
        server_b = LocalServer(journal_b, handler=pond_handler_b)
        thread_b = threading.Thread(target=server_b.serve_forever, daemon=True)
        thread_b.start()

        try:
            port_b = server_b.server_address[1]

            # Turn 1: Valid send from Agent A
            req_1 = create_envelope_turn("agent-a", "agent-b", 1, "msg-1", POND_PROMPT_INITIAL)
            status_1, resp_1 = post_envelope_rpc(port_b, req_1, cred="fixture-caller-a")
            self.assertEqual(status_1, 200)

            # Turn 2: Forged claim - envelope says sender is agent-a, but uses agent-b credentials
            req_forged = create_envelope_turn("agent-a", "agent-b", 2, "msg-forged", "Forged turn")
            status_forged, resp_forged = post_envelope_rpc(port_b, req_forged, cred="fixture-caller-b")
            self.assertEqual(status_forged, 400)
            self.assertIn("CALLER_IDENTITY_MISMATCH", resp_forged["error"]["message"])

            # Verify sequence on Server B did not advance past 1
            self.assertEqual(journal_b.get_session("session-pond-1")["currentSequence"], 1)

        finally:
            server_b.shutdown()
            thread_b.join(timeout=2)
            server_b.server_close()
            journal_b.close()

    def test_revocation_during_conversation(self):
        """Revocation during conversation immediately halts subsequent turns."""
        journal_b = Journal(self.dir_b)
        server_b = LocalServer(journal_b, handler=pond_handler_b)
        thread_b = threading.Thread(target=server_b.serve_forever, daemon=True)
        thread_b.start()

        try:
            port_b = server_b.server_address[1]

            # Turn 1 succeeds
            req_1 = create_envelope_turn("agent-a", "agent-b", 1, "msg-1", POND_PROMPT_INITIAL)
            status_1, resp_1 = post_envelope_rpc(port_b, req_1, cred="fixture-caller-a")
            self.assertEqual(status_1, 200)

            # Suspend Agent A mid-conversation in Server B's gate lifecycle source
            old_source = server_b.gate.trusted_lifecycle_source
            def suspended_source(query):
                if query.get("agentRef") == "agent-a":
                    now_str = server_b.gate.now().strftime("%Y-%m-%dT%H:%M:%SZ")
                    return {
                        "lifecycleStatus": "suspended",
                        "currentCredentialGeneration": 1,
                        "currentRevocationEpoch": 1,
                        "observedAtUtc": now_str,
                        "agentRef": "agent-a",
                        "tenantRef": "tenant-alpha",
                        "ownerRef": "owner-alpha",
                        "kind": "toadaid-a2a-credential-lifecycle-state",
                    }
                return old_source(query)

            server_b.gate.trusted_lifecycle_source = suspended_source

            # Turn 3 attempt by Agent A is refused due to suspension
            req_3 = create_envelope_turn("agent-a", "agent-b", 2, "msg-2", "Let's explore Tobyworld.")
            status_3, resp_3 = post_envelope_rpc(port_b, req_3, cred="fixture-caller-a")
            self.assertEqual(status_3, 400)
            self.assertIn("LIFECYCLE_STATUS_SUSPENDED", resp_3["error"]["message"])

        finally:
            server_b.shutdown()
            thread_b.join(timeout=2)
            server_b.server_close()
            journal_b.close()

    def test_duplicate_delivery_refused(self):
        """Duplicate turn delivery is rejected by sequence and replay checks."""
        journal_b = Journal(self.dir_b)
        server_b = LocalServer(journal_b, handler=pond_handler_b)
        thread_b = threading.Thread(target=server_b.serve_forever, daemon=True)
        thread_b.start()

        try:
            port_b = server_b.server_address[1]

            # Turn 1 succeeds
            req_1 = create_envelope_turn("agent-a", "agent-b", 1, "msg-1", POND_PROMPT_INITIAL)
            status_1, _ = post_envelope_rpc(port_b, req_1, cred="fixture-caller-a")
            self.assertEqual(status_1, 200)

            # Duplicate Turn 1 delivery
            status_dup, resp_dup = post_envelope_rpc(port_b, req_1, cred="fixture-caller-a")
            self.assertEqual(status_dup, 400)
            self.assertIn("OUT_OF_ORDER_SEQUENCE", resp_dup["error"]["message"])

        finally:
            server_b.shutdown()
            thread_b.join(timeout=2)
            server_b.server_close()
            journal_b.close()

    def test_restart_recovery_preserves_conversation(self):
        """Server restart preserves conversation state and rejects past turn replays."""
        journal_b = Journal(self.dir_b)
        server_b = LocalServer(journal_b, handler=pond_handler_b)
        thread_b = threading.Thread(target=server_b.serve_forever, daemon=True)
        thread_b.start()

        port_b = server_b.server_address[1]

        # Process Turn 1
        req_1 = create_envelope_turn("agent-a", "agent-b", 1, "msg-1", POND_PROMPT_INITIAL)
        status_1, _ = post_envelope_rpc(port_b, req_1, cred="fixture-caller-a")
        self.assertEqual(status_1, 200)

        # Stop server B and simulate restart
        server_b.shutdown()
        thread_b.join(timeout=2)
        server_b.server_close()
        journal_b.close()

        # Restart server B using the exact same journal directory
        recovered_journal_b = Journal(self.dir_b)
        recovered_server_b = LocalServer(recovered_journal_b, handler=pond_handler_b)
        recovered_thread_b = threading.Thread(target=recovered_server_b.serve_forever, daemon=True)
        recovered_thread_b.start()

        try:
            new_port_b = recovered_server_b.server_address[1]

            # Replaying Turn 1 must be refused
            status_replay, resp_replay = post_envelope_rpc(new_port_b, req_1, cred="fixture-caller-a")
            self.assertEqual(status_replay, 400)
            self.assertIn("OUT_OF_ORDER_SEQUENCE", resp_replay["error"]["message"])

            # Sequence 2 (the next valid turn) must be accepted
            req_2 = create_envelope_turn("agent-a", "agent-b", 2, "msg-2", "Let's explore Tobyworld.")
            status_2, resp_2 = post_envelope_rpc(new_port_b, req_2, cred="fixture-caller-a")
            self.assertEqual(status_2, 200)
            self.assertEqual(
                resp_2["result"]["message"]["parts"][0]["text"],
                "Let's begin at the Go Pond!",
            )

        finally:
            recovered_server_b.shutdown()
            recovered_thread_b.join(timeout=2)
            recovered_server_b.server_close()
            recovered_journal_b.close()

    def test_bounded_conversation_length_refuses_extra_turn(self):
        """Conversations are strictly bounded by maxTurns in the session manifest."""
        dir_bounded = Path(self.tmp.name) / "agent-bounded"
        provision_conversation_session(dir_bounded, "session-bounded-1", max_turns=2)

        journal = Journal(dir_bounded)
        server = LocalServer(journal, handler=pond_handler_b)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        try:
            port = server.server_address[1]

            # Turn 1 (allowed: 1 <= 2)
            req_1 = create_envelope_turn("agent-a", "agent-b", 1, "msg-1", POND_PROMPT_INITIAL, session_id="session-bounded-1")
            status_1, _ = post_envelope_rpc(port, req_1, cred="fixture-caller-a")
            self.assertEqual(status_1, 200)

            # Turn 2 (allowed: 2 <= 2)
            req_2 = create_envelope_turn("agent-a", "agent-b", 2, "msg-2", "Second turn", session_id="session-bounded-1")
            status_2, _ = post_envelope_rpc(port, req_2, cred="fixture-caller-a")
            self.assertEqual(status_2, 200)

            # Turn 3 (exceeds maxTurns=2)
            req_3 = create_envelope_turn("agent-a", "agent-b", 3, "msg-3", "Third turn", session_id="session-bounded-1")
            status_3, resp_3 = post_envelope_rpc(port, req_3, cred="fixture-caller-a")
            self.assertEqual(status_3, 400)
            self.assertIn("MAX_TURNS_EXCEEDED", resp_3["error"]["message"])

        finally:
            server.shutdown()
            thread.join(timeout=2)
            server.server_close()
            journal.close()

    def test_conversation_handler_rejects_non_string_and_invalid_text(self):
        """When conversation handler is active, rejects null, numeric, boolean, list, empty, and oversized text."""
        journal_b = Journal(self.dir_b)
        server_b = LocalServer(journal_b, handler=pond_handler_b)
        thread_b = threading.Thread(target=server_b.serve_forever, daemon=True)
        thread_b.start()

        try:
            port_b = server_b.server_address[1]

            # 1. Null text value
            req_null = create_envelope_turn("agent-a", "agent-b", 1, "msg-null", "", overrides={"contentParts": {"text": None}})
            status, resp = post_envelope_rpc(port_b, req_null, cred="fixture-caller-a")
            self.assertEqual(status, 400)
            self.assertIn("conversation handler requires string text value", resp["error"]["message"])
            self.assertEqual(journal_b.get_session("session-pond-1")["currentSequence"], 0)
            self.assertEqual((self.dir_b / "local-probe-events.jsonl").read_bytes(), b"")

            # 2. Numeric text value
            req_num = create_envelope_turn("agent-a", "agent-b", 1, "msg-num", "", overrides={"contentParts": {"text": 42}})
            status, resp = post_envelope_rpc(port_b, req_num, cred="fixture-caller-a")
            self.assertEqual(status, 400)
            self.assertIn("conversation handler requires string text value", resp["error"]["message"])
            self.assertEqual(journal_b.get_session("session-pond-1")["currentSequence"], 0)
            self.assertEqual((self.dir_b / "local-probe-events.jsonl").read_bytes(), b"")

            # 3. Boolean text value
            req_bool = create_envelope_turn("agent-a", "agent-b", 1, "msg-bool", "", overrides={"contentParts": {"text": True}})
            status, resp = post_envelope_rpc(port_b, req_bool, cred="fixture-caller-a")
            self.assertEqual(status, 400)
            self.assertIn("conversation handler requires string text value", resp["error"]["message"])
            self.assertEqual(journal_b.get_session("session-pond-1")["currentSequence"], 0)
            self.assertEqual((self.dir_b / "local-probe-events.jsonl").read_bytes(), b"")

            # 4. List text value
            req_list = create_envelope_turn("agent-a", "agent-b", 1, "msg-list", "", overrides={"contentParts": {"text": ["nested", "string"]}})
            status, resp = post_envelope_rpc(port_b, req_list, cred="fixture-caller-a")
            self.assertEqual(status, 400)
            self.assertIn("conversation handler requires string text value", resp["error"]["message"])
            self.assertEqual(journal_b.get_session("session-pond-1")["currentSequence"], 0)
            self.assertEqual((self.dir_b / "local-probe-events.jsonl").read_bytes(), b"")

            # 5. Missing text field
            req_missing = create_envelope_turn("agent-a", "agent-b", 1, "msg-missing", "", overrides={"contentParts": {"other_field": "some_value"}})
            status, resp = post_envelope_rpc(port_b, req_missing, cred="fixture-caller-a")
            self.assertEqual(status, 400)
            self.assertIn("conversation handler requires text field in content parts", resp["error"]["message"])
            self.assertEqual(journal_b.get_session("session-pond-1")["currentSequence"], 0)
            self.assertEqual((self.dir_b / "local-probe-events.jsonl").read_bytes(), b"")

            # 6. Empty text string
            req_empty = create_envelope_turn("agent-a", "agent-b", 1, "msg-empty", "", overrides={"contentParts": {"text": ""}})
            status, resp = post_envelope_rpc(port_b, req_empty, cred="fixture-caller-a")
            self.assertEqual(status, 400)
            self.assertIn("conversation handler requires non-empty text within bounds", resp["error"]["message"])
            self.assertEqual(journal_b.get_session("session-pond-1")["currentSequence"], 0)
            self.assertEqual((self.dir_b / "local-probe-events.jsonl").read_bytes(), b"")

            # 7. Oversized text string
            req_oversized = create_envelope_turn("agent-a", "agent-b", 1, "msg-oversized", "", overrides={"contentParts": {"text": "A" * 1025}})
            status, resp = post_envelope_rpc(port_b, req_oversized, cred="fixture-caller-a")
            self.assertEqual(status, 400)
            self.assertIn("conversation handler requires non-empty text within bounds", resp["error"]["message"])
            self.assertEqual(journal_b.get_session("session-pond-1")["currentSequence"], 0)
            self.assertEqual((self.dir_b / "local-probe-events.jsonl").read_bytes(), b"")

        finally:
            server_b.shutdown()
            thread_b.join(timeout=2)
            server_b.server_close()
            journal_b.close()

    def test_legacy_probe_without_handler_accepts_arbitrary_envelope_content(self):
        """When no conversation handler is set, legacy fixed-ACK probe accepts arbitrary valid content parts."""
        journal_b = Journal(self.dir_b)
        server_b = LocalServer(journal_b, handler=None)
        thread_b = threading.Thread(target=server_b.serve_forever, daemon=True)
        thread_b.start()

        try:
            port_b = server_b.server_address[1]

            # Envelope with non-text dict content parts
            req_custom = create_envelope_turn("agent-a", "agent-b", 1, "msg-custom-payload", "", overrides={"contentParts": {"custom_data": [1, 2, 3]}})
            status, resp = post_envelope_rpc(port_b, req_custom, cred="fixture-caller-a")
            self.assertEqual(status, 200)
            from agent_web.local_probe import ACK
            self.assertEqual(resp["result"]["message"]["parts"][0]["text"], ACK)
            self.assertEqual(journal_b.get_session("session-pond-1")["currentSequence"], 1)

        finally:
            server_b.shutdown()
            thread_b.join(timeout=2)
            server_b.server_close()
            journal_b.close()


if __name__ == "__main__":
    unittest.main()
