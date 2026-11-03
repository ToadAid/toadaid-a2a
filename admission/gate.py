"""CUT-A2A-P0D-A1-20261103 — registered-agent A2A participation gate and router.

Transport-independent, framework-neutral acceptance gate: an A2A message is
admitted ONLY after independently verifying trusted registration and
participation decisions held by an injected trusted adapter. The trusted
adapter query is an exact three-field identity context
{agentRef, tenantRef, ownerRef}; registration claims supplied by an Agent
Card, a message body, or a browser are structurally refused (unexpected
request keys are not admitted, and the request schema carries no claim
fields at all).

Preserved invariant: A2A_CHAT_HAS_ZERO_EXECUTION_AUTHORITY — an admitted
message authorizes no tool, payment, wallet, deployment, protected-host
mutation, or registration change. Authority flags are all false by
construction and re-asserted on every admission receipt.

Journal conventions are reused from the validated cut history (local-probe
Journal): canonical-digest hash chain, idempotent replay of an identical
(messageId, digest) pair, conflicting replay refused, entry recorded and
fsynced-style committed BEFORE any delivery result, single bounded
capacity, and metadata only — message bodies never enter the journal.
Restart support: export_state()/restore() verify the hash chain and refuse
foreign or broken state.
"""

import copy
import datetime
import hashlib

from .model import (
    DECISION_KEYS,
    PARTICIPATION_SCOPES,
    build_registration_decision,
    canonical_json,
    parse_iso_utc,
)
from observatory.model import (
    IDENTIFIER_RE,
    ObservatoryRefusal,
)

__all__ = [
    "GATE_KIND",
    "GATE_SCHEMA_VERSION",
    "GATE_STATUS",
    "A2A_CHAT_HAS_ZERO_EXECUTION_AUTHORITY",
    "MESSAGE_TYPES",
    "MAX_MESSAGE_BODY_CHARS",
    "MAX_REQUEST_BYTES",
    "MAX_JOURNAL_ENTRIES",
    "REQUEST_KEYS",
    "RECIPIENT_KEYS",
    "MESSAGE_KEYS",
    "AdmissionRefused",
    "ParticipationRefused",
    "AdmissionJournal",
    "RegisteredAgentGate",
    "synthetic_registration_adapter",
]

GATE_KIND = "toadaid-a2a-participation-decision"
GATE_SCHEMA_VERSION = "0.1.0"
GATE_STATUS = "LOCAL_SYNTHETIC_ENGINE_NOT_DEPLOYED"

# Constitutional invariant, kept verbatim (guarded by tests and the
# canonical master note; this gate never reopens it).
A2A_CHAT_HAS_ZERO_EXECUTION_AUTHORITY = "A2A_CHAT_HAS_ZERO_EXECUTION_AUTHORITY"

MESSAGE_TYPES = frozenset({"conversation_message", "task_update", "status_report"})
MAX_MESSAGE_BODY_CHARS = 256
MAX_REQUEST_BYTES = 8192
MAX_JOURNAL_ENTRIES = 1024

REQUEST_KEYS = frozenset({
    "agentRef", "tenantRef", "ownerRef", "participationScope",
    "messageId", "correlationId", "occurredAtUtc", "message",
})
MESSAGE_KEYS = frozenset({"messageType", "body"})
RECIPIENT_KEYS = frozenset({"agentRef", "tenantRef", "ownerRef"})

IDENTIFIER_FIELDS = ("agentRef", "tenantRef", "ownerRef")
ISO_FIELDS = ("occurredAtUtc",)


class AdmissionRefused(ValueError):
    """Deny-first refusal of an out-of-bounds admission input."""


class ParticipationRefused(PermissionError):
    """An admission attempt without a trusted, current authorization."""


def _pin_identifier(value, code):
    if not isinstance(value, str) or not IDENTIFIER_RE.match(value):
        raise AdmissionRefused(code)


def _request_digest(request):
    return hashlib.sha256(canonical_json(request).encode("ascii")).hexdigest()


