import json
import unittest

from agent_web.envelope import (
    validate_envelope, EnvelopeRefusal, _canonical_json, _hash_payload, _hash_metadata
)


def dummy_signature_verifier(metadata, signature, sender_id):
    """Synthetic offline signature verifier for testing structural constraints."""
    if signature == "invalid_sig":
        return False
    if sender_id == "unauthorized_agent":
        return False
    return True


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
            
        payload_hash = _hash_payload(content_parts)
        
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
            "sessionPolicyHash": "dummy-policy",
            "payloadHash": payload_hash
        }
        if meta_overrides:
            metadata.update(meta_overrides)
            if "contentParts" in overrides if overrides else False:
                # If content parts were overridden but not payloadHash, make sure payloadHash matches unless intentionally tampered
                pass
            
        env = {
            "metadata": metadata,
            "contentParts": content_parts,
            "signature": "dummy_valid_sig",
            "authoritySource": "NONE",
            "executionEligible": False
        }
        if overrides:
            env.update(overrides)
            
        return _canonical_json(env)

    def test_valid_envelope_acceptance(self):
        env_bytes = self.create_envelope()
        result = validate_envelope(env_bytes, self.session, dummy_signature_verifier, self.current_time_ms)
        self.assertEqual(result["status"], "VALIDATED")
        self.assertFalse(result["deliverable"])
        self.assertEqual(result["envelope"]["metadata"]["messageId"], "msg-1")

    def test_reject_execution_authority_escalation(self):
        env1 = self.create_envelope(overrides={"authoritySource": "AGENT"})
        with self.assertRaisesRegex(EnvelopeRefusal, "AUTHORITY_SOURCE_MUST_BE_NONE"):
            validate_envelope(env1, self.session, dummy_signature_verifier, self.current_time_ms)
            
        env2 = self.create_envelope(overrides={"executionEligible": True})
        with self.assertRaisesRegex(EnvelopeRefusal, "EXECUTION_ELIGIBLE_MUST_BE_FALSE"):
            validate_envelope(env2, self.session, dummy_signature_verifier, self.current_time_ms)

    def test_reject_payload_tampering(self):
        env_raw = self.create_envelope()
        env_dict = json.loads(env_raw)
        # Tamper without updating the hash in metadata
        env_dict["contentParts"] = {"text": "Tampered!"} 
        
        with self.assertRaisesRegex(EnvelopeRefusal, "PAYLOAD_HASH_MISMATCH"):
            validate_envelope(_canonical_json(env_dict), self.session, dummy_signature_verifier, self.current_time_ms)

    def test_reject_invalid_authentication(self):
        env_raw = self.create_envelope(overrides={"signature": "invalid_sig"})
        with self.assertRaisesRegex(EnvelopeRefusal, "INVALID_SIGNATURE"):
            validate_envelope(env_raw, self.session, dummy_signature_verifier, self.current_time_ms)

    def test_wrong_sender_session(self):
        env1 = self.create_envelope(meta_overrides={"senderAgentId": "agent-c"})
        with self.assertRaisesRegex(EnvelopeRefusal, "SENDER_NOT_PARTICIPANT"):
            validate_envelope(env1, self.session, dummy_signature_verifier, self.current_time_ms)
            
        env2 = self.create_envelope(meta_overrides={"sessionId": "other-session"})
        with self.assertRaisesRegex(EnvelopeRefusal, "SESSION_ID_MISMATCH"):
            validate_envelope(env2, self.session, dummy_signature_verifier, self.current_time_ms)

    def test_duplicate_message_idempotent_and_conflicting(self):
        env_raw = self.create_envelope()
        env_dict = json.loads(env_raw)
        meta_hash = _hash_metadata(env_dict["metadata"])
        
        # Idempotent replay
        self.session["seenMessageIds"] = {"msg-1": meta_hash}
        with self.assertRaisesRegex(EnvelopeRefusal, "IDEMPOTENT_REPLAY"):
            validate_envelope(env_raw, self.session, dummy_signature_verifier, self.current_time_ms)
            
        # Conflicting replay
        self.session["seenMessageIds"] = {"msg-1": "some-other-hash"}
        with self.assertRaisesRegex(EnvelopeRefusal, "CONFLICTING_REPLAY"):
            validate_envelope(env_raw, self.session, dummy_signature_verifier, self.current_time_ms)

    def test_out_of_order_sequence(self):
        env_raw = self.create_envelope(meta_overrides={"sequence": 2})
        with self.assertRaisesRegex(EnvelopeRefusal, "OUT_OF_ORDER_SEQUENCE"):
            validate_envelope(env_raw, self.session, dummy_signature_verifier, self.current_time_ms)

    def test_expired_and_future_dated(self):
        # Expired Message
        env1 = self.create_envelope(meta_overrides={"expiresAt": self.current_time_ms - 100})
        with self.assertRaisesRegex(EnvelopeRefusal, "MESSAGE_EXPIRED"):
            validate_envelope(env1, self.session, dummy_signature_verifier, self.current_time_ms)
            
        # Future Message (Clock Skew)
        env2 = self.create_envelope(meta_overrides={
            "createdAt": self.current_time_ms + 61000,
            "expiresAt": self.current_time_ms + 100000
        })
        with self.assertRaisesRegex(EnvelopeRefusal, "MESSAGE_FROM_FUTURE"):
            validate_envelope(env2, self.session, dummy_signature_verifier, self.current_time_ms)

    def test_oversized_input(self):
        big_text = "A" * 9000
        env_raw = self.create_envelope(
            overrides={"contentParts": {"text": big_text}},
            meta_overrides={"payloadHash": _hash_payload({"text": big_text})}
        )
        with self.assertRaisesRegex(EnvelopeRefusal, "ENVELOPE_EXCEEDS_SIZE_LIMIT"):
            validate_envelope(env_raw, self.session, dummy_signature_verifier, self.current_time_ms)

    def test_no_trusted_verifier(self):
        env_raw = self.create_envelope()
        with self.assertRaisesRegex(EnvelopeRefusal, "TRUSTED_SIGNATURE_VERIFIER_REQUIRED"):
            validate_envelope(env_raw, self.session, None, self.current_time_ms)


if __name__ == "__main__":
    unittest.main()
