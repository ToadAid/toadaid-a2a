"""CUT-AO-P0A-20261103 — read-only, owner-scoped Observatory feed.

Bounded feed recorder with a TRUSTED INGESTION seam (producer provenance is
authenticated, never taken from caller-provided component strings) and a
strictly read-only owner-dashboard reader serving only detached snapshots.

Privacy model (Director ruling AO-P0A):
  * ``agent.toadaid.org/dashboard/`` is a PRIVATE owner dashboard: owners may
    view ONLY their own registered agents, with ownership and tenant
    isolation enforced on every request.
  * Reads FAIL CLOSED when authorization is missing or unavailable: the
    default trust adapter refuses everything, and only an injected trusted
    adapter can authorize a reader. This is a seam for a future real
    authentication system — none is invented or bypassed here.
  * WRITES FAIL CLOSED too: a producer must present an opaque credential that
    an injected trusted authenticator maps to a binding (allowed evidence
    classes, component, tenant/owner scope, bound agents, human-receipt
    relay). The default recorder has NO authenticator and refuses every
    write. Component strings like "agent-admission-portal" typed by a caller
    are not credentials and never authenticate anything.
  * Recorded events are stored as detached rebuild snapshots and every read
    returns deep copies: no retained reference — neither the caller's input
    nor a served feed item — can rewrite audited history or upgrade evidence.
  * There is NO public projection in this cut. The public agent directory is
    a separate future cut; requesting one here is refused.
  * Unknown or unavailable agent status can never surface as verified,
    online or idle: non-infrastructure-confirmed status is projected as
    "unknown", with the agent's claim preserved only as
    "claimedRegistrationStatus".
"""

import copy
import re

from .model import (
    EVIDENCE_CLASSES,
    IDENTIFIER_RE,
    ObservatoryRefusal,
    TRUSTED_SOURCES,
    build_event,
    canonical_json,
)

__all__ = [
    "DASHBOARD_KIND",
    "DASHBOARD_SCHEMA_VERSION",
    "DASHBOARD_STATUS",
    "ALLOWED_PAGE_LIMITS",
    "MAX_EVENTS",
    "PUBLIC_DIRECTORY_STATUS",
    "FeedRecorder",
    "OwnerScopeTrustRefused",
    "ProducerToken",
    "ProducerTrustRefused",
    "synthetic_offline_authenticator",
    "owner_dashboard_feed",
    "assert_public_directory_is_separate_cut",
]

DASHBOARD_KIND = "toadaid-observatory-owner-dashboard-feed"
DASHBOARD_SCHEMA_VERSION = "0.1.0"
DASHBOARD_STATUS = "SYNTHETIC_LOCAL_FOUNDATION_READ_ONLY"
PUBLIC_DIRECTORY_STATUS = "SEPARATE_FUTURE_CUT_EXPLICIT_OWNER_PUBLICATION_CONSENT_REQUIRED"

ALLOWED_PAGE_LIMITS = (10, 25, 50)
MAX_EVENTS = 5000

_CURSOR_RE = re.compile(r"^cur:[0-9]{1,9}$")
_SCOPE_KEYS = frozenset({"tenantRef", "ownerRef", "authorizationId"})
_PAGINATION_KEYS = frozenset({"limit", "pageToken"})
_FILTER_KEYS = frozenset({"agentRef"})

# Presentation truthfulness: agent-reported records are always visible AS
# CLAIMED (unverified by default), never re-labelled as observed.
_CLAIMED_PRESENCE = {"agent_reported": True, "human_authorized": False,
                     "infrastructure_observed": False, "unverified": False}


class OwnerScopeTrustRefused(PermissionError):
    """A read with no trusted authorization adapter authorizing it."""


class ProducerTrustRefused(PermissionError):
    """A record attempt without trusted producer authentication."""


class ProducerToken:
    """Opaque ingestion credential (identity equality, not a typed string).

    Provenance binds to the token INSTANCE issued by a trusted provisioning
    step, mapped to a binding by an injected authenticator. A caller who can
    type "agent-admission-portal" can forge nothing.
    """

    __slots__ = ("_label",)

    def __init__(self, label="producer"):
        self._label = str(label)

    def __repr__(self):
        return f"ProducerToken({self._label!r})"


