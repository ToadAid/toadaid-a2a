"""CUT-A2A-P0D-A2-20261103 — trusted credential-lifecycle state boundary.

A registration decision that carries `credentialGeneration` and
`revocationEpoch` (P0D-A1) does NOT, by itself, prove those values are
CURRENT. An adapter-issued decision is a point-in-time record: after a
rotation, revocation, suspension, or emergency disablement, a stale
decision must never authorize communication again. This module defines
the fourth, independently verified fail-closed seam: an injected trusted
lifecycle SOURCE that reports an agent's CURRENT lifecycle state.

Constitutional principles (enforced, not decorative):
  * No state source means refusal — a gate without a trusted lifecycle
    source cannot admit anyone.
  * No agent-supplied claim can establish its own current credential
    state — lifecycle state is fetched from the injected source under
    the same exact three-field identity context as registration, never
    read from a request, a card, a body, or the decision itself.
  * REVOCATION_OVERRIDES_PRIOR_APPROVAL — current revocation/suspension/
    disablement state refuses delivery even when older adapter decisions
    were themselves valid when issued.
  * A2A_CHAT_HAS_ZERO_EXECUTION_AUTHORITY — lifecycle state authorizes
    conversation metadata only; it never carries tool, payment, wallet,
    deployment, protected-host mutation, or registration-change authority.

Exact schema whitelists and bounded values, mirroring the admission
model: identifiers must match ^[a-z][a-z0-9-]{2,63}$, lifecycle counters
are bounded non-negative integers, and the status vocabulary is a closed
frozenset whose "disabled" member models EMERGENCY DISABLEMENT. The
module is an OFFLINE FOUNDATION: no database, identity provider, Portal
account, external framework, or network is connected here.

R1 qualification (review 5756293645): the gate enforces a severe-status
reactivation latch (registered after revoked/disabled requires a
strictly newer revocation epoch) and observation freshness (observedAtUtc
inside a trusted-clock window of 300 s age / 30 s future skew).
Timestamp validation in this module remains SYNTAX validation only — it
is not cryptographic evidence authentication.
"""

import copy

from observatory.model import (
    IDENTIFIER_RE,
    MAX_INT_VALUE,
    ObservatoryRefusal,
    canonical_json,
)

from .model import parse_iso_utc

__all__ = [
    "LIFECYCLE_KIND",
    "LIFECYCLE_STATE_KEYS",
    "LIFECYCLE_STATUSES",
    "MAX_LIFECYCLE_COUNTER",
    "MAX_LIFECYCLE_STRING_CHARS",
    "build_lifecycle_state",
    "canonical_json",
    "synthetic_lifecycle_source",
    "validate_lifecycle_state",
]

LIFECYCLE_KIND = "toadaid-a2a-credential-lifecycle-state"

# Exact state shape — the source may report nothing else.
LIFECYCLE_STATE_KEYS = frozenset({
    "kind", "agentRef", "tenantRef", "ownerRef", "lifecycleStatus",
    "currentCredentialGeneration", "currentRevocationEpoch", "observedAtUtc",
})

# Closed, independently defined vocabulary. "registered" is the only
# admitting status; "suspended", "revoked" and "disabled" all refuse,
# with "disabled" modeling EMERGENCY DISABLEMENT. "revoked" and
# "disabled" are SEVERE: the gate latches them per identity (in-memory)
# and requires a STRICTLY newer currentRevocationEpoch before a later
# "registered" observation re-admits — a generation-only increase or a
# restored counter never re-authorizes. Suspension is deliberately not
# severe: trusted-source suspension recovery at an unchanged epoch
# stays legitimate. Timestamp validation here is syntactic only; the
# GATE enforces observation freshness against the trusted clock, and
# timestamp validation is not cryptographic evidence authentication.
LIFECYCLE_STATUSES = frozenset({
    "registered", "suspended", "revoked", "disabled",
})

MAX_LIFECYCLE_COUNTER = MAX_INT_VALUE
MAX_LIFECYCLE_STRING_CHARS = 256


def _pin_identifier(value, code):
    if not isinstance(value, str) or not IDENTIFIER_RE.match(value):
        raise ObservatoryRefusal(code)


def _pin_counter(value, code):
    if isinstance(value, bool) or not isinstance(value, int) \
            or value < 0 or value > MAX_LIFECYCLE_COUNTER:
        raise ObservatoryRefusal(code)


def _pin_iso_stamp(value, code):
    if not isinstance(value, str) \
            or len(value) > MAX_LIFECYCLE_STRING_CHARS \
            or parse_iso_utc(value) is None:
        raise ObservatoryRefusal(code)


