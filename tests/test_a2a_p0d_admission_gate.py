"""CUT-A2A-P0D-A1-20261103 (R1) with CUT-A2A-P0D-A2-20261103 extension —
offline adversarial qualification of the registration-aware A2A
participation gate.

Synthetic, stdlib-only, no network, no sockets, no live agents: bounded
model, fail-closed adapter, caller-identity (registration is NOT
authentication), credential-LIFECYCLE state (P0D-A2: REVOCATION_OVERRIDES_
PRIOR_APPROVAL — no agent claim proves its own currency), and clock
seams; claim forgery refusals, sender SEND enforcement,
status/evidence freshness enforcement with correct UTC conversion,
participation scoping on both delivery sides, recipient-bound replay
identity, export/restore behavior, tenant isolation, and the two-agent
synthetic rehearsal (Registered Agent A -> gate -> Registered Agent B).
Two-framework fixtures use descriptive framework labels only — NO actual
OpenClaw/Hermes integration is claimed, wired, or tested. Boundary under
test: local synthetic engine, NOT DEPLOYED, zero execution authority.
P0D-A2 adversarial lifecycle controls live in
tests/test_a2a_p0d_credential_lifecycle.py.
"""

import copy
import datetime
import hashlib
import json
import unittest

from admission import model as admission_model
from admission import gate as gate_module
from admission.gate import (
    AdmissionJournal,
    AdmissionRefused,
    CallerCredential,
    ParticipationRefused,
    RegisteredAgentGate,
    REQUEST_KEYS,
    RECIPIENT_KEYS,
    synthetic_caller_credential,
    synthetic_caller_verifier,
    synthetic_registration_adapter,
)
from admission.lifecycle import (
    LIFECYCLE_STATUSES,
    build_lifecycle_state,
    synthetic_lifecycle_source,
)
from admission.model import (
    FRAMEWORK_KINDS,
    PARTICIPATION_SCOPES,
    build_registration_decision,
    canonical_json,
    parse_iso_utc,
)
from observatory.model import ObservatoryRefusal

SECRET_TEXT = "raw-private-conversation-content-should-never-be-journalled"

_OBSERVED = "2026-11-03T10:00:00Z"
_NOW = datetime.datetime(2026, 11, 3, 12, 0, 0)
_EXPIRY = "2026-11-04T10:00:00Z"

_ALL_AUTHORITY_FLAGS = {
    "executionAuthorized", "toolUseAuthorized", "paymentAuthorized",
    "deploymentAuthorized", "agentRegistrationChangeAuthorized",
    "publicDirectoryExposed",
}

# Opaque synthetic caller credentials — fixtures, NOT real identities.
_CRED_A = synthetic_caller_credential("fixture-caller-a")
_CRED_B = synthetic_caller_credential("fixture-caller-b")
_CRED_ALPHA = synthetic_caller_credential("fixture-caller-alpha")


def decision(agent_ref="agent-alpha-one", tenant_ref="tenant-alpha",
             owner_ref="owner-alpha", status="registered",
             generation=2, epoch=1, framework="unspecified",
             adapter_id="synthetic-offline-registration-adapter",
             observed=_OBSERVED, expires=_EXPIRY,
             scopes=("a2a-message-send", "a2a-message-receive")):
    return build_registration_decision(
        agent_ref=agent_ref,
        owner_ref=owner_ref,
        tenant_ref=tenant_ref,
        registration_status=status,
        credential_generation=generation,
        revocation_epoch=epoch,
        framework=framework,
        adapter_id=adapter_id,
        decision_observed_at_utc=observed,
        evidence_expires_at_utc=expires,
        participation_scopes=scopes,
    )


def request(agent_ref="agent-alpha-one", tenant_ref="tenant-alpha",
            owner_ref="owner-alpha", participation_scope="a2a-message-send",
            message_id="msg-alpha-001", correlation="corr-alpha-001",
            occurred="2026-11-03T12:00:00Z",
            body="bounded a2a metadata message for local rehearsal",
            message_type="conversation_message"):
    return {
        "agentRef": agent_ref,
        "tenantRef": tenant_ref,
        "ownerRef": owner_ref,
        "participationScope": participation_scope,
        "messageId": message_id,
        "correlationId": correlation,
        "occurredAtUtc": occurred,
        "message": {"messageType": message_type, "body": body},
    }


def recipient(agent_ref="agent-beta-one", tenant_ref="tenant-alpha",
              owner_ref="owner-alpha"):
    return {"agentRef": agent_ref, "tenantRef": tenant_ref, "ownerRef": owner_ref}


def lifecycle(agent_ref="agent-alpha-one", tenant_ref="tenant-alpha",
              owner_ref="owner-alpha", status="registered",
              generation=2, epoch=1, observed=_OBSERVED):
    """Trusted (source-issued) lifecycle state — the CURRENT truth."""
    return build_lifecycle_state(
        agent_ref=agent_ref,
        owner_ref=owner_ref,
        tenant_ref=tenant_ref,
        lifecycle_status=status,
        current_credential_generation=generation,
        current_revocation_epoch=epoch,
        observed_at_utc=observed,
    )


def matching_lifecycle_source(decisions, **overrides):
    """Source mirroring adapter decisions as CURRENT registered state.

    The P0D-A1 fixtures in this file keep the lifecycle source aligned
    with each agent's decision (always status "registered", so the
    decision-path refusal codes keep dominating). The dedicated
    lifecycle adversarial suite mutates or replaces the source directly.
    """
    states = {}
    for ref, record in decisions.items():
        kwargs = {
            "agent_ref": record["agentRef"],
            "tenant_ref": record["tenantRef"],
            "owner_ref": record["ownerRef"],
            "status": "registered",
            "generation": record["credentialGeneration"],
            "epoch": record["revocationEpoch"],
        }
        kwargs.update(overrides)
        states[ref] = lifecycle(**kwargs)
    return synthetic_lifecycle_source(states)


def rehearsal_decisions():
    return {
        "agent-openclaw-like": decision(
            agent_ref="agent-openclaw-like",
            tenant_ref="tenant-alpha", owner_ref="owner-alpha",
            framework="openclaw"),
        "agent-hermes-like": decision(
            agent_ref="agent-hermes-like",
            tenant_ref="tenant-alpha", owner_ref="owner-beta",
            framework="hermes"),
    }


def rehearsal_bindings():
    return {
        _CRED_A: {"agentRef": "agent-openclaw-like", "tenantRef": "tenant-alpha",
                  "ownerRef": "owner-alpha"},
        _CRED_B: {"agentRef": "agent-hermes-like", "tenantRef": "tenant-alpha",
                  "ownerRef": "owner-beta"},
    }


def rehearsal_gate(decisions=None, now=_NOW):
    """Two-agent synthetic rehearsal gate (framework-neutral).

    Agent A resembles an OpenClaw-registerable external agent; Agent B a
    Hermes-registerable external agent. Framework labels are descriptive
    metadata only — no integration with any real ecosystem is claimed or
    wired. The two agents hold different owners inside one tenant; the
    caller verifier binds an opaque credential to each (R1-4 fixture).
    """
    d = rehearsal_decisions() if decisions is None else decisions
    return RegisteredAgentGate(
        trusted_registration_adapter=synthetic_registration_adapter(d),
        trusted_caller_verifier=synthetic_caller_verifier(rehearsal_bindings()),
        trusted_lifecycle_source=matching_lifecycle_source(d),
        now=lambda: now,
    )


