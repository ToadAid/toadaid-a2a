"""CUT-AO-P0A-20261103 — read-only, owner-scoped Observatory feed.

Bounded feed recorder (trusted-component write seam, private journal style)
and a strictly read-only owner-dashboard reader.

Privacy model (Director ruling AO-P0A):
  * ``agent.toadaid.org/dashboard/`` is a PRIVATE owner dashboard: owners may
    view ONLY their own registered agents, with ownership and tenant
    isolation enforced on every request.
  * Reads FAIL CLOSED when authorization is missing or unavailable: the
    default trust adapter refuses everything, and only an injected trusted
    adapter can authorize a reader. This is a seam for a future real
    authentication system — none is invented or bypassed here.
  * There is NO public projection in this cut. The public agent directory is
    a separate future cut; requesting one here is refused.
  * Unknown or unavailable agent status can never surface as verified,
    online or idle: non-infrastructure-confirmed status is projected as
    "unknown", with the agent's claim preserved only as
    "claimedRegistrationStatus".
"""

import re

from .model import (
    IDENTIFIER_RE,
    ObservatoryRefusal,
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


def assert_public_directory_is_separate_cut():
    """Refuse any public/procedural directory access in THIS cut."""
    raise ObservatoryRefusal("PUBLIC_DIRECTORY_SEPARATE_FUTURE_CUT")


class FeedRecorder:
    """Append-only, bounded, trusted-component feed journal.

    Journal-before-delivery style: idempotent records return their prior
    entry; conflicting duplicates and out-of-bounds state fail closed. No
    client capability can write here.
    """

    def __init__(self, capacity=MAX_EVENTS, trusted_authorization_adapter=None):
        if capacity < 1 or capacity > MAX_EVENTS:
            raise ObservatoryRefusal("FEED_CAPACITY_OUT_OF_BOUNDS")
        self.capacity = capacity
        # Fail-closed seam: a future real authentication system is injected
        # here via a trusted adapter callable. The default (None) authorizes
        # NOTHING — no read without an explicitly trusted adapter.
        self.trusted_authorization_adapter = trusted_authorization_adapter
        self._events = []
        self._canonical_by_event_id = {}

    def record(self, validated_event, component):
        if component not in {"lifecycle-journal", "agent-admission-portal"}:
            raise ObservatoryRefusal("RECORDER_COMPONENT_NOT_TRUSTED")
        if canonical_json(validated_event) != \
                canonical_json(build_event(**_record_to_builder(validated_event))):
            raise ObservatoryRefusal("EVENT_RECORD_TAMPERED")
        key = validated_event["eventId"]
        seen = self._canonical_by_event_id.get(key)
        digest = canonical_json(validated_event)
        if seen is not None:
            if seen == digest:
                return {"recorded": "idempotent", "eventId": key}
            raise ObservatoryRefusal("DUPLICATE_EVENT_ID_CONFLICT")
        if len(self._events) >= self.capacity:
            raise ObservatoryRefusal("FEED_CAPACITY_EXCEEDED")
        self._events.append(validated_event)
        self._canonical_by_event_id[key] = digest
        return {"recorded": True, "eventId": key}

    def events(self):
        return list(self._events)


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
    payload = dict(record["payload"])
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