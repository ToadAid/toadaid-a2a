"""CUT-AO-P0A-20261103 — machine-readable Observatory interface contract.

Stable, frontend-facing contract for Codex's dashboard implementation after
Director review. This module fabricates NO route and serves nothing: the
contract is data describing the (local, synthetic, read-only) data surface,
plus synthetic example responses built from the bounded model.

Contract truthfulness rules reflected here:
  * ``agent.toadaid.org/dashboard/`` = PRIVATE owner dashboard (authenticated,
    authorized humans only; owner- and tenant-scoped; fail closed on missing
    authorization).
  * ``agent.toadaid.org/agents/`` = PUBLIC agent directory: SEPARATE FUTURE
    CUT, explicit owner publication consent required; never fed private
    observability data.
  * Four evidence classes (agent_reported / infrastructure_observed /
    human_authorized / unverified) are part of the contract; agent-reported
    items always arrive plainly marked ``claimed: true``.
  * No production authentication system is invented or bypassed here: the
    contract carries an authorization SEAM (trusted adapter), not an
    implementation. All authority flags stay false.
"""

from . import feed as _feed
from . import model as _model

__all__ = ["interface_contract", "synthetic_dashboard_example"]


def interface_contract():
    """Machine-readable data contract (no endpoints, no grants)."""
    return {
        "kind": "toadaid-observatory-interface-contract",
        "schemaVersion": "0.1.0",
        "contractStatus": "LOCAL_SYNTHETIC_FOUNDATION_NOT_DEPLOYED",
        "proposedSurface": {
            "privateOwnerDashboard": {
                "path": "/dashboard/",
                "origin": "https://agent.toadaid.org",
                "access": "authenticated-authorized-humans-only",
                "ownerScoped": True,
                "tenantIsolationEnforced": True,
                "readOnly": True,
                "failClosedOnMissingAuthorization": True,
            },
            "publicAgentDirectory": {
                "path": "/agents/",
                "origin": "https://agent.toadaid.org",
                "status": _feed.PUBLIC_DIRECTORY_STATUS,
                "includedInThisCut": False,
                "explicitOwnerPublicationConsentRequired": True,
                "privateObservabilityDataIncluded": False,
            },
        },
        "authorizationSeam": {
            "mechanism": "trusted-adapter-callable",
            "inventedAuthenticationSystem": False,
            "defaultPolicy": "refuse",
            "failClosed": True,
            "acceptsForbiddenEvidence": [
                "browser-timestamps", "self-reported-mfa",
                "client-authorization-assertions",
            ],
        },
        "feedContract": {
            "kind": _feed.DASHBOARD_KIND,
            "status": _feed.DASHBOARD_STATUS,
            "eventKinds": sorted(_model.EVENT_KINDS),
            "evidenceClasses": sorted(_model.EVIDENCE_CLASSES),
            "visibilityClasses": sorted(_model.VISIBILITY_CLASSES),
            "privacyClassifications": sorted(_model.PRIVACY_CLASSIFICATIONS),
            "registrationStatuses": sorted(_model.REGISTRATION_STATUSES),
            "pageLimits": list(_feed.ALLOWED_PAGE_LIMITS),
            "pageTokenPattern": "^cur:[0-9]{1,9}$",
            "maxEvents": _feed.MAX_EVENTS,
            "stableItemOrder": ["occurredAtUtc", "eventId"],
            "claimedMarker": "claimed",
            "unknownStatusPolicy":
                "non-confirmed status projects as 'unknown' only; the "
                "agent's claim is preserved separately as "
                "'claimedRegistrationStatus'",
        },
        "privacyContract": {
            "privateByDefault": True,
            "publicByExplicitConsent": True,
            "rawPrivateJournalsPublished": False,
            "crossTenantContentPublished": False,
            "secretsCredentialsRawPromptsPrivateReasoningIncluded": False,
            "agentReportedSilentlyTrusted": False,
        },
        "authority": {
            "executionEligible": False,
            "publicationAuthorized": False,
            "deploymentAuthorized": False,
            "agentRegistrationActive": False,
            "chatMessageApprovesOperation": False,
        },
    }


def synthetic_dashboard_example():
    """Synthetic example response for the frontend contract (offline)."""
    adapter = (lambda scope: scope["tenantRef"] == "tenant-alpha"
               and scope["ownerRef"] == "owner-alpha")
    recorder = _feed.FeedRecorder(trusted_authorization_adapter=adapter)
    from .model import AUTHORITY_FLAGS  # noqa: F401  (shape documentation)
    event = _model.build_event(
        event_kind="agent_identity_reference",
        event_id="evt-synthetic-alpha-001",
        correlation_id="corr-synthetic-alpha-001",
        occurred_at_utc="2026-11-03T00:00:00Z",
        evidence_class="infrastructure_observed",
        source_identity="agent-admission-portal",
        tenant_ref="tenant-alpha",
        owner_ref="owner-alpha",
        privacy_classification="community",
        visibility_class="operator",
        payload={"agentRef": "agent-synthetic-one",
                 "registrationStatus": "registered"},
    )
    recorder.record(event, "agent-admission-portal")
    claimed = _model.build_event(
        event_kind="agent_identity_reference",
        event_id="evt-synthetic-alpha-002",
        correlation_id="corr-synthetic-alpha-002",
        occurred_at_utc="2026-11-03T00:00:01Z",
        evidence_class="agent_reported",
        source_identity="agent-synthetic-two",
        tenant_ref="tenant-alpha",
        owner_ref="owner-alpha",
        privacy_classification="community",
        visibility_class="operator",
        payload={"agentRef": "agent-synthetic-two",
                 "registrationStatus": "registered"},
    )
    recorder.record(claimed, "agent-admission-portal")
    refusal = _model.build_event(
        event_kind="human_refusal_receipt",
        event_id="evt-synthetic-alpha-003",
        correlation_id="corr-synthetic-alpha-003",
        occurred_at_utc="2026-11-03T00:00:02Z",
        evidence_class="human_authorized",
        source_identity="independent-off-chat-human-process",
        tenant_ref="tenant-alpha",
        owner_ref="owner-alpha",
        privacy_classification="community",
        visibility_class="operator",
        payload={"decisionChannel": "independent-off-chat-human-process",
                 "decisionId": "dec-synthetic-003",
                 "subjectKind": "agent_enrollment_publication",
                 "subjectRef": "agent-synthetic-two",
                 "objectionCode": "PRIVACY"},
    )
    recorder.record(refusal, "lifecycle-journal")
    return _feed.owner_dashboard_feed(
        recorder,
        {"tenantRef": "tenant-alpha", "ownerRef": "owner-alpha",
         "authorizationId": "auth-synthetic-alpha"},
    )