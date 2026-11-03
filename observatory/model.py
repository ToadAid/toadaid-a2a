"""CUT-AO-P0A-20261103 — bounded observability event model.

Read-only data foundation for the Agent Observatory
(``agent.toadaid.org/dashboard/``). Every event record carries its own
evidence class, source identity, correlation id, UTC timestamp, tenant ref and
privacy classification, and a fixed, all-false authority flag block.

Boundaries (none of which this module reopens):
  * NO live agent admission, execution, shell, wallet or MCP permission.
  * NO secrets, credentials, raw private conversations or hidden reasoning in
    any record — the builder validates bounds and refuses to mint anything
    wider than its whitelist.
  * Agent-reported events CANNOT silently become trusted evidence: the
    evidence class is a validated, explicit parameter, never inferred, and
    never upgraded after construction.
  * Unknown or unavailable agent status is projected only as "unknown"; it is
    never rendered online, idle or verified anywhere downstream.
"""

import json
import re

__all__ = [
    "EVENT_KINDS",
    "EVIDENCE_CLASSES",
    "VISIBILITY_CLASSES",
    "PRIVACY_CLASSIFICATIONS",
    "REGISTRATION_STATUSES",
    "LIFECYCLE_KINDS",
    "TRUSTED_SOURCES",
    "IDENTIFIER_RE",
    "HUMAN_DECISION_CHANNEL",
    "OBSERVED_ACTIVITY_KINDS",
    "OBSERVED_REQUEST_STATES",
    "SUBJECT_KINDS",
    "OBJECTION_CODES",
    "AUTHORITY_FLAGS",
    "COMMON_KEYS",
    "KIND_KEYS",
    "KIND_EVIDENCE_ALLOW",
    "MAX_STRING_CHARS",
    "MAX_LIST_ITEMS",
    "MAX_INT_VALUE",
    "ObservatoryRefusal",
    "build_event",
    "canonical_json",
]

EVENT_KINDS = frozenset({
    "agent_identity_reference",
    "agent_activity_event",
    "a2a_conversation_metadata",
    "mcp_tool_request_metadata",
    "human_authorization_receipt",
    "human_refusal_receipt",
    "lifecycle_security_event",
})

# Distinguishes what kind of evidence a record carries, per the mission:
# agent-reported claims are never silently trusted.
EVIDENCE_CLASSES = frozenset({
    "agent_reported",
    "infrastructure_observed",
    "human_authorized",
    "unverified",
})

VISIBILITY_CLASSES = frozenset({"public", "community", "operator"})

PRIVACY_CLASSIFICATIONS = frozenset({"private", "internal", "community", "public"})

# Registration status projections. "unknown" is the ONLY honest projection
# for unknown or unavailable status — never "online", never "idle".
REGISTRATION_STATUSES = frozenset({
    "registered", "revoked", "suspended", "unregistered", "unknown",
})

LIFECYCLE_KINDS = frozenset({
    "rotation", "revocation", "emergency_disable", "recovery",
})

# Infrastructure-observed records may only come from trusted components.
TRUSTED_SOURCES = frozenset({
    "lifecycle-journal", "agent-admission-portal", "observatory-recorder",
})

# Human decisions are always recorded by an independent off-chat process.
HUMAN_DECISION_CHANNEL = "independent-off-chat-human-process"

OBSERVED_ACTIVITY_KINDS = frozenset({
    "conversation_message", "task_update", "tool_request_reported",
    "status_declaration",
})

OBSERVED_REQUEST_STATES = frozenset({"requested", "authorized", "refused"})

# Preserved, never cleared (same vocabulary as the lore human handoff).
OBJECTION_CODES = frozenset({
    "SOURCE_IDENTITY", "RIGHTS_CHAIN", "PERMISSION_SCOPE", "ATTRIBUTION",
    "PRIVACY", "WITHDRAWAL", "CONFLICT_OF_INTEREST", "MEDIA_RIGHTS", "OTHER",
})

# Fixed flag block on every record: all false by construction.
AUTHORITY_FLAGS = {
    "executionAuthorized": False,
    "publicationAuthorized": False,
    "deploymentAuthorized": False,
    "agentRegistrationActive": False,
}

COMMON_KEYS = frozenset({
    "eventKind", "eventId", "correlationId", "occurredAtUtc",
    "evidenceClass", "sourceIdentity", "tenantRef", "ownerRef",
    "privacyClassification", "visibilityClass", "authorityFlags", "payload",
})

