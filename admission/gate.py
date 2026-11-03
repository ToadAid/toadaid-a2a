"""CUT-A2A-P0D-A1-20261103 — registered-agent A2A participation gate and router.

Transport-independent, framework-neutral acceptance gate: an A2A message is
admitted ONLY after independently verifying trusted registration and
participation decisions held by an injected trusted adapter. The trusted
adapter query is an exact three-field identity context
{agentRef, tenantRef, ownerRef}; registration claims supplied by an Agent
Card, a message body, or a browser are structurally refused (unexpected
request keys are not admitted, and the request schema carries no claim
fields at all).

Caller identity (R1-4): registration alone is NOT authentication — anyone
who knows a registered agent's identifiers could claim that identity. The
gate therefore requires, on EVERY authorize()/route() call, a fail-closed
trusted caller-identity verifier (a second injected seam) that binds an
OPAQUE caller credential to an independently verified
{agentRef, tenantRef, ownerRef} principal. The request context must equal
that principal binding exactly; identity strings inside requests, Agent
Cards, or message bodies never authenticate anyone, and a None credential
refuses everything. No production authentication, Portal login, or live
agent connection exists in this cut; the synthetic caller verifier and
CallerCredential fixture are explicitly SYNTHETIC OFFLINE ONLY.

Credential lifecycle (P0D-A2, REVOCATION_OVERRIDES_PRIOR_APPROVAL): a
registration decision carrying credentialGeneration/revocationEpoch does
NOT prove those values are current. EVERY authorize()/route() call also
fetches CURRENT lifecycle state for each participating agent from a third
independently verified seam (trusted_lifecycle_source), under the same
exact three-field identity context. A decision must carry the CURRENT
generation and CURRENT revocation epoch (older = stale, higher = a
future claim); any lifecycle status other than "registered" — including
suspension, revocation, and EMERGENCY DISABLEMENT — refuses, and an
identical replay never bypasses a revocation that occurred after its
original admission (lifecycle is enforced before the journal check, so a
revoked agent's replay refuses and appends NO journal entry). The gate
also keeps a per-agent monotonic high-watermark over source-reported
generations and epochs to detect state ROLLBACK; like the journal this
watermark is IN-MEMORY ONLY — it provides no durable rollback protection
after process restart, and no cryptographic provenance is invented.
No agent-supplied claim can establish its own current credential state.

Preserved invariant: A2A_CHAT_HAS_ZERO_EXECUTION_AUTHORITY — an admitted
message authorizes no tool, payment, wallet, deployment, protected-host
mutation, or registration change. Authority flags are all false by
construction and re-asserted on every admission receipt.

Journal conventions are reused from the validated cut history (local-probe
Journal): canonical-digest hash chain, idempotent replay of an identical
(messageId, deliveryDigest) pair, conflicting replay refused, single
bounded capacity, and metadata only — message bodies never enter the
journal. Replay identity binds the complete delivery context (R1-2): the
canonical, independently verified recipient identity is part of the
journal key, so the same message ID aimed at a different recipient is a
CONFLICTING replay, never an identical one. The entry is committed before
any delivery result.

Journal limits (disclosed): the journal is IN-MEMORY state — not fsynced,
replicated, or durable storage; losing it does not weaken admission
decisions, which are recomputed from the trusted seams as needed. A
restored hash chain verifies tamper-evidence of the recorded sequence
ONLY: a hash chain does NOT authenticate externally supplied history, and
a party who fabricates and consistently re-signs a chain can construct
never-recorded entries undetectably. Trust in restored state is a
deployment decision reserved for a future durable cut. Restart support:
export_state()/restore() refuse foreign, malformed, or tampered-broken
state.
"""

import copy
import datetime
import hashlib

