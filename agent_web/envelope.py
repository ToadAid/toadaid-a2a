"""CUT-A2A-P1A-20261109 — A2A message envelope deterministic validator.

Enforces structural bounds, session constraints, cryptographic payload hashing,
and strict sequence/replay checks. By standard-library policy, asymmetric
digital signature verification (e.g. RSA/Ed25519) is not implemented natively;
an explicit trusted adapter seam is provided for signature verification.

Security Invariants enforced:
- THE_MODEL_IS_NOT_THE_AUTHORITY
- A2A_CHAT_HAS_ZERO_EXECUTION_AUTHORITY
- authoritySource MUST be "NONE"
- executionEligible MUST be false
- Replay protection is enforced via in-memory session state (restart-safe
  durability requires a persisted session journal adapter; in-memory is
  volatile).
"""

import hashlib
import json
import time

MAX_ENVELOPE_BYTES = 131072  # 128KB ceiling unless session restricts further
MAX_STRING_LENGTH = 1024


class EnvelopeRefusal(ValueError):
    """Raised when an envelope fails security or structural validation."""
    pass


def _canonical_json(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(",", ":")).encode("ascii")


def _hash_payload(content_parts):
    """Canonical SHA-256 hash of the content parts."""
    return hashlib.sha256(_canonical_json(content_parts)).hexdigest()


def _hash_metadata(metadata):
    """Canonical SHA-256 hash of the metadata."""
    return hashlib.sha256(_canonical_json(metadata)).hexdigest()


def _pin_identifier(value, limit=MAX_STRING_LENGTH):
    if not isinstance(value, str) or not value or len(value) > limit:
        raise EnvelopeRefusal("INVALID_IDENTIFIER")


def validate_envelope(
    envelope_raw: bytes,
    session_manifest: dict,
    trusted_signature_verifier=None,
    current_time_ms: int = None
):
    """Validate a raw A2A envelope against a session manifest.

    trusted_signature_verifier: callable(metadata: dict, signature: str, sender_id: str) -> bool
        Required if strict signature checking is enforced. The Python standard
        library cannot natively verify ECDSA/Ed25519 signatures, so this seam
        must be satisfied by the host runtime (e.g. via a cryptography package
        adapter).
    """
    if current_time_ms is None:
        current_time_ms = int(time.time() * 1000)

    if not isinstance(envelope_raw, bytes):
        raise EnvelopeRefusal("ENVELOPE_MUST_BE_BYTES")

    if len(envelope_raw) > session_manifest.get("maxMessageBytes", MAX_ENVELOPE_BYTES):
        raise EnvelopeRefusal("ENVELOPE_EXCEEDS_SIZE_LIMIT")

    try:
        envelope = json.loads(envelope_raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        raise EnvelopeRefusal("INVALID_JSON") from e

    if not isinstance(envelope, dict):
        raise EnvelopeRefusal("ENVELOPE_MUST_BE_OBJECT")

    # 1. Zero Execution Authority Invariants
    auth_source = envelope.get("authoritySource")
    if auth_source != "NONE":
        raise EnvelopeRefusal("AUTHORITY_SOURCE_MUST_BE_NONE")

    exec_eligible = envelope.get("executionEligible")
    if exec_eligible is not False:
        raise EnvelopeRefusal("EXECUTION_ELIGIBLE_MUST_BE_FALSE")

    # 2. Strict Structure Validation
    metadata = envelope.get("metadata")
    if not isinstance(metadata, dict):
        raise EnvelopeRefusal("MISSING_OR_INVALID_METADATA")

    proto_version = metadata.get("protocolVersion")
    if proto_version != "a2a-p1a-v0":
        raise EnvelopeRefusal("UNSUPPORTED_PROTOCOL_VERSION")

    session_id = metadata.get("sessionId")
    message_id = metadata.get("messageId")
    sender_id = metadata.get("senderAgentId")
    recipient_id = metadata.get("recipientAgentId")

    _pin_identifier(session_id)
    _pin_identifier(message_id)
    _pin_identifier(sender_id)
    _pin_identifier(recipient_id)

    # 3. Session Constraints
    if session_id != session_manifest.get("sessionId"):
        raise EnvelopeRefusal("SESSION_ID_MISMATCH")

    if session_manifest.get("state") != "OPEN":
        raise EnvelopeRefusal("SESSION_NOT_OPEN")

    participants = session_manifest.get("participants", {})
    if sender_id not in participants:
        raise EnvelopeRefusal("SENDER_NOT_PARTICIPANT")
    if recipient_id not in participants:
        raise EnvelopeRefusal("RECIPIENT_NOT_PARTICIPANT")

    # 4. Time Bounds
    created_at = metadata.get("createdAt")
    expires_at = metadata.get("expiresAt")

    if not isinstance(created_at, int) or not isinstance(expires_at, int):
        raise EnvelopeRefusal("INVALID_TIMESTAMPS")

    if created_at > expires_at:
        raise EnvelopeRefusal("CREATED_AFTER_EXPIRY")

    if current_time_ms > expires_at:
        raise EnvelopeRefusal("MESSAGE_EXPIRED")

    # Optional clock skew check: message shouldn't be too far in the future
    if created_at > current_time_ms + 60000:  # 60s skew allowance
        raise EnvelopeRefusal("MESSAGE_FROM_FUTURE")

    # 5. Cryptographic Integrity
    content_parts = envelope.get("contentParts")
    expected_payload_hash = _hash_payload(content_parts)

    if metadata.get("payloadHash") != expected_payload_hash:
        raise EnvelopeRefusal("PAYLOAD_HASH_MISMATCH")

    # 6. Sequence and Replay (Memory-based)
    seq = metadata.get("sequence")
    if not isinstance(seq, int) or seq <= 0:
        raise EnvelopeRefusal("INVALID_SEQUENCE")

    if seq > session_manifest.get("maxTurns", 0):
        raise EnvelopeRefusal("MAX_TURNS_EXCEEDED")

    current_sequence = session_manifest.get("currentSequence", 0)
    if seq != current_sequence + 1:
        raise EnvelopeRefusal("OUT_OF_ORDER_SEQUENCE")

    seen_ids = session_manifest.get("seenMessageIds", {})
    env_hash = _hash_metadata(metadata)

    if message_id in seen_ids:
        if seen_ids[message_id] == env_hash:
            raise EnvelopeRefusal("IDEMPOTENT_REPLAY")
        else:
            raise EnvelopeRefusal("CONFLICTING_REPLAY")

    # 7. Integrity / Authentication Validation via Trusted Seam
    signature = envelope.get("signature")
    if not isinstance(signature, str):
        raise EnvelopeRefusal("MISSING_OR_INVALID_SIGNATURE")

    if trusted_signature_verifier is None:
        raise EnvelopeRefusal("TRUSTED_SIGNATURE_VERIFIER_REQUIRED")

    if not trusted_signature_verifier(metadata, signature, sender_id):
        raise EnvelopeRefusal("INVALID_SIGNATURE")

    return {
        "status": "VALIDATED",
        "envelope": envelope,
        "metadataHash": env_hash,
        "deliverable": False  # Invariant: A2A chat carries zero execution authority
    }