# Per-kind payload whitelist. Payload key sets are exact: nothing extra can be
# smuggled into a projection.
KIND_KEYS = {
    "agent_identity_reference": frozenset({
        "agentRef", "registrationStatus",
    }),
    "agent_activity_event": frozenset({
        "agentRef", "activityKind",
    }),
    "a2a_conversation_metadata": frozenset({
        "conversationId", "turnCount", "participants",
    }),
    "mcp_tool_request_metadata": frozenset({
        "toolName", "requestState", "authorizationGrantRef",
    }),
    "human_authorization_receipt": frozenset({
        "decisionChannel", "decisionId", "subjectKind", "subjectRef",
    }),
    "human_refusal_receipt": frozenset({
        "decisionChannel", "decisionId", "subjectKind", "subjectRef",
        "objectionCode",
    }),
    "lifecycle_security_event": frozenset({
        "agentRef", "lifecycleKind", "generation", "revocationEpoch",
    }),
}

KIND_EVIDENCE_ALLOW = {
    "agent_identity_reference": frozenset({
        "infrastructure_observed", "agent_reported", "unverified",
    }),
    "agent_activity_event": frozenset({
        "infrastructure_observed", "agent_reported", "unverified",
    }),
    "a2a_conversation_metadata": frozenset({
        "infrastructure_observed", "agent_reported", "unverified",
    }),
    "mcp_tool_request_metadata": frozenset({
        "infrastructure_observed", "unverified",
    }),
    "human_authorization_receipt": frozenset({"human_authorized"}),
    "human_refusal_receipt": frozenset({"human_authorized"}),
    "lifecycle_security_event": frozenset({
        "infrastructure_observed", "unverified",
    }),
}

MAX_STRING_CHARS = 512
MAX_LIST_ITEMS = 8
MAX_INT_VALUE = 10_000
MAX_PAYLOAD_KEYS = 16

SUBJECT_KINDS = frozenset({
    "operation", "agent_task", "agent_enrollment",
    "agent_enrollment_publication", "lifecycle_decision",
})

_TOOL_NAME_RE = re.compile(r"^[a-z][a-z0-9._-]{1,63}$")

IDENTIFIER_RE = re.compile(r"^[a-z][a-z0-9-]{2,63}$")
_ISO_UTC_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$"
)


class ObservatoryRefusal(ValueError):
    """Deny-first refusal of an out-of-bounds observability record."""


def _check(value, name):
    if value is None:
        return value
    if isinstance(value, str):
        if not value or len(value) > MAX_STRING_CHARS:
            raise ObservatoryRefusal("OBSERVABILITY_STRING_OUT_OF_BOUNDS")
        return value
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        if value < 0 or value > MAX_INT_VALUE:
            raise ObservatoryRefusal("OBSERVABILITY_INT_OUT_OF_BOUNDS")
        return value
    if isinstance(value, list):
        if len(value) > MAX_LIST_ITEMS:
            raise ObservatoryRefusal("OBSERVABILITY_LIST_OUT_OF_BOUNDS")
        return [ _check(item, name) for item in value ]
    if isinstance(value, dict):
        if len(value) > MAX_PAYLOAD_KEYS:
            raise ObservatoryRefusal("OBSERVABILITY_PAYLOAD_OUT_OF_BOUNDS")
        return { key: _check(item, name) for key, item in value.items() }
    raise ObservatoryRefusal("OBSERVABILITY_TYPE_FORBIDDEN")


