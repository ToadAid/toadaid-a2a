import concurrent.futures
import threading
import json
import unittest

from agent_web.envelope import (
    validate_envelope, EnvelopeRefusal, _canonical_json, _hash_payload, _hash_metadata
)


def mock_trust_framework_verifier(metadata, signature, sender_id):
    """Synthetic offline verifier asserting trusted adapter boundary."""
    if signature == "trusted_valid_adapter_sig":
        return True
    return False


class TestA2AEnvelopeEngine(unittest.TestCase):
    def setUp(self):
        self.session = {
            "sessionId": "test-session-1",
            "state": "OPEN",
            "participants": {
                "agent-a": {"agentId": "agent-a"},
                "agent-b": {"agentId": "agent-b"}
            },
            "maxMessageBytes": 8192,
            "maxTurns": 10,
            "currentSequence": 0,
            "seenMessageIds": {}
        }
        self.current_time_ms = 1000000
    
    def create_envelope(self, overrides=None, meta_overrides=None):
        content_parts = {"text": "Hello World"}
        if overrides and "contentParts" in overrides:
            content_parts = overrides["contentParts"]
            
        # Hash must match the injected content otherwise it's tampered
        payload_hash = _hash_payload(content_parts) if not isinstance(content_parts, bytes) else "dummy_hash"
        
        metadata = {
            "protocolVersion": "a2a-p1a-v0",
            "sessionId": self.session["sessionId"],
            "messageId": "msg-1",
            "senderAgentId": "agent-a",
            "recipientAgentId": "agent-b",
            "sequence": 1,
            "kind": "TURN",
            "createdAt": self.current_time_ms - 1000,
            "expiresAt": self.current_time_ms + 10000,
            "payloadHash": payload_hash
        }
        
        if meta_overrides:
            metadata.update(meta_overrides)
            
        env = {
            "metadata": metadata,
            "contentParts": content_parts,
            "signature": "trusted_valid_adapter_sig",
            "authoritySource": "NONE",
            "executionEligible": False
        }
        if overrides:
            env.update(overrides)
            
        return _canonical_json(env)

    def test_valid_envelope_acceptance_and_state_advance(self):
        env1_bytes = self.create_envelope(meta_overrides={"messageId": "msg-1", "sequence": 1})
        res1 = validate_envelope(env1_bytes, self.session, mock_trust_framework_verifier, self.current_time_ms)
        self.assertEqual(res1["status"], "VALIDATED")
        self.assertFalse(res1["deliverable"])
        self.assertEqual(self.session["currentSequence"], 1)
        self.assertIn("msg-1", self.session["seenMessageIds"])
        
        env2_bytes = self.create_envelope(meta_overrides={"messageId": "msg-2", "sequence": 2})
        res2 = validate_envelope(env2_bytes, self.session, mock_trust_framework_verifier, self.current_time_ms)
        self.assertEqual(res2["status"], "VALIDATED")
        self.assertEqual(self.session["currentSequence"], 2)
        self.assertIn("msg-2", self.session["seenMessageIds"])

    def test_auth_failure_not_recorded(self):
        env_raw = self.create_envelope(overrides={"signature": "bad_signature"})
        with self.assertRaisesRegex(EnvelopeRefusal, "INVALID_SIGNATURE"):
            validate_envelope(env_raw, self.session, mock_trust_framework_verifier, self.current_time_ms)
            
        self.assertEqual(self.session["currentSequence"], 0)
        self.assertNotIn("msg-1", self.session.get("seenMessageIds", {}))

    def test_invalid_size_configuration(self):
        self.session["maxMessageBytes"] = "not_an_int"
        env = self.create_envelope()
        with self.assertRaisesRegex(EnvelopeRefusal, "INVALID_SIZE_CONFIGURATION"):
            validate_envelope(env, self.session, mock_trust_framework_verifier, self.current_time_ms)
            
        self.session["maxMessageBytes"] = -10
        with self.assertRaisesRegex(EnvelopeRefusal, "INVALID_SIZE_CONFIGURATION"):
            validate_envelope(env, self.session, mock_trust_framework_verifier, self.current_time_ms)

        # Allow valid session configuration above ceiling, but enforce 128KB limit anyway
        self.session["maxMessageBytes"] = 200000 
        big_text = "A" * 150000
        env_big = self.create_envelope(overrides={"contentParts": {"text": big_text}})
        with self.assertRaisesRegex(EnvelopeRefusal, "ENVELOPE_EXCEEDS_SIZE_LIMIT"):
            validate_envelope(env_big, self.session, mock_trust_framework_verifier, self.current_time_ms)

    def test_reject_duplicate_json_keys(self):
        env_str = self.create_envelope()
        # Directly manipulate bytes to insert duplicate top-level key
        tampered_str = env_str.decode('utf-8').replace('}', ',"authoritySource":"DUPLICATE"}').encode('utf-8')
        with self.assertRaisesRegex(EnvelopeRefusal, "DUPLICATE_JSON_KEY"):
            validate_envelope(tampered_str, self.session, mock_trust_framework_verifier, self.current_time_ms)

    def test_reject_non_finite_numbers(self):
        env_str = self.create_envelope().decode('utf-8')
        tampered_str = env_str.replace('"sequence":1', '"sequence":NaN').encode('utf-8')
        with self.assertRaisesRegex(EnvelopeRefusal, "NON_FINITE_NUMBER"):
            validate_envelope(tampered_str, self.session, mock_trust_framework_verifier, self.current_time_ms)

    def test_reject_boolean_in_int_fields(self):
        env1 = self.create_envelope(meta_overrides={"sequence": True})
        with self.assertRaisesRegex(EnvelopeRefusal, "INVALID_SEQUENCE"):
            validate_envelope(env1, self.session, mock_trust_framework_verifier, self.current_time_ms)
            
        env2 = self.create_envelope(meta_overrides={"createdAt": False})
        with self.assertRaisesRegex(EnvelopeRefusal, "INVALID_TIMESTAMPS"):
            validate_envelope(env2, self.session, mock_trust_framework_verifier, self.current_time_ms)

    def test_session_policy_hash_mismatch(self):
        self.session["sessionPolicyHash"] = "expected-policy"
        env1 = self.create_envelope(meta_overrides={"sessionPolicyHash": "different-policy"})
        with self.assertRaisesRegex(EnvelopeRefusal, "SESSION_POLICY_HASH_MISMATCH"):
            validate_envelope(env1, self.session, mock_trust_framework_verifier, self.current_time_ms)
            
        env2 = self.create_envelope(meta_overrides={"sessionPolicyHash": "expected-policy"})
        res = validate_envelope(env2, self.session, mock_trust_framework_verifier, self.current_time_ms)
        self.assertEqual(res["status"], "VALIDATED")

    def test_content_parts_structure(self):
        env1 = self.create_envelope(overrides={"contentParts": "just a string"})
        with self.assertRaisesRegex(EnvelopeRefusal, "INVALID_CONTENT_PARTS_STRUCTURE"):
            validate_envelope(env1, self.session, mock_trust_framework_verifier, self.current_time_ms)

        env2 = self.create_envelope(overrides={"contentParts": {"valid": "structure"}})
        res = validate_envelope(env2, self.session, mock_trust_framework_verifier, self.current_time_ms)
        self.assertEqual(res["status"], "VALIDATED")

    def test_reject_execution_authority_escalation(self):
        env1 = self.create_envelope(overrides={"authoritySource": "AGENT"})
        with self.assertRaisesRegex(EnvelopeRefusal, "AUTHORITY_SOURCE_MUST_BE_NONE"):
            validate_envelope(env1, self.session, mock_trust_framework_verifier, self.current_time_ms)
            
        env2 = self.create_envelope(overrides={"executionEligible": True})
        with self.assertRaisesRegex(EnvelopeRefusal, "EXECUTION_ELIGIBLE_MUST_BE_FALSE"):
            validate_envelope(env2, self.session, mock_trust_framework_verifier, self.current_time_ms)

    def test_reject_payload_tampering(self):
        env_raw = self.create_envelope()
        env_dict = json.loads(env_raw)
        env_dict["contentParts"] = {"text": "Tampered!"} 
        
        with self.assertRaisesRegex(EnvelopeRefusal, "PAYLOAD_HASH_MISMATCH"):
            validate_envelope(_canonical_json(env_dict), self.session, mock_trust_framework_verifier, self.current_time_ms)

    def test_wrong_sender_session(self):
        env1 = self.create_envelope(meta_overrides={"senderAgentId": "agent-c"})
        with self.assertRaisesRegex(EnvelopeRefusal, "SENDER_NOT_PARTICIPANT"):
            validate_envelope(env1, self.session, mock_trust_framework_verifier, self.current_time_ms)
            
        env2 = self.create_envelope(meta_overrides={"sessionId": "other-session"})
        with self.assertRaisesRegex(EnvelopeRefusal, "SESSION_ID_MISMATCH"):
            validate_envelope(env2, self.session, mock_trust_framework_verifier, self.current_time_ms)

    def test_duplicate_message_idempotent_and_conflicting(self):
        env_raw = self.create_envelope()
        env_dict = json.loads(env_raw)
        meta_hash = _hash_metadata(env_dict["metadata"])
        
        # Manually seed the replay dictionary to test early check logic
        self.session["seenMessageIds"] = {"msg-1": meta_hash}
        with self.assertRaisesRegex(EnvelopeRefusal, "IDEMPOTENT_REPLAY"):
            validate_envelope(env_raw, self.session, mock_trust_framework_verifier, self.current_time_ms)
            
        self.session["seenMessageIds"] = {"msg-1": "some-other-hash"}
        with self.assertRaisesRegex(EnvelopeRefusal, "CONFLICTING_REPLAY"):
            validate_envelope(env_raw, self.session, mock_trust_framework_verifier, self.current_time_ms)

    def test_out_of_order_sequence(self):
        env_raw = self.create_envelope(meta_overrides={"sequence": 2})
        with self.assertRaisesRegex(EnvelopeRefusal, "OUT_OF_ORDER_SEQUENCE"):
            validate_envelope(env_raw, self.session, mock_trust_framework_verifier, self.current_time_ms)

    def test_expired_and_future_dated(self):
        env1 = self.create_envelope(meta_overrides={"expiresAt": self.current_time_ms - 100})
        with self.assertRaisesRegex(EnvelopeRefusal, "MESSAGE_EXPIRED"):
            validate_envelope(env1, self.session, mock_trust_framework_verifier, self.current_time_ms)
            
        env2 = self.create_envelope(meta_overrides={
            "createdAt": self.current_time_ms + 61000,
            "expiresAt": self.current_time_ms + 100000
        })
        with self.assertRaisesRegex(EnvelopeRefusal, "MESSAGE_FROM_FUTURE"):
            validate_envelope(env2, self.session, mock_trust_framework_verifier, self.current_time_ms)

    def test_no_trusted_verifier(self):
        env_raw = self.create_envelope()
        with self.assertRaisesRegex(EnvelopeRefusal, "TRUSTED_SIGNATURE_VERIFIER_REQUIRED"):
            validate_envelope(env_raw, self.session, None, self.current_time_ms)

    def test_concurrent_replay_race_condition(self):
        env_bytes = self.create_envelope(meta_overrides={"messageId": "msg-1", "sequence": 1})
        
        barrier = threading.Barrier(2)
        
        def racin_validator():
            barrier.wait(timeout=2)
            try:
                return validate_envelope(env_bytes, self.session, mock_trust_framework_verifier, self.current_time_ms)
            except EnvelopeRefusal as e:
                return e

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            future1 = executor.submit(racin_validator)
            future2 = executor.submit(racin_validator)
            
            res1 = future1.result()
            res2 = future2.result()
            
        results = [res1, res2]
        
        successes = [r for r in results if isinstance(r, dict) and r.get("status") == "VALIDATED"]
        failures = [r for r in results if isinstance(r, Exception)]
        
        # Exactly one should succeed and exactly one should fail
        # Depending on thread timing, the loser hits either IDEMPOTENT_REPLAY or OUT_OF_ORDER_SEQUENCE
        self.assertEqual(len(successes), 1)
        self.assertEqual(len(failures), 1)
        err_str = str(failures[0])
        self.assertTrue("IDEMPOTENT_REPLAY" in err_str or "OUT_OF_ORDER_SEQUENCE" in err_str or "CONCURRENT_SEQUENCE_ADVANCE" in err_str)
        self.assertEqual(self.session["currentSequence"], 1)

if __name__ == "__main__":
    unittest.main()