from .model import (
    ADAPTER_ID_MAX_CHARS,
    DECISION_KEYS,
    PARTICIPATION_SCOPES,
    build_registration_decision,
    canonical_json,
    parse_iso_utc,
)
from .lifecycle import (
    LIFECYCLE_STATE_KEYS,
    build_lifecycle_state,
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
    "PRINCIPAL_KEYS",
    "RECIPIENT_KEYS",
    "MESSAGE_KEYS",
    "AdmissionRefused",
    "ParticipationRefused",
    "AdmissionJournal",
    "CallerCredential",
    "RegisteredAgentGate",
    "synthetic_caller_credential",
    "synthetic_caller_verifier",
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
# Every independently verified agent-side identity context — the trusted
# principal binding of a caller, and a delivery recipient — is exactly
# these three fields. RECIPIENT_KEYS is the delivery-facing alias.
PRINCIPAL_KEYS = frozenset({"agentRef", "tenantRef", "ownerRef"})
RECIPIENT_KEYS = PRINCIPAL_KEYS
MESSAGE_KEYS = frozenset({"messageType", "body"})

IDENTIFIER_FIELDS = ("agentRef", "tenantRef", "ownerRef")


class AdmissionRefused(ValueError):
    """Deny-first refusal of an out-of-bounds admission input."""


class ParticipationRefused(PermissionError):
    """An admission attempt without a trusted, current authorization."""


class CallerCredential:
    """Opaque, hashable caller credential (SYNTHETIC fixture).

    Presented by the transport layer to the trusted caller verifier.
    It is NOT a self-asserted identity string, is never accepted from
    inside a request body, and carries no parseable registration
    evidence. Contents are opaque: even the fixture label is not a
    meaningful identity in itself — only the VERIFIER's binding is.
    """

    def __init__(self, label):
        if not isinstance(label, str) or not label \
                or len(label) > ADAPTER_ID_MAX_CHARS:
            raise ObservatoryRefusal("CALLER_CREDENTIAL_LABEL_NOT_ADMITTED")
        object.__setattr__(self, "_label", label)

    def __setattr__(self, name, value):
        raise ObservatoryRefusal("CALLER_CREDENTIAL_NOT_ADMITTED")

    def __repr__(self):
        return "CallerCredential(<opaque>)"


def synthetic_caller_credential(label):
    """SYNTHETIC OFFLINE ONLY — build one opaque fixture credential."""
    return CallerCredential(label)


def _pin_identifier(value, code):
    if not isinstance(value, str) or not IDENTIFIER_RE.match(value):
        raise AdmissionRefused(code)


def synthetic_caller_verifier(bindings,
                              verifier_id="synthetic-offline-caller-verifier"):
    """SYNTHETIC OFFLINE ONLY — NOT A REAL AUTHENTICATION SYSTEM.

    Maps opaque CallerCredential objects -> independently verified
    principal bindings {agentRef, tenantRef, ownerRef}. The binding is
    the verifier's own verified knowledge of WHO THE CALLER IS — a
    registration record lookup is a different concern and can never be
    substituted for it. Production stance stays fail-closed: a real
    deployment injects a trusted verifier (e.g. server-side session or
    challenge-based identity) instead, and this factory is never wired
    to production.
    """
    if not isinstance(bindings, dict):
        raise ObservatoryRefusal("CALLER_BINDINGS_SHAPE_INVALID")
    frozen = {}
    for credential, binding in bindings.items():
        if not isinstance(credential, CallerCredential):
            raise ObservatoryRefusal("CALLER_CREDENTIAL_NOT_ADMITTED")
        if not isinstance(binding, dict) or set(binding) != set(PRINCIPAL_KEYS):
            raise ObservatoryRefusal("CALLER_BINDING_NOT_ADMITTED")
        checked = {}
        for field in ("agentRef", "tenantRef", "ownerRef"):
            value = binding[field]
            if not isinstance(value, str) or not IDENTIFIER_RE.match(value):
                raise ObservatoryRefusal("CALLER_BINDING_NOT_ADMITTED")
            checked[field] = value
        frozen[credential] = {**checked}
    return lambda credential: copy.deepcopy(frozen.get(credential))


def _request_digest(request):
    return hashlib.sha256(canonical_json(request).encode("ascii")).hexdigest()


def _delivery_digest(request_digest, recipient_identity):
    """Replay key binding the request to its verified recipient (R1-2)."""
    return hashlib.sha256(canonical_json({
        "requestDigest": request_digest,
        "recipientAgentRef": recipient_identity["agentRef"],
        "recipientTenantRef": recipient_identity["tenantRef"],
        "recipientOwnerRef": recipient_identity["ownerRef"],
    }).encode("ascii")).hexdigest()


class AdmissionJournal:
    """Bounded, hash-chained, metadata-only, IN-MEMORY admission journal.

    Entries store {messageId, deliveryDigest, prev, digest} — canonical
    digests only, never message bodies. The deliveryDigest binds the
    complete delivery context (request digest + verified recipient
    identity), so the same messageId aimed at a different recipient is a
    conflicting replay. Same (messageId, deliveryDigest) replays
    idempotently to the prior outcome; a conflicting digest under the
    same messageId is refused. Capacity is bounded and fails closed.

    THIS IS NOT DURABLE STORAGE: the journal lives in process memory —
    nothing is fsynced, replicated, or persisted across process death.
    That is acceptable here because admission decisions are always
    recomputed from the trusted seams; the journal is audit metadata.
    A restored chain is tamper-EVIDENCE only: re-verified digests prove
    the sequence was not edited after export, but a hash chain alone
    does NOT authenticate externally supplied history — anyone can
    fabricate and consistently re-sign a whole chain.
    """

    record_keys = frozenset({"messageId", "deliveryDigest", "prev", "digest"})

    def __init__(self, capacity=MAX_JOURNAL_ENTRIES):
        if isinstance(capacity, bool) or not isinstance(capacity, int) \
                or capacity < 1 or capacity > MAX_JOURNAL_ENTRIES:
            raise ObservatoryRefusal("ADMISSION_JOURNAL_CAPACITY_OUT_OF_BOUNDS")
        self.capacity = capacity
        self._entries = []
        self._by_message_id = {}

    def check_and_record(self, message_id, delivery_digest):
        entry = self._by_message_id.get(message_id)
        if entry is not None:
            if entry["deliveryDigest"] == delivery_digest:
                return {"journalResult": "replayed-idempotent",
                        "digest": entry["digest"]}
            raise ParticipationRefused("REPLAY_MESSAGE_ID_CONFLICT")
        if len(self._entries) >= self.capacity:
            raise ObservatoryRefusal("ADMISSION_JOURNAL_FULL")
        prev = self._entries[-1]["digest"] if self._entries else "genesis"
        record = {
            "messageId": message_id,
            "deliveryDigest": delivery_digest,
            "prev": prev,
            "digest": hashlib.sha256(canonical_json({
                "messageId": message_id,
                "deliveryDigest": delivery_digest,
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
                "deliveryDigest": record["deliveryDigest"],
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

    Maps agentRef -> adapter-verified registration decisions for offline
    tests and the two-agent synthetic rehearsal. Registration answers
    WHO IS ENROLLED AND WHAT THEY MAY DO; it is NOT caller
    authentication — pair this adapter with a trusted caller verifier
    (R1-4). Production stance stays fail-closed: a real deployment
    injects an independently verified adapter instead, and this factory
    is never wired to production.
    """
    if not isinstance(decisions, dict) and decisions is not None:
        raise ObservatoryRefusal("ADAPTER_DECISIONS_SHAPE_INVALID")
    frozen = dict(decisions) if decisions else {}
    return lambda query: frozen.get(query.get("agentRef"))


class RegisteredAgentGate:
    """Executable, transport-independent registered-agent gate.

    Fails closed unless FOUR trust seams are injected: a trusted caller
    verifier (WHO is asking — R1-4), a trusted registration adapter
    (WHAT the registered agent may do), a trusted credential-lifecycle
    source (WHICH generation and revocation epoch are CURRENT — P0D-A2),
    and a clock source (WHEN the evidence is still fresh). Every caller
    credential is bound to an independently verified principal; every
    returned decision is re-validated and re-bound to the request
    context before use; every decision's generation and epoch are
    checked against independently verified CURRENT lifecycle state.
    """

    def __init__(self, trusted_registration_adapter=None,
                 trusted_caller_verifier=None, trusted_lifecycle_source=None,
                 now=None, journal=None):
        self.trusted_registration_adapter = trusted_registration_adapter
        self.trusted_caller_verifier = trusted_caller_verifier
        self.trusted_lifecycle_source = trusted_lifecycle_source
        self.now = now
        self.journal = journal if journal is not None else AdmissionJournal()
        # P0D-A2: per-agent monotonic high-watermark over SOURCE-reported
        # lifecycle counters, detecting state rollback. IN-MEMORY ONLY —
        # no durable rollback protection survives process restart.
        self._lifecycle_high_water = {}

    # -- caller identity -------------------------------------------------

    def _verified_caller_principal(self, caller_credential):
        verifier = self.trusted_caller_verifier
        if verifier is None or not callable(verifier):
            raise ParticipationRefused("CALLER_AUTHENTICATOR_NOT_TRUSTED")
        if not isinstance(caller_credential, CallerCredential):
            # Identity strings, dicts, or missing credentials are NOT
            # caller identities. Self-asserted identity is refused here.
            raise ParticipationRefused("CALLER_CREDENTIAL_NOT_ADMITTED")
        binding = verifier(caller_credential)
        if binding is None:
            raise ParticipationRefused("CALLER_NOT_AUTHENTICATED")
        if not isinstance(binding, dict) or set(binding) != set(PRINCIPAL_KEYS):
            raise ParticipationRefused("CALLER_BINDING_REJECTED")
        checked = {}
        for field in ("agentRef", "tenantRef", "ownerRef"):
            value = binding[field]
            if not isinstance(value, str) or not IDENTIFIER_RE.match(value):
                raise ParticipationRefused("CALLER_BINDING_REJECTED")
            checked[field] = value
        return checked

    def _caller_matches(self, principal, scope):
        for field in ("agentRef", "tenantRef", "ownerRef"):
            if principal[field] != scope[field]:
                raise ParticipationRefused("CALLER_IDENTITY_MISMATCH")

    # -- credential lifecycle (P0D-A2) ----------------------------------------

    def _enforce_lifecycle(self, identity_query, decision):
        """Compare a verified decision against CURRENT lifecycle state.

        Fails closed: no source -> refusal; source unavailable -> refusal;
        malformed / tampered / identity-mismatched state -> refusal; any
        status but "registered" -> refusal; a decision whose generation
        or revocation epoch is not the CURRENT value -> refusal; and a
        source reporting a counter BELOW this gate's per-agent
        high-watermark (state rollback) -> refusal. The watermark is
        IN-MEMORY only and provides no durable protection across a
        process restart.
        """
        source = self.trusted_lifecycle_source
        if source is None or not callable(source):
            raise ParticipationRefused("LIFECYCLE_SOURCE_NOT_TRUSTED")
        if set(identity_query) != {"agentRef", "tenantRef", "ownerRef"}:
            raise AdmissionRefused("LIFECYCLE_QUERY_NOT_ADMITTED")
        raw = source(identity_query)
        if raw is None:
            raise ParticipationRefused("LIFECYCLE_STATE_UNAVAILABLE")
        if not isinstance(raw, dict) or set(raw) != LIFECYCLE_STATE_KEYS:
            raise ParticipationRefused("LIFECYCLE_STATE_SHAPE_INVALID")
        state = build_lifecycle_state(
            agent_ref=raw["agentRef"],
            owner_ref=raw["ownerRef"],
            tenant_ref=raw["tenantRef"],
            lifecycle_status=raw["lifecycleStatus"],
            current_credential_generation=raw["currentCredentialGeneration"],
            current_revocation_epoch=raw["currentRevocationEpoch"],
            observed_at_utc=raw["observedAtUtc"],
        )
        if state["kind"] != "toadaid-a2a-credential-lifecycle-state":
            raise ParticipationRefused("LIFECYCLE_STATE_KIND_INVALID")
        if canonical_json(state) != canonical_json(raw):
            raise ParticipationRefused("LIFECYCLE_STATE_TAMPERED")
        for field in ("agentRef", "tenantRef", "ownerRef"):
            if state[field] != identity_query[field]:
                raise ParticipationRefused("LIFECYCLE_STATE_IDENTITY_MISMATCH")

        watermark = self._lifecycle_high_water.get(identity_query["agentRef"])
        if watermark is None:
            watermark = {"generation": state["currentCredentialGeneration"],
                         "epoch": state["currentRevocationEpoch"]}
        else:
            # Rollback detection: only a source reporting a lower counter
            # than ever seen before trips this. Equal-or-higher refreshes
            # the watermark.
            if state["currentCredentialGeneration"] < watermark["generation"] \
                    or state["currentRevocationEpoch"] < watermark["epoch"]:
                raise ParticipationRefused("CREDENTIAL_STATE_ROLLBACK")
            watermark = {
                "generation": max(watermark["generation"],
                                  state["currentCredentialGeneration"]),
                "epoch": max(watermark["epoch"],
                             state["currentRevocationEpoch"]),
            }
        self._lifecycle_high_water[identity_query["agentRef"]] = watermark

        status = state["lifecycleStatus"]
        if status == "registered":
            pass
        elif status == "revoked":
            raise ParticipationRefused("LIFECYCLE_STATUS_REVOKED")
        elif status == "suspended":
            raise ParticipationRefused("LIFECYCLE_STATUS_SUSPENDED")
        elif status == "disabled":
            # Emergency disablement — no silent path back to admission.
            raise ParticipationRefused("LIFECYCLE_STATUS_DISABLED")
        else:
            raise ParticipationRefused("LIFECYCLE_STATUS_UNKNOWN")

        if decision["credentialGeneration"] \
                < state["currentCredentialGeneration"]:
            raise ParticipationRefused("CREDENTIAL_GENERATION_STALE")
        if decision["credentialGeneration"] \
                > state["currentCredentialGeneration"]:
            # A higher generation proves nothing: newly rotated
            # credentials are not automatically trusted merely because
            # their generation is higher.
            raise ParticipationRefused("CREDENTIAL_GENERATION_NOT_CURRENT")
        if decision["revocationEpoch"] < state["currentRevocationEpoch"]:
            # REVOCATION_OVERRIDES_PRIOR_APPROVAL: a decision from before
            # the current epoch never survives a later revocation.
            raise ParticipationRefused("REVOCATION_EPOCH_STALE")
        if decision["revocationEpoch"] > state["currentRevocationEpoch"]:
            raise ParticipationRefused("REVOCATION_EPOCH_NOT_CURRENT")

    # -- sender authorization ------------------------------------------------

    def authorize(self, request, caller_credential=None):
        """Verify one participation request; no delivery, no journal write.

        The request context must equal the caller's independently
        verified principal binding; the request's OWN claims never
        establish identity.
        """
        principal = self._verified_caller_principal(caller_credential)
        scope = self._validated_request_scope(request)
        self._caller_matches(principal, scope)
        query = {field: scope[field] for field in ("agentRef", "tenantRef", "ownerRef")}
        decision = self._verified_decision(query, require_scope=scope["participationScope"])
        # P0D-A2 — current credential-lifecycle state is mandatory even
        # for a verified, non-expired, correctly-scoped decision.
        self._enforce_lifecycle(query, decision)
        return self._admission_receipt(scope, decision)

    # -- two-agent routing ---------------------------------------------------

    def route(self, sender_request, recipient_context, caller_credential=None):
        """Registered sender -> gate -> registered recipient, journal-first.

        ``recipient_context`` is the recipient's own exact identity
        context {"agentRef", "tenantRef", "ownerRef"}, pinned before any
        adapter call. The caller is authenticated FIRST; the sender is
        verified for 'a2a-message-send' in EVERY route regardless of the
        request's declared scope (R1-1 — a receive-only sender can never
        initiate delivery), and any route request not declaring
        'a2a-message-send' is a scope mismatch. The recipient is
        independently verified for 'a2a-message-receive' under its own
        binding. Tenant isolation is explicit policy: cross-tenant
        delivery is refused (REACHABLE refusal, not dead code). The
        journal entry is committed before the delivery result and binds
        the verified recipient identity (R1-2).
        """
        principal = self._verified_caller_principal(caller_credential)
        scope = self._validated_request_scope(sender_request)
        if scope["participationScope"] != "a2a-message-send":
            raise ParticipationRefused("SENDER_SCOPE_MISMATCH")
        self._caller_matches(principal, scope)
        if not isinstance(recipient_context, dict) \
                or set(recipient_context) != set(RECIPIENT_KEYS):
            raise AdmissionRefused("RECIPIENT_KEYS_NOT_ADMITTED")
        _pin_identifier(recipient_context["agentRef"], "RECIPIENT_REF_NOT_ADMITTED")
        _pin_identifier(recipient_context["tenantRef"],
                        "RECIPIENT_TENANT_REF_NOT_ADMITTED")
        _pin_identifier(recipient_context["ownerRef"],
                        "RECIPIENT_OWNER_REF_NOT_ADMITTED")
        if recipient_context["agentRef"] == scope["agentRef"] \
                and recipient_context["tenantRef"] == scope["tenantRef"] \
                and recipient_context["ownerRef"] == scope["ownerRef"]:
            raise AdmissionRefused("SELF_DELIVERY_NOT_ADMITTED")
        sender_query = {field: scope[field]
                        for field in ("agentRef", "tenantRef", "ownerRef")}
        sender_decision = self._verified_decision(
            sender_query, require_scope="a2a-message-send")
        # P0D-A2 — BOTH sides of a delivery pass the CURRENT lifecycle
        # check before any journal write, so an identical replay cannot
        # bypass a revocation that occurred since its original admission,
        # and lifecycle refusals append NO journal entry.
        self._enforce_lifecycle(sender_query, sender_decision)

        recipient_decision = self._verified_decision(
            dict(recipient_context), require_scope="a2a-message-receive")
        self._enforce_lifecycle(dict(recipient_context), recipient_decision)
        if recipient_decision["tenantRef"] != sender_decision["tenantRef"]:
            raise ParticipationRefused("CROSS_TENANT_DELIVERY_REFUSED")

        delivery_digest = _delivery_digest(
            _request_digest(sender_request), recipient_decision)
        journal_result = self.journal.check_and_record(
            scope["messageId"], delivery_digest)
        return self._delivery_receipt(scope, sender_decision, recipient_decision,
                                      journal_result)

    # -- internals ------------------------------------------------------------

    def _now_utc(self):
        if self.now is None or not callable(self.now):
            raise ParticipationRefused("CLOCK_SOURCE_REQUIRED")
        stamp = self.now()
        if not isinstance(stamp, datetime.datetime):
            raise ParticipationRefused("CLOCK_SOURCE_REQUIRED")
        if stamp.tzinfo is not None:
            # R1-3: convert to true UTC, never just strip the offset.
            stamp = stamp.astimezone(datetime.timezone.utc).replace(tzinfo=None)
        return stamp

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
        if not isinstance(request["participationScope"], str) \
                or request["participationScope"] not in PARTICIPATION_SCOPES:
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
        if not isinstance(message["messageType"], str) \
                or message["messageType"] not in MESSAGE_TYPES:
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