"""CUT-A2A-P0D-A1-20261103 — framework-neutral registration decision model.

A registration decision is an ADAPTER-VERIFIED record, never a caller claim.
It binds, and refuses to build without, every field the mission requires:
stable agent identity, verified owner/controller reference, tenant,
registration status, current credential generation and revocation epoch,
evidence observation and expiry instants, and the specific A2A
participation scopes authorized. The framework name is descriptive
metadata ONLY — never proof of identity or authority, and no field implies
another automatically (a framework claim can never change status, evidence
or authority). Preserved invariant: A2A_CHAT_HAS_ZERO_EXECUTION_AUTHORITY —
admitted messages authorize no tool, payment, deployment, host mutation, or
registration change.
"""

import datetime
import re

from observatory.model import (
    IDENTIFIER_RE,
    MAX_INT_VALUE,
    ObservatoryRefusal,
    REGISTRATION_STATUSES,
    canonical_json,
)

__all__ = [
    "FRAMEWORK_KINDS",
    "PARTICIPATION_SCOPES",
    "MAX_DECISION_STRING_CHARS",
    "ADAPTER_ID_MAX_CHARS",
    "DECISION_KEYS",
    "parse_iso_utc",
    "build_registration_decision",
    "canonical_json",
]

# Descriptive metadata only. None of these values proves identity or
# authority, and no registration requirement is framework-conditioned.
FRAMEWORK_KINDS = frozenset({
    "agent0-diamond", "openclaw", "hermes", "community", "commercial",
    "other", "unspecified",
})

# The specific A2A participation scopes an adapter must authorize
# explicitly. Send and receive are separate concerns; either can be
# granted or withheld independently, and neither implies the other.
PARTICIPATION_SCOPES = frozenset({"a2a-message-send", "a2a-message-receive"})

MAX_DECISION_STRING_CHARS = 256
ADAPTER_ID_MAX_CHARS = 128

DECISION_KEYS = frozenset({
    "kind", "agentRef", "ownerRef", "tenantRef", "registrationStatus",
    "credentialGeneration", "revocationEpoch", "framework", "adapterId",
    "decisionObservedAtUtc", "evidenceExpiresAtUtc", "participationScopes",
    "authorityFlags",
})

_ISO_UTC_RE_TEMPLATE = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$"


def parse_iso_utc(value):
    """Calendar-real ISO-8601 UTC second-precision stamps -> datetime/None."""
    stamp = value if isinstance(value, str) else ""
    if not re.match(_ISO_UTC_RE_TEMPLATE, stamp):
        return None
    try:
        return datetime.datetime.strptime(stamp, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return None


def _pin_identifier(value, code):
    if not isinstance(value, str) or not IDENTIFIER_RE.match(value):
        raise ObservatoryRefusal(code)


def _pin_counter(value, code):
    if isinstance(value, bool) or not isinstance(value, int) \
            or value < 0 or value > MAX_INT_VALUE:
        raise ObservatoryRefusal(code)


def _pin_iso_stamp(value, code):
    if not isinstance(value, str) \
            or len(value) > MAX_DECISION_STRING_CHARS \
            or parse_iso_utc(value) is None:
        raise ObservatoryRefusal(code)


# Exact output shape — every field is adapter-verified input, and the fixed
# all-false flag block mirrors the observatory authority convention.
def build_registration_decision(
    agent_ref,
    owner_ref,
    tenant_ref,
    registration_status,
    credential_generation,
    revocation_epoch,
    framework,
    adapter_id,
    decision_observed_at_utc,
    evidence_expires_at_utc,
    participation_scopes,
):
    """Build one validated registration decision record.

    The signature is an exact whitelist (no **kwargs, no passthrough):
    only adapter-issued fields can exist, and framework/adapter metadata
    can never smuggle authority into the record.
    """
    _pin_identifier(agent_ref, "DECISION_AGENT_REF_NOT_ADMITTED")
    _pin_identifier(owner_ref, "DECISION_OWNER_REF_NOT_ADMITTED")
    _pin_identifier(tenant_ref, "DECISION_TENANT_REF_NOT_ADMITTED")
    if not isinstance(registration_status, str) \
            or registration_status not in REGISTRATION_STATUSES:
        raise ObservatoryRefusal("REGISTRATION_STATUS_NOT_ADMITTED")
    _pin_counter(credential_generation, "CREDENTIAL_GENERATION_NOT_ADMITTED")
    _pin_counter(revocation_epoch, "REVOCATION_EPOCH_NOT_ADMITTED")
    if not isinstance(framework, str) or framework not in FRAMEWORK_KINDS:
        raise ObservatoryRefusal("FRAMEWORK_NOT_ADMITTED")
    if not isinstance(adapter_id, str) or not adapter_id \
            or len(adapter_id) > ADAPTER_ID_MAX_CHARS:
        raise ObservatoryRefusal("ADAPTER_ID_NOT_ADMITTED")
    observed = parse_iso_utc(decision_observed_at_utc)
    if observed is None:
        raise ObservatoryRefusal("DECISION_OBSERVED_AT_NOT_ADMITTED")
    expires = parse_iso_utc(evidence_expires_at_utc)
    if expires is None:
        raise ObservatoryRefusal("EVIDENCE_EXPIRY_NOT_ADMITTED")
    if expires <= observed:
        raise ObservatoryRefusal("EVIDENCE_EXPIRY_NOT_AFTER_OBSERVATION")
    if not isinstance(participation_scopes, (list, tuple)) \
            or not participation_scopes \
            or len(participation_scopes) > len(PARTICIPATION_SCOPES):
        raise ObservatoryRefusal("PARTICIPATION_SCOPES_NOT_ADMITTED")
    for scope in participation_scopes:
        # isinstance guard: an unhashable element (list/dict) must produce
        # an explicit refusal, never an uncontrolled TypeError.
        if not isinstance(scope, str) or scope not in PARTICIPATION_SCOPES:
            raise ObservatoryRefusal("PARTICIPATION_SCOPE_NOT_ADMITTED")

    return {
        "kind": "toadaid-a2a-registration-decision",
        "agentRef": agent_ref,
        "ownerRef": owner_ref,
        "tenantRef": tenant_ref,
        "registrationStatus": registration_status,
        "credentialGeneration": credential_generation,
        "revocationEpoch": revocation_epoch,
        "framework": framework,
        "adapterId": adapter_id,
        "decisionObservedAtUtc": decision_observed_at_utc,
        "evidenceExpiresAtUtc": evidence_expires_at_utc,
        "participationScopes": sorted(set(participation_scopes)),
        "authorityFlags": {
            "executionAuthorized": False,
            "toolUseAuthorized": False,
            "paymentAuthorized": False,
            "deploymentAuthorized": False,
            "agentRegistrationChangeAuthorized": False,
            "publicDirectoryExposed": False,
        },
    }