def single_gate(agent_ref="agent-alpha-one", tenant_ref="tenant-alpha",
                owner_ref="owner-alpha", **decision_kwargs):
    """Gate with one registered agent and one matching caller credential.

    Returns (gate, credential).
    """
    cred = synthetic_caller_credential("fixture-" + agent_ref)
    d = {agent_ref: decision(agent_ref=agent_ref, tenant_ref=tenant_ref,
                             owner_ref=owner_ref, **decision_kwargs)}
    gate = RegisteredAgentGate(
        trusted_registration_adapter=synthetic_registration_adapter(d),
        trusted_caller_verifier=synthetic_caller_verifier({
            cred: {"agentRef": agent_ref, "tenantRef": tenant_ref,
                   "ownerRef": owner_ref},
        }),
        trusted_lifecycle_source=matching_lifecycle_source(d),
        now=lambda: _NOW,
    )
    return gate, cred


class DecisionModelTests(unittest.TestCase):
    def test_decision_binds_every_required_field(self):
        record = decision()
        self.assertEqual(set(record), set(admission_model.DECISION_KEYS))
        self.assertFalse(any(record["authorityFlags"].values()))
        for field in ("agentRef", "ownerRef", "tenantRef", "registrationStatus",
                      "credentialGeneration", "revocationEpoch", "framework",
                      "adapterId", "decisionObservedAtUtc", "evidenceExpiresAtUtc",
                      "participationScopes"):
            self.assertTrue(field in record, field)
        self.assertEqual(record["kind"], "toadaid-a2a-registration-decision")
        # The decision NEVER carries proof-only privilege fields: no
        # provider-membership or MCP condition exists on the model.
        self.assertNotIn("erc8004Verified", record)
        self.assertNotIn("diamondRequired", record)
        self.assertNotIn("mcpRequired", record)

    def test_framework_is_descriptive_independent_metadata(self):
        self.assertEqual(
            FRAMEWORK_KINDS, frozenset({
                "agent0-diamond", "openclaw", "hermes", "community",
                "commercial", "other", "unspecified"}))
        for framework in ("openclaw", "hermes", "community", "unspecified"):
            record = decision(framework=framework)
            self.assertEqual(record["framework"], framework)
            # The framework label binds nothing: status, evidence and
            # authority are independent, explicitly-provided fields.
            self.assertEqual(record["registrationStatus"], "registered")
            self.assertFalse(any(record["authorityFlags"].values()))

    def test_scopes_sorted_and_canonical(self):
        self.assertEqual(decision(scopes=("a2a-message-receive",))
                         ["participationScopes"], ["a2a-message-receive"])
        # The model sorts and de-duplicates regardless of adapter order.
        self.assertEqual(
            decision(scopes=("a2a-message-receive", "a2a-message-send"))
            ["participationScopes"],
            ["a2a-message-receive", "a2a-message-send"])

    def test_no_kwargs_smuggling(self):
        with self.assertRaises(TypeError):
            build_registration_decision(
                **decision(), claimedOnline=True, erc8004Verified=True)

    def test_calendar_real_timestamps(self):
        self.assertIsNone(parse_iso_utc("2026-02-30T10:00:00Z"))
        self.assertIsNone(parse_iso_utc("2026-13-01T10:00:00Z"))
        self.assertIsNone(parse_iso_utc("2026-11-03T10:61:00Z"))
        self.assertIsNone(parse_iso_utc("not-a-stamp"))
        self.assertEqual(parse_iso_utc("2026-11-03T10:00:00Z"),
                         datetime.datetime(2026, 11, 3, 10, 0, 0))

    def test_malformed_collection_enums_explicitly_refused(self):
        # Non-string, unhashable, or collection-typed enum values must be
        # explicit refusals, never uncontrolled exceptions (TypeError/KeyError).
        cases = (
            ({"status": {"a": 1}}, "REGISTRATION_STATUS_NOT_ADMITTED"),
            ({"status": ["registered"]}, "REGISTRATION_STATUS_NOT_ADMITTED"),
            ({"framework": ["openclaw"]}, "FRAMEWORK_NOT_ADMITTED"),
            ({"framework": None}, "FRAMEWORK_NOT_ADMITTED"),
            ({"scopes": ["a2a-message-send", ["a2a-message-receive"]]},
             "PARTICIPATION_SCOPE_NOT_ADMITTED"),
            ({"scopes": ({"a2a-message-send": 1},)},
             "PARTICIPATION_SCOPE_NOT_ADMITTED"),
            ({"scopes": None}, "PARTICIPATION_SCOPES_NOT_ADMITTED"),
            ({"scopes": {0: "a2a-message-send"}},
             "PARTICIPATION_SCOPES_NOT_ADMITTED"),
        )
        for kwargs, code in cases:
            with self.subTest(code=code, kwargs=kwargs):
                with self.assertRaisesRegex(ObservatoryRefusal, code):
                    decision(**kwargs)

    def test_refusals_at_construction(self):
        cases = (
            ({"agent_ref": "Agent-Bad-Ref"},
             "DECISION_AGENT_REF_NOT_ADMITTED"),
            ({"agent_ref": 7}, "DECISION_AGENT_REF_NOT_ADMITTED"),
            ({"owner_ref": "ab"}, "DECISION_OWNER_REF_NOT_ADMITTED"),
            ({"tenant_ref": "tenant_underscore"},
             "DECISION_TENANT_REF_NOT_ADMITTED"),
            ({"status": "online"}, "REGISTRATION_STATUS_NOT_ADMITTED"),
            ({"generation": "2"}, "CREDENTIAL_GENERATION_NOT_ADMITTED"),
            ({"generation": True}, "CREDENTIAL_GENERATION_NOT_ADMITTED"),
            ({"epoch": -1}, "REVOCATION_EPOCH_NOT_ADMITTED"),
            ({"epoch": True}, "REVOCATION_EPOCH_NOT_ADMITTED"),
            ({"framework": "super-framework"}, "FRAMEWORK_NOT_ADMITTED"),
            ({"adapter_id": ""}, "ADAPTER_ID_NOT_ADMITTED"),
            ({"adapter_id": "a" * 129}, "ADAPTER_ID_NOT_ADMITTED"),
            ({"observed": "2026-02-30T10:00:00Z"},
             "DECISION_OBSERVED_AT_NOT_ADMITTED"),
            ({"expires": "2026-11-04T10:61:00Z"},
             "EVIDENCE_EXPIRY_NOT_ADMITTED"),
            ({"expires": "2026-11-04T10:00:00Z",
              "observed": "2026-11-04T10:00:00Z"},
             "EVIDENCE_EXPIRY_NOT_AFTER_OBSERVATION"),
            ({"scopes": ()}, "PARTICIPATION_SCOPES_NOT_ADMITTED"),
            ({"scopes": "a2a-message-send"},
             "PARTICIPATION_SCOPES_NOT_ADMITTED"),
            ({"scopes": ("a2a-message-run-tools",)},
             "PARTICIPATION_SCOPE_NOT_ADMITTED"),
        )
        for kwargs, code in cases:
            with self.subTest(code=code, kwargs=kwargs):
                with self.assertRaisesRegex(ObservatoryRefusal, code):
                    decision(**kwargs)