def synthetic_offline_authenticator(bindings):
    """SYNTHETIC OFFLINE ONLY — NOT A REAL AUTHENTICATION SYSTEM.

    Maps issued ProducerToken instances to producer binding dicts for local
    tests and synthetic examples. The fail-closed production stance stays
    intact: a real deployment injects a real authenticator instead.
    """
    if not isinstance(bindings, dict) or not bindings:
        raise ObservatoryRefusal("PRODUCER_BINDINGS_SHAPE_INVALID")
    try:
        frozen = {token: binding for token, binding in bindings.items()}
    except TypeError:
        raise ObservatoryRefusal("PRODUCER_BINDINGS_SHAPE_INVALID")
    return lambda token: frozen.get(token)


_BINDING_KEYS = frozenset({
    "producerComponent", "evidenceClasses", "humanReceipts",
    "tenantRefs", "ownerRefs", "agentRefs",
})

_REFUSABLE_SEQUENCES = (frozenset, set, list, tuple)


def _validate_binding(binding):
    """Shape- and domain-check a producer binding; return a frozen copy.

    An authenticated producer is bound to its component, allowed evidence
    classes, tenant/owner scope, the agents whose agent-reported claims it
    may relay, and whether it may relay off-chat human decisions.
    """
    if not isinstance(binding, dict) or set(binding) != _BINDING_KEYS:
        raise ObservatoryRefusal("PRODUCER_BINDING_NOT_ADMITTED")
    component = binding["producerComponent"]
    if not isinstance(component, str) or component not in TRUSTED_SOURCES:
        raise ObservatoryRefusal("PRODUCER_BINDING_NOT_ADMITTED")
    classes = binding["evidenceClasses"]
    if not isinstance(classes, _REFUSABLE_SEQUENCES) or not classes \
            or not set(classes) <= EVIDENCE_CLASSES:
        raise ObservatoryRefusal("PRODUCER_BINDING_NOT_ADMITTED")
    if not isinstance(binding["humanReceipts"], bool):
        raise ObservatoryRefusal("PRODUCER_BINDING_NOT_ADMITTED")

    def _pinned_refs(refs):
        if not isinstance(refs, _REFUSABLE_SEQUENCES):
            raise ObservatoryRefusal("PRODUCER_BINDING_NOT_ADMITTED")
        for ref in refs:
            if not isinstance(ref, str) or not IDENTIFIER_RE.match(ref):
                raise ObservatoryRefusal("PRODUCER_BINDING_NOT_ADMITTED")
        return frozenset(refs)

    agents = binding["agentRefs"]
    return {
        "producerComponent": component,
        "evidenceClasses": frozenset(classes),
        "humanReceipts": binding["humanReceipts"],
        "tenantRefs": _pinned_refs(binding["tenantRefs"]),
        "ownerRefs": _pinned_refs(binding["ownerRefs"]),
        "agentRefs": None if agents is None else _pinned_refs(agents),
    }


def assert_public_directory_is_separate_cut():
    """Refuse any public/procedural directory access in THIS cut."""
    raise ObservatoryRefusal("PUBLIC_DIRECTORY_SEPARATE_FUTURE_CUT")