class AdmissionJournal:
    """Bounded, hash-chained, metadata-only admission journal.

    Entries store {messageId, requestDigest, prev, digest} — canonical
    digests only, never message bodies. Same (messageId, digest) replays
    idempotently to the prior outcome; a conflicting digest under the same
    messageId is refused. Capacity is bounded and fails closed.
    """

    record_keys = frozenset({"messageId", "requestDigest", "prev", "digest"})

    def __init__(self, capacity=MAX_JOURNAL_ENTRIES):
        if isinstance(capacity, bool) or not isinstance(capacity, int) \
                or capacity < 1 or capacity > MAX_JOURNAL_ENTRIES:
            raise ObservatoryRefusal("ADMISSION_JOURNAL_CAPACITY_OUT_OF_BOUNDS")
        self.capacity = capacity
        self._entries = []
        self._by_message_id = {}

    def check_and_record(self, message_id, request_digest):
        entry = self._by_message_id.get(message_id)
        if entry is not None:
            if entry["requestDigest"] == request_digest:
                return {"journalResult": "replayed-idempotent",
                        "digest": entry["digest"]}
            raise ParticipationRefused("REPLAY_MESSAGE_ID_CONFLICT")
        if len(self._entries) >= self.capacity:
            raise ObservatoryRefusal("ADMISSION_JOURNAL_FULL")
        prev = self._entries[-1]["digest"] if self._entries else "genesis"
        record = {
            "messageId": message_id,
            "requestDigest": request_digest,
            "prev": prev,
            "digest": hashlib.sha256(canonical_json({
                "messageId": message_id,
                "requestDigest": request_digest,
                "prev": prev,
            }).encode("ascii")).hexdigest(),
        }
        # Journal-before-delivery: the entry is committed before any
        # delivery result is produced.
        self._entries.append(record)
        self._by_message_id[message_id] = record
        return {"journalResult": "recorded", "digest": record["digest"]}

    def entries(self):
        return copy.deepcopy(self._entries)

    def export_state(self):
        return {
            "kind": "toadaid-a2a-admission-journal",
            "schemaVersion": "0.1.0",
            "capacity": self.capacity,
            "entries": self.entries(),
        }

    @classmethod
    def restore(cls, state, capacity=MAX_JOURNAL_ENTRIES):
        journal = cls(capacity=capacity)
        if not isinstance(state, dict) or set(state) != set(journal.export_state()):
            raise ObservatoryRefusal("ADMISSION_JOURNAL_STATE_NOT_ADMITTED")
        if state["kind"] != "toadaid-a2a-admission-journal" \
                or state["schemaVersion"] != "0.1.0":
            raise ObservatoryRefusal("ADMISSION_JOURNAL_STATE_NOT_ADMITTED")
        entries = state["entries"]
        if not isinstance(entries, list):
            raise ObservatoryRefusal("ADMISSION_JOURNAL_STATE_NOT_ADMITTED")
        if len(entries) > journal.capacity:
            raise ObservatoryRefusal("ADMISSION_JOURNAL_CAPACITY_OUT_OF_BOUNDS")
        prev = "genesis"
        for record in entries:
            if not isinstance(record, dict) or set(record) != cls.record_keys:
                raise ObservatoryRefusal("ADMISSION_JOURNAL_CHAIN_BROKEN")
            if record["prev"] != prev or record["messageId"] \
                    in journal._by_message_id:
                raise ObservatoryRefusal("ADMISSION_JOURNAL_CHAIN_BROKEN")
            expected = hashlib.sha256(canonical_json({
                "messageId": record["messageId"],
                "requestDigest": record["requestDigest"],
                "prev": record["prev"],
            }).encode("ascii")).hexdigest()
            if record["digest"] != expected:
                raise ObservatoryRefusal("ADMISSION_JOURNAL_CHAIN_BROKEN")
            journal._entries.append(dict(record))
            journal._by_message_id[record["messageId"]] = record
            prev = record["digest"]
        return journal


def synthetic_registration_adapter(decisions,
                                   adapter_id="synthetic-offline-registration-adapter"):
    """SYNTHETIC OFFLINE ONLY — NOT A REAL AUTHENTICATION SYSTEM.

    Maps agentRef -> adapter-verified decisions for offline tests and the
    two-agent synthetic rehearsal. Production stance stays fail-closed:
    a real deployment injects an independently verified adapter instead,
    and this factory is never wired to production.
    """
    if not isinstance(decisions, dict) and decisions is not None:
        raise ObservatoryRefusal("ADAPTER_DECISIONS_SHAPE_INVALID")
    frozen = dict(decisions) if decisions else {}
    return lambda query: frozen.get(query.get("agentRef"))