class CallerIdentityTests(unittest.TestCase):
    """R1-4 — registration is not authentication; self-asserted identity
    strings authenticate no one."""

    def test_missing_caller_verifier_refused(self):
        gate = RegisteredAgentGate(
            trusted_registration_adapter=synthetic_registration_adapter(
                {"agent-alpha-one": decision()}),
            now=lambda: _NOW)
        for call in (lambda: gate.authorize(request()),
                     lambda: gate.route(request(), recipient())):
            with self.subTest(call=call):
                with self.assertRaisesRegex(
                        ParticipationRefused,
                        "CALLER_AUTHENTICATOR_NOT_TRUSTED"):
                    call()

    def test_none_and_foreign_credentials_refused(self):
        gate = rehearsal_gate()
        for bad_credential in (None, 7, {"agentRef": "agent-openclaw-like"},
                               [".token"], "agent-openclaw-like"):
            with self.subTest(bad_credential=bad_credential):
                with self.assertRaisesRegex(
                        ParticipationRefused,
                        "CALLER_CREDENTIAL_NOT_ADMITTED"):
                    gate.authorize(request(), bad_credential)

    def test_identity_string_cannot_impersonate_registered_principal(self):
        # The classic attack: know the registered agent's public IDs,
        # present them as the credential, skip the binding entirely.
        gate = rehearsal_gate()
        for impersonation in ("agent-openclaw-like",
                              json.dumps({"agentRef": "agent-openclaw-like",
                                          "tenantRef": "tenant-alpha",
                                          "ownerRef": "owner-alpha"})):
            with self.subTest(impersonation=impersonation[:40]):
                with self.assertRaisesRegex(
                        ParticipationRefused,
                        "CALLER_CREDENTIAL_NOT_ADMITTED"):
                    gate.authorize(request(), impersonation)

    def test_unbound_credential_refused(self):
        gate = rehearsal_gate()
        stranger = synthetic_caller_credential("fixture-caller-stranger")
        with self.assertRaisesRegex(ParticipationRefused,
                                    "CALLER_NOT_AUTHENTICATED"):
            gate.authorize(request(agent_ref="agent-stranger-9"), stranger)

    def test_verified_principal_with_other_identity_mismatch_refused(self):
        # Even a VALID credential cannot act outside its verified binding.
        gate = rehearsal_gate()
        with self.assertRaisesRegex(ParticipationRefused,
                                    "CALLER_IDENTITY_MISMATCH"):
            gate.authorize(request(), _CRED_B)
        with self.assertRaisesRegex(ParticipationRefused,
                                    "CALLER_IDENTITY_MISMATCH"):
            gate.route(request(), recipient(agent_ref="agent-hermes-like",
                                            owner_ref="owner-beta"), _CRED_A)

    def test_self_asserted_context_tampering_refused_per_field(self):
        gate = rehearsal_gate()
        for field, value in (("tenantRef", "tenant-impersonate"),
                             ("ownerRef", "owner-impersonate"),
                             ("agentRef", "agent-phantom-0001")):
            forged = request()
            forged[field] = value
            with self.subTest(field=field):
                with self.assertRaisesRegex(
                        ParticipationRefused, "CALLER_IDENTITY_MISMATCH"):
                    gate.authorize(forged, _CRED_A)

    def test_tampered_verifier_binding_refused(self):
        adapter = synthetic_registration_adapter({"agent-alpha-one": decision()})
        for bad_binding, code in (
            (None, "CALLER_NOT_AUTHENTICATED"),
            ([], "CALLER_BINDING_REJECTED"),
            ({"agentRef": "agent-alpha-one"}, "CALLER_BINDING_REJECTED"),
            ({"agentRef": "agent-alpha-one", "tenantRef": "t-x",
              "ownerRef": "owner-x", "claimed": True}, "CALLER_BINDING_REJECTED"),
            ({"agentRef": "Agent Bad", "tenantRef": "tenant-alpha",
              "ownerRef": "owner-alpha"}, "CALLER_BINDING_REJECTED"),
        ):
            gate = RegisteredAgentGate(
                trusted_registration_adapter=adapter,
                trusted_caller_verifier=lambda credential, b=bad_binding: (
                    copy.deepcopy(b) if b is not None else None),
                now=lambda: _NOW)
            with self.subTest(code=code, bad_binding=str(bad_binding)[:60]):
                with self.assertRaisesRegex(ParticipationRefused, code):
                    gate.authorize(request(), _CRED_ALPHA)


class SenderSendAuthorityTests(unittest.TestCase):
    """R1-1 — every route() requires a2a-message-send for its sender,
    regardless of the request's declared scope."""

    def _receive_only_gate(self):
        return single_gate(scopes=("a2a-message-receive",))

    def test_receive_only_sender_declaring_receive_refused(self):
        gate, cred = self._receive_only_gate()
        with self.assertRaisesRegex(ParticipationRefused,
                                    "SENDER_SCOPE_MISMATCH"):
            gate.route(request(participation_scope="a2a-message-receive"),
                       recipient(), cred)

    def test_receive_only_sender_declaring_send_refused(self):
        gate, cred = self._receive_only_gate()
        with self.assertRaisesRegex(ParticipationRefused,
                                    "PARTICIPATION_SCOPE_NOT_AUTHORIZED"):
            gate.route(request(participation_scope="a2a-message-send"),
                       recipient(), cred)

    def test_dual_grant_sender_declaring_receive_still_refused(self):
        # The declared scope must match the routing operation even when
        # the send grant exists: a route request is a send, not a receive.
        gate = rehearsal_gate()
        with self.assertRaisesRegex(ParticipationRefused,
                                    "SENDER_SCOPE_MISMATCH"):
            gate.route(request(agent_ref="agent-openclaw-like",
                               participation_scope="a2a-message-receive"),
                       recipient(agent_ref="agent-hermes-like",
                                 owner_ref="owner-beta"), _CRED_A)

    def test_send_granted_sender_still_requires_declared_send(self):
        gate = rehearsal_gate()
        receipt = gate.route(request(agent_ref="agent-openclaw-like",
                                     participation_scope="a2a-message-send"),
                             recipient(agent_ref="agent-hermes-like",
                                       owner_ref="owner-beta"), _CRED_A)
        self.assertEqual(receipt["decision"], "DELIVERED_LOCAL_SYNTHETIC")

    def test_receive_only_authorize_probe_still_works(self):
        # authorize() verifies a declared scope honestly: a receive-only
        # agent IS authorized to receive; it is just never a sender.
        gate, cred = self._receive_only_gate()
        receipt = gate.authorize(request(participation_scope="a2a-message-receive"),
                                 cred)
        self.assertEqual(receipt["decision"], "AUTHORIZED_LOCAL_SYNTHETIC")
        self.assertEqual(receipt["participationScope"], "a2a-message-receive")