def build_lifecycle_state(
    agent_ref,
    owner_ref,
    tenant_ref,
    lifecycle_status,
    current_credential_generation,
    current_revocation_epoch,
    observed_at_utc,
):
    """Build one validated trusted-lifecycle-state record.

    Exact whitelist (no **kwargs, no passthrough): only the seven
    independently verified fields can exist. This record is the SOURCE'S
    verified answer — it is never built from agent-supplied claims.
    """
    _pin_identifier(agent_ref, "LIFECYCLE_STATE_AGENT_REF_NOT_ADMITTED")
    _pin_identifier(owner_ref, "LIFECYCLE_STATE_OWNER_REF_NOT_ADMITTED")
    _pin_identifier(tenant_ref, "LIFECYCLE_STATE_TENANT_REF_NOT_ADMITTED")
    if not isinstance(lifecycle_status, str) \
            or lifecycle_status not in LIFECYCLE_STATUSES:
        raise ObservatoryRefusal("LIFECYCLE_STATUS_NOT_ADMITTED")
    _pin_counter(current_credential_generation,
                 "LIFECYCLE_GENERATION_NOT_ADMITTED")
    _pin_counter(current_revocation_epoch,
                 "LIFECYCLE_REVOCATION_EPOCH_NOT_ADMITTED")
    _pin_iso_stamp(observed_at_utc, "LIFECYCLE_OBSERVED_AT_NOT_ADMITTED")
    return {
        "kind": LIFECYCLE_KIND,
        "agentRef": agent_ref,
        "tenantRef": tenant_ref,
        "ownerRef": owner_ref,
        "lifecycleStatus": lifecycle_status,
        "currentCredentialGeneration": current_credential_generation,
        "currentRevocationEpoch": current_revocation_epoch,
        "observedAtUtc": observed_at_utc,
    }


def synthetic_lifecycle_source(states,
                               source_id="synthetic-offline-lifecycle-source"):
    """SYNTHETIC OFFLINE ONLY — NOT A REAL LIFECYCLE AUTHORITY.

    Maps agentRef -> trusted lifecycle states for offline tests and the
    synthetic rehearsal. The source answers WHO IS CURRENTLY ENABLED AND
    AT WHICH CREDENTIAL GENERATION; it is independent of both the
    registration adapter and any caller-supplied claim. Production stance
    stays fail-closed: a real deployment injects a trusted source (e.g.
    an independently observed revocation ledger) instead, and this
    factory is never wired to production.
    """
    if not isinstance(states, dict):
        raise ObservatoryRefusal("LIFECYCLE_SOURCE_STATES_SHAPE_INVALID")
    frozen = {}
    for agent_ref, raw in states.items():
        if not isinstance(agent_ref, str) or not IDENTIFIER_RE.match(agent_ref):
            raise ObservatoryRefusal("LIFECYCLE_SOURCE_KEY_NOT_ADMITTED")
        state = validate_lifecycle_state(raw)
        if state["agentRef"] != agent_ref:
            raise ObservatoryRefusal("LIFECYCLE_SOURCE_KEY_MISMATCH")
        frozen[agent_ref] = state
    return lambda query: copy.deepcopy(frozen.get(query["agentRef"]))


def validate_lifecycle_state(raw):
    """Re-validate one externally supplied state record, fail-closed.

    The record must reproduce EXACTLY what build_lifecycle_state would
    emit: an extra field, a missing field, a bad enum, or a bad counter
    refuses instead of degrading towards authorization.
    """
    if not isinstance(raw, dict) or set(raw) != LIFECYCLE_STATE_KEYS:
        raise ObservatoryRefusal("LIFECYCLE_STATE_SHAPE_INVALID")
    if raw["kind"] != LIFECYCLE_KIND:
        raise ObservatoryRefusal("LIFECYCLE_STATE_KIND_INVALID")
    built = build_lifecycle_state(
        agent_ref=raw["agentRef"],
        owner_ref=raw["ownerRef"],
        tenant_ref=raw["tenantRef"],
        lifecycle_status=raw["lifecycleStatus"],
        current_credential_generation=raw["currentCredentialGeneration"],
        current_revocation_epoch=raw["currentRevocationEpoch"],
        observed_at_utc=raw["observedAtUtc"],
    )
    if canonical_json(built) != canonical_json(raw):
        raise ObservatoryRefusal("LIFECYCLE_STATE_TAMPERED")
    return built