class FeedRecorder:
    """Append-only, bounded, authenticated producer journal.

    Ingestion is fail-closed: the constructor's trusted authenticator is
    None by default, so an unconfigured recorder accepts NOTHING. Accepted
    records are stored as detached rebuild snapshots and every read returns
    deep copies, so retained references cannot rewrite history.
    """

    def __init__(self, capacity=MAX_EVENTS, trusted_authorization_adapter=None,
                 trusted_producer_authenticator=None):
        if capacity < 1 or capacity > MAX_EVENTS:
            raise ObservatoryRefusal("FEED_CAPACITY_OUT_OF_BOUNDS")
        self.capacity = capacity
        # Read-side fail-closed seam: a future real authentication system is
        # injected here via a trusted adapter callable. The default (None)
        # authorizes NOTHING — no read without an explicitly trusted adapter.
        self.trusted_authorization_adapter = trusted_authorization_adapter
        # Write-side fail-closed seam: a future real producer authenticator
        # is injected here. The default (None) accepts NOTHING — no write
        # without an explicitly trusted authenticator.
        self.trusted_producer_authenticator = trusted_producer_authenticator
        # Detached snapshots only: the caller's dict is never retained.
        self._events = []
        self._canonical_by_event_id = {}

    def record(self, validated_event, producer_credential):
        """Authenticate a producer, re-validate, then store a detached copy.

        Provenance is verified against the authenticator's binding, not the
        caller's word: the binding fixes the producer's component, the
        evidence classes it may attest, its tenant/owner scope, the agents
        whose agent-reported claims it may relay, and whether it may relay
        off-chat human decisions. Component strings typed by callers are not
        credentials.
        """
        if self.trusted_producer_authenticator is None:
            raise ProducerTrustRefused("PRODUCER_AUTHENTICATION_REQUIRED")
        try:
            raw_binding = self.trusted_producer_authenticator(producer_credential)
        except (TypeError, LookupError):
            raw_binding = None
        if not isinstance(raw_binding, dict):
            raise ProducerTrustRefused("PRODUCER_AUTHENTICATION_REFUSED")
        binding = _validate_binding(raw_binding)

        rebuilt = build_event(**_record_to_builder(validated_event))
        if canonical_json(validated_event) != canonical_json(rebuilt):
            raise ObservatoryRefusal("EVENT_RECORD_TAMPERED")

        evidence = rebuilt["evidenceClass"]
        if evidence not in binding["evidenceClasses"]:
            raise ProducerTrustRefused("PRODUCER_EVIDENCE_NOT_BOUND")
        if evidence == "infrastructure_observed" \
                and rebuilt["sourceIdentity"] != binding["producerComponent"]:
            raise ProducerTrustRefused("PRODUCER_SOURCE_MISMATCH")
        if evidence == "human_authorized" and not binding["humanReceipts"]:
            raise ProducerTrustRefused("PRODUCER_HUMAN_CHANNEL_NOT_BOUND")
        if evidence == "agent_reported":
            agents = binding["agentRefs"]
            agent = rebuilt["payload"].get("agentRef")
            if agents is None or agent not in agents:
                raise ProducerTrustRefused("PRODUCER_AGENT_NOT_BOUND")
        if rebuilt["tenantRef"] not in binding["tenantRefs"]:
            raise ProducerTrustRefused("PRODUCER_TENANT_NOT_BOUND")
        if rebuilt["ownerRef"] not in binding["ownerRefs"]:
            raise ProducerTrustRefused("PRODUCER_OWNER_NOT_BOUND")

        key = rebuilt["eventId"]
        digest = canonical_json(rebuilt)
        seen = self._canonical_by_event_id.get(key)
        if seen is not None:
            if seen == digest:
                return {"recorded": "idempotent", "eventId": key}
            raise ObservatoryRefusal("DUPLICATE_EVENT_ID_CONFLICT")
        if len(self._events) >= self.capacity:
            raise ObservatoryRefusal("FEED_CAPACITY_EXCEEDED")
        # `rebuilt` shares no mutable container with the caller's input.
        self._events.append(rebuilt)
        self._canonical_by_event_id[key] = digest
        return {"recorded": True, "eventId": key}

    def events(self):
        """Detached deep-copied journal view; mutation here is local only."""
        return copy.deepcopy(self._events)


def _record_to_builder(validated):
    return {
        "event_kind": validated["eventKind"],
        "event_id": validated["eventId"],
        "correlation_id": validated["correlationId"],
        "occurred_at_utc": validated["occurredAtUtc"],
        "evidence_class": validated["evidenceClass"],
        "source_identity": validated["sourceIdentity"],
        "tenant_ref": validated["tenantRef"],
        "owner_ref": validated["ownerRef"],
        "privacy_classification": validated["privacyClassification"],
        "visibility_class": validated["visibilityClass"],
        "payload": validated["payload"],
    }