class UtcEvidenceTests(unittest.TestCase):
    """R1-3 — aware clocks convert to true UTC before expiry comparison."""

    def test_nonzero_offset_refuses_exactly_expired_evidence(self):
        # 14:00+02:00 == 12:00Z -> evidence expiring 12:00:00Z is exhausted.
        d = {"agent-alpha-one": decision(expires="2026-11-03T12:00:00Z")}
        gate = RegisteredAgentGate(
            trusted_registration_adapter=synthetic_registration_adapter(d),
            trusted_caller_verifier=synthetic_caller_verifier({
                _CRED_ALPHA: {"agentRef": "agent-alpha-one",
                              "tenantRef": "tenant-alpha",
                              "ownerRef": "owner-alpha"},
            }),
            trusted_lifecycle_source=matching_lifecycle_source(d),
            now=lambda: datetime.datetime(
                2026, 11, 3, 14, 0, 0,
                tzinfo=datetime.timezone(datetime.timedelta(hours=2))))
        with self.assertRaisesRegex(ParticipationRefused,
                                    "REGISTRATION_EVIDENCE_EXPIRED"):
            gate.authorize(request(), _CRED_ALPHA)

    def test_nonzero_offset_admits_one_second_of_headroom(self):
        # 13:59:59+02:00 == 11:59:59Z -> evidence expiring 12:00:00Z is live.
        d = {"agent-alpha-one": decision(expires="2026-11-03T12:00:00Z")}
        gate = RegisteredAgentGate(
            trusted_registration_adapter=synthetic_registration_adapter(d),
            trusted_caller_verifier=synthetic_caller_verifier({
                _CRED_ALPHA: {"agentRef": "agent-alpha-one",
                              "tenantRef": "tenant-alpha",
                              "ownerRef": "owner-alpha"},
            }),
            trusted_lifecycle_source=matching_lifecycle_source(d),
            now=lambda: datetime.datetime(
                2026, 11, 3, 13, 59, 59,
                tzinfo=datetime.timezone(datetime.timedelta(hours=2))))
        receipt = gate.authorize(request(), _CRED_ALPHA)
        self.assertEqual(receipt["decision"], "AUTHORIZED_LOCAL_SYNTHETIC")

    def test_correct_utc_conversion_admits_not_yet_expired(self):
        # 16:00+05:45 == 10:15Z -> evidence expiring 11:00Z is still live
        # (a naive-strip bug would read 16:00 and refuse).
        d = {"agent-alpha-one": decision(expires="2026-11-03T11:00:00Z")}
        gate = RegisteredAgentGate(
            trusted_registration_adapter=synthetic_registration_adapter(d),
            trusted_caller_verifier=synthetic_caller_verifier({
                _CRED_ALPHA: {"agentRef": "agent-alpha-one",
                              "tenantRef": "tenant-alpha",
                              "ownerRef": "owner-alpha"},
            }),
            trusted_lifecycle_source=matching_lifecycle_source(d),
            now=lambda: datetime.datetime(
                2026, 11, 3, 16, 0, 0,
                tzinfo=datetime.timezone(datetime.timedelta(hours=5, minutes=45))))
        receipt = gate.authorize(request(), _CRED_ALPHA)
        self.assertEqual(receipt["decision"], "AUTHORIZED_LOCAL_SYNTHETIC")

    def test_correct_utc_conversion_refuses_across_long_offset(self):
        # 07:00-06:00 == 13:00Z -> evidence expiring 11:00Z is dead.
        d = {"agent-alpha-one": decision(expires="2026-11-03T11:00:00Z")}
        gate = RegisteredAgentGate(
            trusted_registration_adapter=synthetic_registration_adapter(d),
            trusted_caller_verifier=synthetic_caller_verifier({
                _CRED_ALPHA: {"agentRef": "agent-alpha-one",
                              "tenantRef": "tenant-alpha",
                              "ownerRef": "owner-alpha"},
            }),
            trusted_lifecycle_source=matching_lifecycle_source(d),
            now=lambda: datetime.datetime(
                2026, 11, 3, 7, 0, 0,
                tzinfo=datetime.timezone(datetime.timedelta(hours=-6))))
        with self.assertRaisesRegex(ParticipationRefused,
                                    "REGISTRATION_EVIDENCE_EXPIRED"):
            gate.authorize(request(), _CRED_ALPHA)

    def test_naive_clock_unaffected(self):
        gate, cred = single_gate()
        receipt = gate.authorize(request(), cred)
        self.assertEqual(receipt["decision"], "AUTHORIZED_LOCAL_SYNTHETIC")


class GateFailClosedTests(unittest.TestCase):
    def test_default_gate_refuses_everything(self):
        gate = RegisteredAgentGate()
        with self.assertRaisesRegex(ParticipationRefused,
                                    "CALLER_AUTHENTICATOR_NOT_TRUSTED"):
            gate.authorize(request())
        with self.assertRaisesRegex(ParticipationRefused,
                                    "CALLER_AUTHENTICATOR_NOT_TRUSTED"):
            gate.route(request(), recipient())

    def test_missing_registration_adapter_refused(self):
        gate = RegisteredAgentGate(
            trusted_caller_verifier=synthetic_caller_verifier({
                _CRED_ALPHA: {"agentRef": "agent-alpha-one",
                              "tenantRef": "tenant-alpha",
                              "ownerRef": "owner-alpha"},
            }),
            now=lambda: _NOW)
        with self.assertRaisesRegex(ParticipationRefused,
                                    "ADMISSION_AUTHORIZATION_REQUIRED"):
            gate.authorize(request(), _CRED_ALPHA)

    def test_missing_clock_refused(self):
        gate = RegisteredAgentGate(
            trusted_registration_adapter=synthetic_registration_adapter(
                {"agent-alpha-one": decision()}),
            trusted_caller_verifier=synthetic_caller_verifier({
                _CRED_ALPHA: {"agentRef": "agent-alpha-one",
                              "tenantRef": "tenant-alpha",
                              "ownerRef": "owner-alpha"}}))
        with self.assertRaisesRegex(ParticipationRefused,
                                    "CLOCK_SOURCE_REQUIRED"):
            gate.authorize(request(), _CRED_ALPHA)

    def test_non_callable_and_bad_clock_refused(self):
        gate, cred = single_gate()
        for bad_clock in (42, "stamp", lambda: "not-a-datetime"):
            gate.now = bad_clock
            with self.subTest(bad_clock=bad_clock):
                with self.assertRaisesRegex(ParticipationRefused,
                                            "CLOCK_SOURCE_REQUIRED"):
                    gate.authorize(request(), cred)

    def test_adapter_returning_none_refused(self):
        gate = RegisteredAgentGate(
            trusted_registration_adapter=synthetic_registration_adapter({}),
            trusted_caller_verifier=synthetic_caller_verifier({
                _CRED_ALPHA: {"agentRef": "agent-alpha-one",
                              "tenantRef": "tenant-alpha",
                              "ownerRef": "owner-alpha"},
            }),
            now=lambda: _NOW)
        with self.assertRaisesRegex(ParticipationRefused,
                                    "REGISTRATION_NOT_FOUND"):
            gate.authorize(request(), _CRED_ALPHA)

    def test_adapter_extra_field_refused(self):
        broken_extra = {**decision(), "claimedOnline": True}
        gate = RegisteredAgentGate(
            trusted_registration_adapter=synthetic_registration_adapter(
                {"agent-alpha-one": broken_extra}),
            trusted_caller_verifier=synthetic_caller_verifier({
                _CRED_ALPHA: {"agentRef": "agent-alpha-one",
                              "tenantRef": "tenant-alpha",
                              "ownerRef": "owner-alpha"},
            }),
            now=lambda: _NOW)
        with self.assertRaisesRegex(ParticipationRefused,
                                    "REGISTRATION_DECISION_TAMPERED"):
            gate.authorize(request(), _CRED_ALPHA)

    def test_malformed_adapter_record_fails_closed(self):
        broken = {**decision(), "framework": "bogus-framework"}
        gate, cred = single_gate()
        gate.trusted_registration_adapter = synthetic_registration_adapter(
            {"agent-alpha-one": broken})
        with self.assertRaisesRegex(ObservatoryRefusal,
                                    "FRAMEWORK_NOT_ADMITTED"):
            gate.authorize(request(), cred)

    def test_flipped_authority_flag_never_survives_rebuild(self):
        record = decision()
        forged = dict(record)
        forged["authorityFlags"] = dict(record["authorityFlags"])
        forged["authorityFlags"]["executionAuthorized"] = True
        gate, cred = single_gate()
        gate.trusted_registration_adapter = synthetic_registration_adapter(
            {"agent-alpha-one": forged})
        with self.assertRaisesRegex(ParticipationRefused,
                                    "REGISTRATION_DECISION_TAMPERED"):
            gate.authorize(request(), cred)