class RegisteredAgentGate:
    """Executable, transport-independent registered-agent gate.

    Fails closed unless a trusted registration adapter AND a clock source
    are injected. The adapter is a trusted callable: it returns the
    independently verified registration decision for an exact identity
    query, or None for no decision. Every returned decision is
    re-validated and re-bound to the request context before use.
    """

    def __init__(self, trusted_registration_adapter=None, now=None, journal=None):
        self.trusted_registration_adapter = trusted_registration_adapter
        self.now = now
        self.journal = journal if journal is not None else AdmissionJournal()

    # -- sender authorization ------------------------------------------------

    def authorize(self, request):
        """Verify one participation request; no delivery, no journal write."""
        scope = self._validated_request_scope(request)
        query = {field: scope[field] for field in ("agentRef", "tenantRef", "ownerRef")}
        decision = self._verified_decision(query, require_scope=scope["participationScope"])
        return self._admission_receipt(scope, decision)

    # -- two-agent routing ---------------------------------------------------

    def route(self, sender_request, recipient_context):
        """Registered sender -> gate -> registered recipient, journal-first.

        ``recipient_context`` is the recipient's own exact identity context
        {"agentRef", "tenantRef", "ownerRef"}. Both agents are independently
        verified under their own binding: the sender needs
        'a2a-message-send', the recipient needs 'a2a-message-receive'.
        Tenant isolation is explicit policy: cross-tenant delivery is
        refused (REACHABLE refusal, not dead code). The journal entry is
        committed before the delivery result.
        """
        scope = self._validated_request_scope(sender_request)
        if not isinstance(recipient_context, dict) \
                or set(recipient_context) != set(RECIPIENT_KEYS):
            raise AdmissionRefused("RECIPIENT_KEYS_NOT_ADMITTED")
        _pin_identifier(recipient_context["agentRef"], "RECIPIENT_REF_NOT_ADMITTED")
        if recipient_context["agentRef"] == scope["agentRef"] \
                and recipient_context["tenantRef"] == scope["tenantRef"] \
                and recipient_context["ownerRef"] == scope["ownerRef"]:
            raise AdmissionRefused("SELF_DELIVERY_NOT_ADMITTED")
        sender_query = {field: scope[field]
                        for field in ("agentRef", "tenantRef", "ownerRef")}
        sender_decision = self._verified_decision(
            sender_query, require_scope=scope["participationScope"])

        recipient_decision = self._verified_decision(
            dict(recipient_context), require_scope="a2a-message-receive")
        if recipient_decision["tenantRef"] != sender_decision["tenantRef"]:
            raise ParticipationRefused("CROSS_TENANT_DELIVERY_REFUSED")

        digest = _request_digest(sender_request)
        journal_result = self.journal.check_and_record(
            scope["messageId"], digest)
        return self._delivery_receipt(scope, sender_decision, recipient_decision,
                                      journal_result)

    # -- internals ------------------------------------------------------------

    def _now_utc(self):
        if self.now is None or not callable(self.now):
            raise ParticipationRefused("CLOCK_SOURCE_REQUIRED")
        stamp = self.now()
        if not isinstance(stamp, datetime.datetime):
            raise ParticipationRefused("CLOCK_SOURCE_REQUIRED")
        return stamp.replace(tzinfo=None) if stamp.tzinfo is not None else stamp

    def _validated_request_scope(self, request):
        if not isinstance(request, dict):
            raise AdmissionRefused("REQUEST_SHAPE_INVALID")
        if set(request) != REQUEST_KEYS:
            # An Agent-Card / message-body / browser registration claim has
            # no field to live in — it is refused on the first extra key.
            raise AdmissionRefused("REQUEST_KEYS_NOT_ADMITTED")
        checked = {}
        for field in IDENTIFIER_FIELDS:
            _pin_identifier(request[field], "REQUEST_" + field.upper() + "_NOT_ADMITTED")
            checked[field] = request[field]
        if request["participationScope"] not in PARTICIPATION_SCOPES:
            raise AdmissionRefused("PARTICIPATION_SCOPE_NOT_ADMITTED")
        checked["participationScope"] = request["participationScope"]
        for field in ("messageId", "correlationId"):
            _pin_identifier(request[field], "REQUEST_" + field.upper() + "_NOT_ADMITTED")
            checked[field] = request[field]
        checked["occurredAtUtc"] = request["occurredAtUtc"]
        if parse_iso_utc(checked["occurredAtUtc"]) is None:
            raise AdmissionRefused("REQUEST_TIMESTAMP_NOT_ADMITTED")
        message = request["message"]
        if not isinstance(message, dict) or set(message) != MESSAGE_KEYS:
            raise AdmissionRefused("MESSAGE_KEYS_NOT_ADMITTED")
        if message["messageType"] not in MESSAGE_TYPES:
            raise AdmissionRefused("MESSAGE_TYPE_NOT_ADMITTED")
        body = message["body"]
        if not isinstance(body, str) or not body \
                or len(body) > MAX_MESSAGE_BODY_CHARS:
            raise AdmissionRefused("MESSAGE_BODY_NOT_ADMITTED")
        checked["message"] = message
        if len(canonical_json(request).encode("ascii")) > MAX_REQUEST_BYTES:
            raise AdmissionRefused("REQUEST_OUT_OF_BOUNDS")
        return checked

    def _verified_decision(self, query, require_scope=None):
        adapter = self.trusted_registration_adapter
        if adapter is None or not callable(adapter):
            raise ParticipationRefused("ADMISSION_AUTHORIZATION_REQUIRED")
        if set(query) != {"agentRef", "tenantRef", "ownerRef"}:
            raise AdmissionRefused("ADAPTER_QUERY_NOT_ADMITTED")
        raw = adapter(query)
        if raw is None:
            raise ParticipationRefused("REGISTRATION_NOT_FOUND")
        if not isinstance(raw, dict) or set(raw) != DECISION_KEYS:
            raise ParticipationRefused("REGISTRATION_DECISION_TAMPERED")
        decision = build_registration_decision(
            agent_ref=raw["agentRef"],
            owner_ref=raw["ownerRef"],
            tenant_ref=raw["tenantRef"],
            registration_status=raw["registrationStatus"],
            credential_generation=raw["credentialGeneration"],
            revocation_epoch=raw["revocationEpoch"],
            framework=raw["framework"],
            adapter_id=raw["adapterId"],
            decision_observed_at_utc=raw["decisionObservedAtUtc"],
            evidence_expires_at_utc=raw["evidenceExpiresAtUtc"],
            participation_scopes=raw["participationScopes"],
        )
        if canonical_json(decision) != canonical_json(raw):
            # Rebuild must reproduce the adapter record exactly: an adapter
            # trying to smuggle extra fields fails closed here.
            raise ParticipationRefused("REGISTRATION_DECISION_TAMPERED")
        for field in ("agentRef", "tenantRef", "ownerRef"):
            if decision[field] != query[field]:
                raise ParticipationRefused("REGISTRATION_CONTEXT_MISMATCH")
        status = decision["registrationStatus"]
        if status == "registered":
            pass
        elif status == "revoked":
            raise ParticipationRefused("REGISTRATION_REVOKED")
        elif status == "suspended":
            raise ParticipationRefused("REGISTRATION_SUSPENDED")
        elif status == "unregistered":
            raise ParticipationRefused("REGISTRATION_UNREGISTERED")
        else:
            raise ParticipationRefused("REGISTRATION_UNKNOWN_STATUS")

        now = self._now_utc()
        expires = parse_iso_utc(decision["evidenceExpiresAtUtc"])
        if expires is None or expires <= now:
            raise ParticipationRefused("REGISTRATION_EVIDENCE_EXPIRED")

        required = require_scope if require_scope is not None \
            else query.get("participationScope")
        if required is not None and required not in decision["participationScopes"]:
            raise ParticipationRefused("PARTICIPATION_SCOPE_NOT_AUTHORIZED")
        return decision

    def _base_receipt(self, scope, decision):
        return {
            "kind": GATE_KIND,
            "schemaVersion": GATE_SCHEMA_VERSION,
            "status": GATE_STATUS,
            "messageId": scope["messageId"],
            "correlationId": scope["correlationId"],
            "occurredAtUtc": scope["occurredAtUtc"],
            "tenantRef": scope["tenantRef"],
            "senderRef": scope["agentRef"],
            "framework": decision["framework"],
            "boundary": A2A_CHAT_HAS_ZERO_EXECUTION_AUTHORITY,
            "authorityFlags": {
                "executionAuthorized": False,
                "toolUseAuthorized": False,
                "paymentAuthorized": False,
                "deploymentAuthorized": False,
                "agentRegistrationChangeAuthorized": False,
                "publicDirectoryExposed": False,
            },
        }

    def _admission_receipt(self, scope, decision):
        receipt = self._base_receipt(scope, decision)
        receipt["decision"] = "AUTHORIZED_LOCAL_SYNTHETIC"
        receipt["participationScope"] = scope["participationScope"]
        return receipt

    def _delivery_receipt(self, scope, sender_decision, recipient_decision,
                          journal_result):
        receipt = self._base_receipt(scope, sender_decision)
        receipt["decision"] = "DELIVERED_LOCAL_SYNTHETIC"
        receipt["recipientRef"] = recipient_decision["agentRef"]
        receipt["journalResult"] = journal_result["journalResult"]
        return receipt