def build_event(
    event_kind,
    event_id,
    correlation_id,
    occurred_at_utc,
    evidence_class,
    source_identity,
    tenant_ref,
    owner_ref,
    privacy_classification,
    visibility_class,
    payload,
):
    """Build one validated, fixed-shape observability event record.

    The signature is an exact whitelist: there is no **kwargs and no passthrough,
    so extraneous claimed authority cannot reach a durable record.
    """
    if event_kind not in EVENT_KINDS:
        raise ObservatoryRefusal("EVENT_KIND_NOT_ADMITTED")
    if evidence_class not in EVIDENCE_CLASSES:
        raise ObservatoryRefusal("EVIDENCE_CLASS_NOT_ADMITTED")
    if evidence_class not in KIND_EVIDENCE_ALLOW[event_kind]:
        raise ObservatoryRefusal("EVIDENCE_CLASS_CONFLICTS_WITH_EVENT_KIND")
    if privacy_classification not in PRIVACY_CLASSIFICATIONS:
        raise ObservatoryRefusal("PRIVACY_CLASSIFICATION_NOT_ADMITTED")
    if visibility_class not in VISIBILITY_CLASSES:
        raise ObservatoryRefusal("VISIBILITY_CLASS_NOT_ADMITTED")
    if not tenant_ref or not isinstance(tenant_ref, str):
        raise ObservatoryRefusal("TENANT_REF_REQUIRED_FROM_TRUSTED_SERVER")
    if not owner_ref or not isinstance(owner_ref, str):
        raise ObservatoryRefusal("OWNER_REF_REQUIRED_FROM_TRUSTED_SERVER")
    _check(tenant_ref, "tenantRef")
    if not IDENTIFIER_RE.match(event_id or ""):
        raise ObservatoryRefusal("EVENT_ID_NOT_ADMITTED")
    if not IDENTIFIER_RE.match(correlation_id or ""):
        raise ObservatoryRefusal("CORRELATION_ID_NOT_ADMITTED")
    if not IDENTIFIER_RE.match(owner_ref):
        raise ObservatoryRefusal("OWNER_REF_NOT_ADMITTED")
    if not _ISO_UTC_RE.match(occurred_at_utc or ""):
        raise ObservatoryRefusal("TIMESTAMP_NOT_ISO_UTC")
    if not isinstance(payload, dict) or not payload:
        raise ObservatoryRefusal("PAYLOAD_SHAPE_INVALID")
    if set(payload) != KIND_KEYS[event_kind]:
        raise ObservatoryRefusal("PAYLOAD_KEYS_NOT_ADMITTED")

    # Evidence-source separation: a record's source identity must honestly
    # match its evidence class.
    if evidence_class == "infrastructure_observed" \
            and source_identity not in TRUSTED_SOURCES:
        raise ObservatoryRefusal("SOURCE_IDENTITY_NOT_A_TRUSTED_COMPONENT")
    if evidence_class == "human_authorized" \
            and source_identity != HUMAN_DECISION_CHANNEL:
        raise ObservatoryRefusal("HUMAN_DECISION_CHANNEL_NOT_OFF_CHAT")
    if evidence_class == "agent_reported" \
            and source_identity != payload.get("agentRef"):
        raise ObservatoryRefusal("AGENT_REPORTED_SOURCE_MUST_BE_THE_AGENT")

    checked_payload = _check(payload, "payload")
    for key in ("generation", "revocationEpoch"):
        if event_kind == "lifecycle_security_event" and key not in checked_payload:
            raise ObservatoryRefusal("LIFECYCLE_COUNTERS_REQUIRED")

    # Value-domain pinning for bounded payloads.
    if event_kind == "agent_identity_reference":
        if checked_payload["registrationStatus"] not in REGISTRATION_STATUSES:
            raise ObservatoryRefusal("REGISTRATION_STATUS_NOT_ADMITTED")
    if event_kind == "agent_activity_event":
        if checked_payload["activityKind"] not in OBSERVED_ACTIVITY_KINDS:
            raise ObservatoryRefusal("ACTIVITY_KIND_NOT_ADMITTED")
    if event_kind == "mcp_tool_request_metadata":
        if checked_payload["requestState"] not in OBSERVED_REQUEST_STATES:
            raise ObservatoryRefusal("REQUEST_STATE_NOT_ADMITTED")
        if not _TOOL_NAME_RE.match(checked_payload["toolName"]):
            raise ObservatoryRefusal("TOOL_NAME_NOT_ADMITTED")
        grant = checked_payload["authorizationGrantRef"]
        if grant is not None and not IDENTIFIER_RE.match(grant):
            raise ObservatoryRefusal("GRANT_REF_NOT_ADMITTED")
    if event_kind in ("human_authorization_receipt", "human_refusal_receipt"):
        if checked_payload["subjectKind"] not in SUBJECT_KINDS:
            raise ObservatoryRefusal("SUBJECT_KIND_NOT_ADMITTED")
        if checked_payload["decisionChannel"] != HUMAN_DECISION_CHANNEL:
            raise ObservatoryRefusal("HUMAN_DECISION_CHANNEL_NOT_OFF_CHAT")
        if event_kind == "human_refusal_receipt" \
                and checked_payload["objectionCode"] not in OBJECTION_CODES:
            raise ObservatoryRefusal("OBJECTION_CODE_NOT_ADMITTED")

    privacy_floor = {"public": {"public"},
                     "community": {"community", "public"},
                     "operator": PRIVACY_CLASSIFICATIONS}[visibility_class]
    if privacy_classification not in privacy_floor:
        raise ObservatoryRefusal(
            "PRIVACY_EXCEEDS_REQUESTED_VISIBILITY_FLOOR")

    return {
        "eventKind": event_kind,
        "eventId": event_id,
        "correlationId": correlation_id,
        "occurredAtUtc": occurred_at_utc,
        "evidenceClass": evidence_class,
        "sourceIdentity": source_identity,
        "tenantRef": tenant_ref,
        "ownerRef": owner_ref,
        "privacyClassification": privacy_classification,
        "visibilityClass": visibility_class,
        "authorityFlags": dict(AUTHORITY_FLAGS),
        "payload": checked_payload,
    }


def canonical_json(record):
    """Deterministic JSON digestion input (repo convention)."""
    return json.dumps(record, sort_keys=True, ensure_ascii=True,
                      separators=(",", ":"), allow_nan=False)