class StatusAndFreshnessTests(unittest.TestCase):
    def _gate_for_status(self, status):
        return single_gate(status=status)

    def test_registered_admitted(self):
        gate, cred = self._gate_for_status("registered")
        receipt = gate.authorize(request(), cred)
        self.assertEqual(receipt["decision"], "AUTHORIZED_LOCAL_SYNTHETIC")

    def test_revoked_refused(self):
        gate, cred = self._gate_for_status("revoked")
        with self.assertRaisesRegex(ParticipationRefused,
                                    "REGISTRATION_REVOKED"):
            gate.authorize(request(), cred)

    def test_suspended_refused(self):
        gate, cred = self._gate_for_status("suspended")
        with self.assertRaisesRegex(ParticipationRefused,
                                    "REGISTRATION_SUSPENDED"):
            gate.authorize(request(), cred)

    def test_unregistered_refused(self):
        gate, cred = self._gate_for_status("unregistered")
        with self.assertRaisesRegex(ParticipationRefused,
                                    "REGISTRATION_UNREGISTERED"):
            gate.authorize(request(), cred)

    def test_unknown_status_refused(self):
        gate, cred = self._gate_for_status("unknown")
        with self.assertRaisesRegex(ParticipationRefused,
                                    "REGISTRATION_UNKNOWN_STATUS"):
            gate.authorize(request(), cred)

    def test_expired_evidence_refused(self):
        gate, cred = single_gate(expires=_EXPIRY)
        gate.now = lambda: datetime.datetime(2026, 11, 4, 11, 0, 1)
        with self.assertRaisesRegex(ParticipationRefused,
                                    "REGISTRATION_EVIDENCE_EXPIRED"):
            gate.authorize(request(), cred)

    def test_expiry_boundary_is_inclusive(self):
        gate, cred = single_gate(expires="2026-11-03T12:00:00Z")
        with self.assertRaisesRegex(ParticipationRefused,
                                    "REGISTRATION_EVIDENCE_EXPIRED"):
            gate.authorize(request(), cred)

    def test_one_second_of_headroom_admits(self):
        gate, cred = single_gate(expires="2026-11-03T12:00:01Z")
        receipt = gate.authorize(request(), cred)
        self.assertEqual(receipt["decision"], "AUTHORIZED_LOCAL_SYNTHETIC")


class ClaimForgeryTests(unittest.TestCase):
    """A registration claim from an Agent Card, a message body, a browser,
    or raw request keys NEVER authorizes."""

    def test_agent_card_claim_never_authorizes(self):
        forged = request()
        forged["claimedRegistration"] = {
            "registrationStatus": "registered",
            "credentialGeneration": 9,
            "revocationEpoch": 0,
            "framework": "openclaw",
        }
        gate = rehearsal_gate()
        with self.assertRaisesRegex(AdmissionRefused,
                                    "REQUEST_KEYS_NOT_ADMITTED"):
            gate.authorize(forged, _CRED_A)

    def test_execution_and_payment_requests_never_admitted(self):
        for extra_key, value in (
            ("toolRequest", {"name": "rm", "args": []}),
            ("paymentIntent", {"amount": 1}),
            ("walletRef", "wallet-alpha"),
            ("deployRequest", {"target": "prod"}),
            ("registrationChange", {"status": "revoked"}),
            ("publicDirectory", True),
        ):
            forged = request()
            forged[extra_key] = value
            gate = rehearsal_gate()
            with self.subTest(extra_key=extra_key):
                with self.assertRaisesRegex(AdmissionRefused,
                                            "REQUEST_KEYS_NOT_ADMITTED"):
                    gate.authorize(forged, _CRED_A)
                self.assertEqual(len(gate.journal.entries()), 0)

    def test_message_body_claim_is_inert(self):
        # The body may contain any text — including convincing registration
        # claims from OTHER agents — but only the trusted seams decide;
        # the body is never read for authority.
        forged_body = json.dumps({
            "a2aRegistration": {
                "agentRef": "agent-stranger-9",
                "registrationStatus": "registered",
                "participationScopes": ["a2a-message-send",
                                        "a2a-message-receive"],
            }
        }, sort_keys=True)
        gate = rehearsal_gate()
        receipt = gate.authorize(
            request(agent_ref="agent-openclaw-like", body=forged_body[:256]),
            _CRED_A)
        self.assertEqual(receipt["decision"], "AUTHORIZED_LOCAL_SYNTHETIC")

    def test_unregistered_agent_has_no_path_in(self):
        gate = rehearsal_gate()
        stranger = synthetic_caller_credential("fixture-caller-stranger")
        with self.assertRaisesRegex(ParticipationRefused,
                                    "CALLER_NOT_AUTHENTICATED"):
            gate.authorize(request(agent_ref="agent-stranger-9"), stranger)

    def test_admitted_receipt_carries_zero_authority(self):
        gate = rehearsal_gate()
        receipt = gate.authorize(request(agent_ref="agent-openclaw-like"), _CRED_A)
        self.assertEqual(set(receipt["authorityFlags"]), _ALL_AUTHORITY_FLAGS)
        self.assertFalse(any(receipt["authorityFlags"].values()))
        self.assertEqual(receipt["boundary"],
                         gate_module.A2A_CHAT_HAS_ZERO_EXECUTION_AUTHORITY)


class ParticipationScopeTests(unittest.TestCase):
    def test_receive_scope_required_for_recipient(self):
        gate = rehearsal_gate()
        decisions = {
            "agent-openclaw-like": decision(agent_ref="agent-openclaw-like",
                                            owner_ref="owner-alpha"),
            "agent-hermes-like": decision(agent_ref="agent-hermes-like",
                                          owner_ref="owner-beta",
                                          scopes=("a2a-message-send",)),
        }
        gate.trusted_registration_adapter = synthetic_registration_adapter(decisions)
        with self.assertRaisesRegex(ParticipationRefused,
                                    "PARTICIPATION_SCOPE_NOT_AUTHORIZED"):
            gate.route(request(agent_ref="agent-openclaw-like"),
                       recipient(agent_ref="agent-hermes-like",
                                 owner_ref="owner-beta"), _CRED_A)

    def test_unknown_scope_shape_refused(self):
        gate = rehearsal_gate()
        with self.assertRaisesRegex(AdmissionRefused,
                                    "PARTICIPATION_SCOPE_NOT_ADMITTED"):
            gate.authorize(request(
                agent_ref="agent-openclaw-like",
                participation_scope="a2a-message-run-tools"), _CRED_A)

    def test_route_requires_both_sides_registered(self):
        gate = rehearsal_gate()
        with self.assertRaisesRegex(ParticipationRefused,
                                    "REGISTRATION_NOT_FOUND"):
            gate.route(request(agent_ref="agent-openclaw-like"),
                       recipient(agent_ref="agent-unregistered-1", owner_ref="owner-beta"),
                       _CRED_A)