def owner_dashboard_feed(recorder, owner_scope, filters=None, pagination=None):
    """Return the read-only feed for one authorized owner scope.

    Fails closed unless ``trusted_authorization_adapter`` (constructor or
    module-level default: refuse everything) authorizes the scope's owner.
    No public visibility floor is servable here.
    """
    trusted_authorization_adapter = getattr(recorder, "trusted_authorization_adapter", None)
    if trusted_authorization_adapter is None or not owner_scope or \
            set(owner_scope) != _SCOPE_KEYS:
        raise OwnerScopeTrustRefused("OWNER_SCOPE_AUTHORIZATION_REQUIRED")
    if not IDENTIFIER_RE.match(owner_scope["tenantRef"]) or \
            not IDENTIFIER_RE.match(owner_scope["ownerRef"]) or \
            not IDENTIFIER_RE.match(owner_scope["authorizationId"]):
        raise OwnerScopeTrustRefused("OWNER_SCOPE_AUTHORIZATION_REQUIRED")
    if not trusted_authorization_adapter(owner_scope):
        raise OwnerScopeTrustRefused("OWNER_SCOPE_AUTHORIZATION_REFUSED")

    matched = []
    for record in recorder.events():
        if record["tenantRef"] != owner_scope["tenantRef"] or \
                record["ownerRef"] != owner_scope["ownerRef"]:
            continue
        matched.append(record)
    if filters:
        if set(filters) != _FILTER_KEYS:
            raise ObservatoryRefusal("FILTER_KEYS_NOT_ADMITTED")
        agent_ref = filters["agentRef"]
        if agent_ref is not None:
            if not IDENTIFIER_RE.match(agent_ref):
                raise ObservatoryRefusal("FILTER_AGENT_REF_NOT_ADMITTED")
            matched = [ r for r in matched if r["payload"].get("agentRef") == agent_ref ]

    if pagination is not None and (
            not isinstance(pagination, dict) or not set(pagination) <= _PAGINATION_KEYS):
        raise ObservatoryRefusal("PAGINATION_KEYS_NOT_ADMITTED")
    limit = pagination.get("limit", 25) if pagination else 25
    if limit not in ALLOWED_PAGE_LIMITS:
        raise ObservatoryRefusal("PAGE_LIMIT_NOT_ADMITTED")
    page_token = None if not pagination else pagination.get("pageToken")
    offset = 0
    if page_token is not None:
        if not _CURSOR_RE.match(page_token):
            raise ObservatoryRefusal("PAGE_TOKEN_NOT_ADMITTED")
        offset = int(page_token.split(":", 1)[1])
    if offset > len(matched):
        raise ObservatoryRefusal("PAGE_OFFSET_PAST_END")
    page = matched[offset:offset + limit]
    next_offset = offset + limit
    result = {
        "kind": DASHBOARD_KIND,
        "schemaVersion": DASHBOARD_SCHEMA_VERSION,
        "status": DASHBOARD_STATUS,
        "tenantRef": owner_scope["tenantRef"],
        "ownerRef": owner_scope["ownerRef"],
        "items": [ _project(record) for record in page ],
        "stats": {"totalForOwner": len(matched)},
        "authorityFlags": {"executionAuthorized": False,
                           "publicationAuthorized": False,
                           "deploymentAuthorized": False,
                           "agentRegistrationActive": False,
                           "publicDirectoryExposed": False},
    }
    if next_offset < len(matched):
        result["nextPageToken"] = f"cur:{next_offset}"
    return result


def _project(record):
    # Detached projection: the served item shares no mutable container with
    # the stored record, so a client mutating a feed item cannot rewrite the
    # audited journal.
    payload = copy.deepcopy(record["payload"])
    extra = {}
    if record["eventKind"] == "agent_identity_reference":
        if record["evidenceClass"] != "infrastructure_observed":
            claimed = payload.get("registrationStatus")
            if claimed not in ("unknown",):
                extra["claimedRegistrationStatus"] = claimed
            payload["registrationStatus"] = "unknown"
    item = {
        "eventKind": record["eventKind"],
        "eventId": record["eventId"],
        "correlationId": record["correlationId"],
        "occurredAtUtc": record["occurredAtUtc"],
        "evidenceClass": record["evidenceClass"],
        "sourceIdentity": record["sourceIdentity"],
        "claimed": _CLAIMED_PRESENCE[record["evidenceClass"]],
        "payload": payload,
    }
    item.update(extra)
    return item