class RequestShapeTests(unittest.TestCase):
    def test_non_dict_refused(self):
        gate = rehearsal_gate()
        for bad in (None, [], "request", b"bytes"):
            with self.subTest(bad=bad):
                with self.assertRaisesRegex(AdmissionRefused,
                                            "REQUEST_SHAPE_INVALID"):
                    gate.authorize(bad, _CRED_A)

    def test_exact_request_keys_enforced(self):
        gate = rehearsal_gate()
        forged = {**request(), "extraClaim": "x"}
        with self.assertRaisesRegex(AdmissionRefused,
                                    "REQUEST_KEYS_NOT_ADMITTED"):
            gate.authorize(forged, _CRED_A)
        missing = request()
        missing.pop("correlationId")
        with self.assertRaisesRegex(AdmissionRefused,
                                    "REQUEST_KEYS_NOT_ADMITTED"):
            gate.authorize(missing, _CRED_A)

    def test_identifier_fields_type_and_value_checked(self):
        gate = rehearsal_gate()
        for field in ("agentRef", "tenantRef", "ownerRef", "messageId",
                      "correlationId"):
            bad = request()
            bad[field] = "Bad Ref!"
            with self.subTest(field=field):
                with self.assertRaisesRegex(
                        AdmissionRefused, "REQUEST_%s_NOT_ADMITTED"
                        % field.upper()):
                    gate.authorize(bad, _CRED_A)
        bad = request()
        bad["messageId"] = 7
        with self.assertRaisesRegex(AdmissionRefused,
                                    "REQUEST_MESSAGEID_NOT_ADMITTED"):
            gate.authorize(bad, _CRED_A)

    def test_message_shape_type_and_bounds(self):
        gate = rehearsal_gate()
        base = dict(request())
        for message in (None, "body", {}, {"messageType": "conversation_message"},
                        {"messageType": "conversation_message", "body": "x",
                         "claim": "register-me"}):
            bad = dict(base)
            bad["message"] = message
            with self.subTest(message=message):
                with self.assertRaisesRegex(AdmissionRefused,
                                            "MESSAGE_KEYS_NOT_ADMITTED"):
                    gate.authorize(bad, _CRED_A)
        bad = dict(base)
        bad["message"] = {"messageType": "email", "body": "x"}
        with self.assertRaisesRegex(AdmissionRefused,
                                    "MESSAGE_TYPE_NOT_ADMITTED"):
            gate.authorize(bad, _CRED_A)
        bad = dict(base)
        bad["message"] = {"messageType": ["conversation_message"], "body": "x"}
        with self.assertRaisesRegex(AdmissionRefused,
                                    "MESSAGE_TYPE_NOT_ADMITTED"):
            gate.authorize(bad, _CRED_A)
        bad = dict(base)
        bad["message"] = {"messageType": "conversation_message", "body": ""}
        with self.assertRaisesRegex(AdmissionRefused,
                                    "MESSAGE_BODY_NOT_ADMITTED"):
            gate.authorize(bad, _CRED_A)
        bad = dict(base)
        bad["message"] = {"messageType": "conversation_message",
                          "body": "y" * 257}
        with self.assertRaisesRegex(AdmissionRefused,
                                    "MESSAGE_BODY_NOT_ADMITTED"):
            gate.authorize(bad, _CRED_A)

    def test_timestamp_shape_and_bounds(self):
        gate = rehearsal_gate()
        for occurred in ("2026-13-01T00:00:00Z", "nope", 1730600000,
                         "2026-02-30T00:00:00Z"):
            with self.subTest(occurred=occurred):
                with self.assertRaisesRegex(AdmissionRefused,
                                            "REQUEST_TIMESTAMP_NOT_ADMITTED"):
                    gate.authorize(request(occurred=occurred), _CRED_A)

    def test_recipient_context_pinned_before_adapter(self):
        gate = rehearsal_gate()
        for bad_recipient, code in (
            (None, "RECIPIENT_KEYS_NOT_ADMITTED"),
            ("agent-hermes-like", "RECIPIENT_KEYS_NOT_ADMITTED"),
            ({"agentRef": "agent-hermes-like"}, "RECIPIENT_KEYS_NOT_ADMITTED"),
            ({"agentRef": "agent-hermes-like", "tenantRef": "tenant-alpha"},
             "RECIPIENT_KEYS_NOT_ADMITTED"),
            (dict(recipient(agent_ref="agent-hermes-like"), extraClaim=True),
             "RECIPIENT_KEYS_NOT_ADMITTED"),
            (recipient(agent_ref="Agent-Hermes", owner_ref="owner-beta"),
             "RECIPIENT_REF_NOT_ADMITTED"),
            (recipient(agent_ref="agent-hermes-like",
                       tenant_ref="Tenant_Alpha", owner_ref="owner-beta"),
             "RECIPIENT_TENANT_REF_NOT_ADMITTED"),
            (recipient(agent_ref="agent-hermes-like",
                       tenant_ref="tenant-alpha", owner_ref=42),
             "RECIPIENT_OWNER_REF_NOT_ADMITTED"),
        ):
            with self.subTest(code=code, bad_recipient=str(bad_recipient)[:60]):
                entries_before = len(gate.journal.entries())
                with self.assertRaisesRegex(AdmissionRefused, code):
                    gate.route(request(agent_ref="agent-openclaw-like"),
                               bad_recipient, _CRED_A)
                self.assertEqual(len(gate.journal.entries()), entries_before)

    def test_self_delivery_refused(self):
        gate = rehearsal_gate()
        with self.assertRaisesRegex(AdmissionRefused,
                                    "SELF_DELIVERY_NOT_ADMITTED"):
            gate.route(request(agent_ref="agent-openclaw-like"),
                       recipient(agent_ref="agent-openclaw-like",
                                 owner_ref="owner-alpha"), _CRED_A)

    def test_malformed_request_enums_explicitly_refused(self):
        gate = rehearsal_gate()
        bad = request(agent_ref="agent-openclaw-like")
        bad["participationScope"] = ["a2a-message-send"]
        with self.assertRaisesRegex(AdmissionRefused,
                                    "PARTICIPATION_SCOPE_NOT_ADMITTED"):
            gate.authorize(bad, _CRED_A)
        bad = request(agent_ref="agent-openclaw-like")
        bad["participationScope"] = {"scope": "a2a-message-send"}
        with self.assertRaisesRegex(AdmissionRefused,
                                    "PARTICIPATION_SCOPE_NOT_ADMITTED"):
            gate.authorize(bad, _CRED_A)


class ReplayAndRestartTests(unittest.TestCase):
    def test_identical_replay_is_idempotent(self):
        gate = rehearsal_gate()
        req = request(agent_ref="agent-openclaw-like")
        first = gate.route(req, recipient(agent_ref="agent-hermes-like",
                                          owner_ref="owner-beta"), _CRED_A)
        second = gate.route(req, recipient(agent_ref="agent-hermes-like",
                                           owner_ref="owner-beta"), _CRED_A)
        self.assertEqual(first["journalResult"], "recorded")
        self.assertEqual(second["journalResult"], "replayed-idempotent")
        self.assertEqual(len(gate.journal.entries()), 1)

    def test_same_message_id_to_second_recipient_refused(self):
        """R1-2 — replay identity binds the verified recipient."""
        decisions = rehearsal_decisions()
        decisions["agent-community-like"] = decision(
            agent_ref="agent-community-like",
            tenant_ref="tenant-alpha", owner_ref="owner-gamma")
        gate = rehearsal_gate(decisions=decisions)
        req = request(agent_ref="agent-openclaw-like")
        first = gate.route(req, recipient(agent_ref="agent-hermes-like",
                                          owner_ref="owner-beta"), _CRED_A)
        self.assertEqual(first["journalResult"], "recorded")
        # A distinct registered recipient with the SAME message ID: not an
        # identical replay — refused, and no second journal entry.
        with self.assertRaisesRegex(ParticipationRefused,
                                    "REPLAY_MESSAGE_ID_CONFLICT"):
            gate.route(req, recipient(agent_ref="agent-community-like",
                                      owner_ref="owner-gamma"), _CRED_A)
        self.assertEqual(len(gate.journal.entries()), 1)

    def test_conflicting_content_same_id_refused(self):
        gate = rehearsal_gate()
        gate.route(request(agent_ref="agent-openclaw-like",
                           message_id="msg-alpha-001"),
                   recipient(agent_ref="agent-hermes-like",
                             owner_ref="owner-beta"), _CRED_A)
        with self.assertRaisesRegex(ParticipationRefused,
                                    "REPLAY_MESSAGE_ID_CONFLICT"):
            gate.route(request(agent_ref="agent-openclaw-like",
                               message_id="msg-alpha-001",
                               body="different content, same id"),
                       recipient(agent_ref="agent-hermes-like",
                                 owner_ref="owner-beta"), _CRED_A)

    def test_journal_capacity_fails_closed(self):
        decisions = {
            "agent-alpha-one": decision(),
            "agent-beta-one": decision(agent_ref="agent-beta-one"),
        }
        bindings = {
            _CRED_ALPHA: {"agentRef": "agent-alpha-one",
                          "tenantRef": "tenant-alpha", "ownerRef": "owner-alpha"},
        }
        gate = RegisteredAgentGate(
            trusted_registration_adapter=synthetic_registration_adapter(decisions),
            trusted_caller_verifier=synthetic_caller_verifier(bindings),
            trusted_lifecycle_source=matching_lifecycle_source(decisions),
            now=lambda: _NOW,
            journal=AdmissionJournal(capacity=1))
        gate.route(request(message_id="msg-alpha-001"), recipient(), _CRED_ALPHA)
        with self.assertRaisesRegex(ObservatoryRefusal,
                                    "ADMISSION_JOURNAL_FULL"):
            gate.route(request(message_id="msg-alpha-002"), recipient(),
                       _CRED_ALPHA)

    def test_journal_capacity_out_of_bounds_at_construction(self):
        for bad in (0, -1, True, "many", gate_module.MAX_JOURNAL_ENTRIES + 1):
            with self.subTest(bad=bad):
                with self.assertRaisesRegex(
                        ObservatoryRefusal,
                        "ADMISSION_JOURNAL_CAPACITY_OUT_OF_BOUNDS"):
                    AdmissionJournal(capacity=bad)
        journal = AdmissionJournal(capacity=gate_module.MAX_JOURNAL_ENTRIES)
        self.assertEqual(journal.capacity, gate_module.MAX_JOURNAL_ENTRIES)

    def _delivery_digest_of(self, gate, req, recipient_context):
        return gate_module._delivery_digest(
            gate_module._request_digest(req),
            {"agentRef": recipient_context["agentRef"],
             "tenantRef": recipient_context["tenantRef"],
             "ownerRef": recipient_context["ownerRef"]})

    def test_export_restore_replays_and_binds_recipient(self):
        """R1-2 — recipient binding survives export/restore both positively
        (same recipient, idempotent) and negatively (new recipient, refused)."""
        gate = rehearsal_gate()
        req = request(agent_ref="agent-openclaw-like")
        hermes_rcpt = recipient(agent_ref="agent-hermes-like", owner_ref="owner-beta")
        gate.route(req, hermes_rcpt, _CRED_A)
        restored = AdmissionJournal.restore(gate.journal.export_state())
        self.assertEqual(len(restored.entries()), 1)
        same_digest = self._delivery_digest_of(gate, req, hermes_rcpt)
        result = restored.check_and_record("msg-alpha-001", same_digest)
        self.assertEqual(result["journalResult"], "replayed-idempotent")
        self.assertEqual(len(restored.entries()), 1)
        other_digest = self._delivery_digest_of(
            gate, req, recipient(agent_ref="agent-openclaw-like"))
        with self.assertRaisesRegex(ParticipationRefused,
                                    "REPLAY_MESSAGE_ID_CONFLICT"):
            restored.check_and_record("msg-alpha-001", other_digest)

    def test_restore_refuses_broken_chain(self):
        gate = rehearsal_gate()
        gate.route(request(agent_ref="agent-openclaw-like"),
                   recipient(agent_ref="agent-hermes-like",
                             owner_ref="owner-beta"), _CRED_A)
        state = gate.journal.export_state()
        state["entries"][0]["digest"] = "0" * 64
        with self.assertRaisesRegex(ObservatoryRefusal,
                                    "ADMISSION_JOURNAL_CHAIN_BROKEN"):
            AdmissionJournal.restore(state)

    def test_restore_refuses_tampered_payload_hash(self):
        gate = rehearsal_gate()
        gate.route(request(agent_ref="agent-openclaw-like"),
                   recipient(agent_ref="agent-hermes-like",
                             owner_ref="owner-beta"), _CRED_A)
        state = gate.journal.export_state()
        state["entries"][0]["deliveryDigest"] = "f" * 64
        with self.assertRaisesRegex(ObservatoryRefusal,
                                    "ADMISSION_JOURNAL_CHAIN_BROKEN"):
            AdmissionJournal.restore(state)

    def test_restore_refuses_foreign_state(self):
        for foreign in (None, [], {"kind": "other-thing"},
                        {"entries": []},
                        "toadaid-a2a-admission-journal"):
            with self.subTest(foreign=foreign):
                with self.assertRaisesRegex(
                        ObservatoryRefusal,
                        "ADMISSION_JOURNAL_STATE_NOT_ADMITTED"):
                    AdmissionJournal.restore(foreign)

    def test_replayed_message_id_in_resigned_state_refused(self):
        # Even a perfectly re-signed chain must be refused when a messageId
        # appears twice: the by-messageId index is part of the journal law,
        # not an implementation detail. (A hash chain authenticates nothing
        # about externally supplied history — restore refuses duplicates.)
        gate = rehearsal_gate()
        gate.route(request(agent_ref="agent-openclaw-like"),
                   recipient(agent_ref="agent-hermes-like",
                             owner_ref="owner-beta"), _CRED_A)
        state = gate.journal.export_state()
        first = state["entries"][0]
        duplicate = {
            "messageId": first["messageId"],
            "deliveryDigest": "f" * 64,
            "prev": first["digest"],
            "digest": _chain_digest(first["messageId"], "f" * 64,
                                    first["digest"]),
        }
        state["entries"].append(duplicate)
        with self.assertRaisesRegex(
                ObservatoryRefusal, "ADMISSION_JOURNAL_CHAIN_BROKEN"):
            AdmissionJournal.restore(state)

    def test_journal_is_metadata_only(self):
        gate = rehearsal_gate()
        secret_request = request(agent_ref="agent-openclaw-like",
                                 body="secret: " + SECRET_TEXT)
        gate.route(secret_request, recipient(agent_ref="agent-hermes-like",
                                             owner_ref="owner-beta"), _CRED_A)
        dumped = json.dumps(gate.journal.export_state())
        self.assertNotIn(SECRET_TEXT, dumped)
        self.assertNotIn("secret: ", dumped)
        for entry in gate.journal.entries():
            self.assertEqual(set(entry),
                             {"messageId", "deliveryDigest", "prev", "digest"})
            self.assertNotIn("message", entry)
            self.assertNotIn("body", entry)


class TenantIsolationTests(unittest.TestCase):
    def _gate(self):
        decisions = {
            "agent-alpha-one": decision(tenant_ref="tenant-alpha"),
            "agent-beta-one": decision(agent_ref="agent-beta-one",
                                       tenant_ref="tenant-beta",
                                       owner_ref="owner-beta"),
        }
        return RegisteredAgentGate(
            trusted_registration_adapter=synthetic_registration_adapter(decisions),
            trusted_caller_verifier=synthetic_caller_verifier({
                _CRED_ALPHA: {"agentRef": "agent-alpha-one",
                              "tenantRef": "tenant-alpha",
                              "ownerRef": "owner-alpha"},
            }),
            trusted_lifecycle_source=matching_lifecycle_source(decisions),
            now=lambda: _NOW)

    def test_cross_tenant_delivery_refused(self):
        gate = self._gate()
        with self.assertRaisesRegex(ParticipationRefused,
                                    "CROSS_TENANT_DELIVERY_REFUSED"):
            gate.route(request(), recipient(
                agent_ref="agent-beta-one", tenant_ref="tenant-beta",
                owner_ref="owner-beta"), _CRED_ALPHA)

    def test_cross_tenant_refusal_writes_no_journal_entry(self):
        gate = self._gate()
        entries_before = len(gate.journal.entries())
        with self.assertRaisesRegex(ParticipationRefused,
                                    "CROSS_TENANT_DELIVERY_REFUSED"):
            gate.route(request(), recipient(
                agent_ref="agent-beta-one", tenant_ref="tenant-beta",
                owner_ref="owner-beta"), _CRED_ALPHA)
        self.assertEqual(len(gate.journal.entries()), entries_before)

    def test_recipient_tenant_mismatch_refused_as_context(self):
        gate = self._gate()
        # Recipient context pretends tenant-alpha, but the adapter decision
        # binds agent-beta-one to tenant-beta -> context mismatch first.
        with self.assertRaisesRegex(ParticipationRefused,
                                    "REGISTRATION_CONTEXT_MISMATCH"):
            gate.route(request(), recipient(agent_ref="agent-beta-one"),
                       _CRED_ALPHA)

    def test_delivery_receipt_binds_both_agents(self):
        gate = rehearsal_gate()
        receipt = gate.route(request(agent_ref="agent-openclaw-like"),
                             recipient(agent_ref="agent-hermes-like",
                                       owner_ref="owner-beta"), _CRED_A)
        self.assertEqual(receipt["senderRef"], "agent-openclaw-like")
        self.assertEqual(receipt["recipientRef"], "agent-hermes-like")
        self.assertEqual(receipt["tenantRef"], "tenant-alpha")
        self.assertEqual(receipt["decision"], "DELIVERED_LOCAL_SYNTHETIC")
        self.assertFalse(any(receipt["authorityFlags"].values()))


class TwoAgentRehearsalTests(unittest.TestCase):
    def test_full_rehearsal_a_to_b_and_back(self):
        gate = rehearsal_gate()
        forward = gate.route(
            request(agent_ref="agent-openclaw-like",
                    message_id="msg-rehearsal-a1",
                    correlation="corr-rehearsal-a1"),
            recipient(agent_ref="agent-hermes-like", owner_ref="owner-beta"),
            _CRED_A)
        self.assertEqual(forward["decision"], "DELIVERED_LOCAL_SYNTHETIC")
        self.assertEqual(forward["senderRef"], "agent-openclaw-like")
        self.assertEqual(forward["recipientRef"], "agent-hermes-like")
        self.assertEqual(forward["framework"], "openclaw")
        self.assertEqual(forward["journalResult"], "recorded")

        backward = gate.route(
            request(agent_ref="agent-hermes-like", owner_ref="owner-beta",
                    message_id="msg-rehearsal-b1",
                    correlation="corr-rehearsal-b1"),
            recipient(agent_ref="agent-openclaw-like", owner_ref="owner-alpha"),
            _CRED_B)
        self.assertEqual(backward["decision"], "DELIVERED_LOCAL_SYNTHETIC")
        self.assertEqual(backward["senderRef"], "agent-hermes-like")
        self.assertEqual(backward["recipientRef"], "agent-openclaw-like")
        self.assertEqual(backward["framework"], "hermes")

    def test_owners_differ_tenant_matches(self):
        gate = rehearsal_gate()
        # owner-alpha's agent can address owner-beta's agent within the
        # same tenant; cross-tenant is separately refused (above).
        receipt = gate.route(request(agent_ref="agent-openclaw-like"),
                             recipient(agent_ref="agent-hermes-like",
                                       owner_ref="owner-beta"), _CRED_A)
        self.assertEqual(receipt["decision"], "DELIVERED_LOCAL_SYNTHETIC")

    def test_authorize_writes_no_journal_entry(self):
        gate = rehearsal_gate()
        gate.authorize(request(agent_ref="agent-openclaw-like"), _CRED_A)
        self.assertEqual(len(gate.journal.entries()), 0)

    def test_revoked_mid_conversation_stops_delivery(self):
        # Same gate, same tenant, but the adapter's decision for B is
        # revoked -> the next delivery refuses even though A was admitted.
        revoked = {
            "agent-openclaw-like": decision(agent_ref="agent-openclaw-like"),
            "agent-hermes-like": decision(agent_ref="agent-hermes-like",
                                          owner_ref="owner-beta",
                                          status="revoked"),
        }
        gate = rehearsal_gate(decisions=revoked)
        with self.assertRaisesRegex(ParticipationRefused,
                                    "REGISTRATION_REVOKED"):
            gate.route(request(agent_ref="agent-openclaw-like"),
                       recipient(agent_ref="agent-hermes-like",
                                 owner_ref="owner-beta"), _CRED_A)
        self.assertEqual(len(gate.journal.entries()), 0)


class ContractTests(unittest.TestCase):
    def test_gate_constants_truthful(self):
        self.assertEqual(gate_module.GATE_KIND,
                         "toadaid-a2a-participation-decision")
        self.assertEqual(gate_module.GATE_STATUS,
                         "LOCAL_SYNTHETIC_ENGINE_NOT_DEPLOYED")
        self.assertIn("NOT_DEPLOYED", gate_module.GATE_STATUS)

    def test_zero_execution_authority_invariant_preserved(self):
        self.assertEqual(
            gate_module.A2A_CHAT_HAS_ZERO_EXECUTION_AUTHORITY,
            "A2A_CHAT_HAS_ZERO_EXECUTION_AUTHORITY")
        self.assertIn("A2A_CHAT_HAS_ZERO_EXECUTION_AUTHORITY",
                      gate_module.__doc__)
        self.assertIn("A2A_CHAT_HAS_ZERO_EXECUTION_AUTHORITY",
                      admission_model.__doc__)

    def test_participation_scopes_are_send_and_receive_only(self):
        self.assertEqual(PARTICIPATION_SCOPES, frozenset({
            "a2a-message-send", "a2a-message-receive"}))
        self.assertEqual(REQUEST_KEYS, frozenset({
            "agentRef", "tenantRef", "ownerRef", "participationScope",
            "messageId", "correlationId", "occurredAtUtc", "message"}))
        self.assertEqual(RECIPIENT_KEYS,
                         frozenset({"agentRef", "tenantRef", "ownerRef"}))

    def test_synthetic_seams_declare_themselves(self):
        self.assertIn("SYNTHETIC OFFLINE ONLY",
                      gate_module.synthetic_registration_adapter.__doc__)
        self.assertIn("SYNTHETIC OFFLINE ONLY",
                      gate_module.synthetic_caller_verifier.__doc__)

    def test_decision_and_receipt_kinds_distinct(self):
        record = decision()
        self.assertEqual(record["kind"], "toadaid-a2a-registration-decision")
        self.assertNotEqual(record["kind"], gate_module.GATE_KIND)


def _chain_digest(message_id, delivery_digest, prev):
    """Chain digest exactly as AdmissionJournal computes it."""
    payload = canonical_json({
        "messageId": message_id,
        "deliveryDigest": delivery_digest,
        "prev": prev,
    }).encode("ascii")
    return hashlib.sha256(payload).hexdigest()


if __name__ == "__main__":
    unittest.main()