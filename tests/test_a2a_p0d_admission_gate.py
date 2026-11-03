"""CUT-A2A-P0D-A1-20261103 — offline adversarial qualification of the
registration-aware A2A participation gate.

Synthetic, stdlib-only, no network, no sockets, no live agents: bounded
model, fail-closed adapter seam, claim forgery refusals, status/evidence
freshness enforcement, participation scoping, replay and restart behavior,
tenant isolation, and the two-agent synthetic rehearsal
(Registered Agent A -> gate -> Registered Agent B). Two-framework fixtures
use descriptive framework labels only — NO actual OpenClaw/Hermes
integration is claimed, wired, or tested. Boundary under test: local
synthetic engine, NOT DEPLOYED, zero execution authority.
"""

import datetime
import json
import unittest

from admission import model as admission_model
from admission import gate as gate_module
from admission.gate import (
    AdmissionJournal,
    AdmissionRefused,
    ParticipationRefused,
    RegisteredAgentGate,
    REQUEST_KEYS,
    RECIPIENT_KEYS,
    synthetic_registration_adapter,
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


def rehearsal_gate():
    """Two-agent synthetic rehearsal gate (framework-neutral).

    Agent A resembles an OpenClaw-registerable external agent; Agent B a
    Hermes-registerable external agent. Framework labels are descriptive
    metadata only — no integration with any real ecosystem is claimed or
    wired. The two agents hold different owners inside one tenant.
    """
    decisions = {
        "agent-openclaw-like": decision(
            agent_ref="agent-openclaw-like",
            tenant_ref="tenant-alpha", owner_ref="owner-alpha",
            framework="openclaw"),
        "agent-hermes-like": decision(
            agent_ref="agent-hermes-like",
            tenant_ref="tenant-alpha", owner_ref="owner-beta",
            framework="hermes"),
    }
    return RegisteredAgentGate(
        trusted_registration_adapter=synthetic_registration_adapter(decisions),
        now=lambda: _NOW,
    )


class DecisionModelTests(unittest.TestCase):
    def test_decision_binds_every_required_field(self):
        record = decision()
        self.assertEqual(set(record), set(admission_model.DECISION_KEYS))
        self.assertTrue(all(record["authorityFlags"].values()) is False)
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

    def test_scopes_sorted_and_independent(self):
        record = decision(scopes=("a2a-message-receive",))
        self.assertEqual(record["participationScopes"], ["a2a-message-receive"])
        # The model sorts and de-duplicates: the record shape is canonical
        # regardless of the order the adapter supplies.
        record = decision(scopes=("a2a-message-receive", "a2a-message-send"))
        self.assertEqual(record["participationScopes"],
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


class GateFailClosedTests(unittest.TestCase):
    def test_default_gate_refuses_everything(self):
        gate = RegisteredAgentGate()
        with self.assertRaisesRegex(ParticipationRefused,
                                    "ADMISSION_AUTHORIZATION_REQUIRED"):
            gate.authorize(request())
        with self.assertRaisesRegex(ParticipationRefused,
                                    "ADMISSION_AUTHORIZATION_REQUIRED"):
            gate.route(request(), recipient())

    def test_missing_clock_refused(self):
        adapter = synthetic_registration_adapter({"agent-alpha-one": decision()})
        gate = RegisteredAgentGate(trusted_registration_adapter=adapter)
        with self.assertRaisesRegex(ParticipationRefused,
                                    "CLOCK_SOURCE_REQUIRED"):
            gate.authorize(request())

    def test_non_callable_and_bad_clock_refused(self):
        adapter = synthetic_registration_adapter({"agent-alpha-one": decision()})
        for bad_clock in (42, "stamp", lambda: "not-a-datetime"):
            gate = RegisteredAgentGate(
                trusted_registration_adapter=adapter, now=bad_clock)
            with self.assertRaisesRegex(ParticipationRefused,
                                        "CLOCK_SOURCE_REQUIRED"):
                gate.authorize(request())

    def test_aware_clock_normalized(self):
        adapter = synthetic_registration_adapter({"agent-alpha-one": decision()})
        aware = datetime.datetime(
            2026, 11, 3, 12, 0, 0, tzinfo=datetime.timezone.utc)
        gate = RegisteredAgentGate(
            trusted_registration_adapter=adapter, now=lambda: aware)
        receipt = gate.authorize(request())
        self.assertEqual(receipt["decision"], "AUTHORIZED_LOCAL_SYNTHETIC")

    def test_adapter_returning_none_refused(self):
        gate = RegisteredAgentGate(
            trusted_registration_adapter=synthetic_registration_adapter({}),
            now=lambda: _NOW)
        with self.assertRaisesRegex(ParticipationRefused,
                                    "REGISTRATION_NOT_FOUND"):
            gate.authorize(request())

    def test_adapter_returning_foreign_shape_refused(self):
        # An adapter record carrying an extra field dies at the exact-key
        # tamper guard before anything else happens.
        broken_extra = {**decision(), "claimedOnline": True}
        gate = RegisteredAgentGate(
            trusted_registration_adapter=synthetic_registration_adapter(
                {"agent-alpha-one": broken_extra}),
            now=lambda: _NOW)
        with self.assertRaisesRegex(ParticipationRefused,
                                    "REGISTRATION_DECISION_TAMPERED"):
            gate.authorize(request())

    def test_malformed_adapter_record_fails_closed(self):
        # A malformed adapter record (invalid field value) is refused by the
        # decision builder — no partial admission, no default-to-allow.
        broken = {**decision(), "framework": "bogus-framework"}
        gate = RegisteredAgentGate(
            trusted_registration_adapter=synthetic_registration_adapter(
                {"agent-alpha-one": broken}),
            now=lambda: _NOW)
        with self.assertRaisesRegex(ObservatoryRefusal,
                                    "FRAMEWORK_NOT_ADMITTED"):
            gate.authorize(request())

    def test_flipped_authority_flag_never_survives_rebuild(self):
        record = decision()
        forged = dict(record)
        forged["authorityFlags"] = dict(record["authorityFlags"])
        forged["authorityFlags"]["executionAuthorized"] = True
        gate = RegisteredAgentGate(
            trusted_registration_adapter=synthetic_registration_adapter(
                {"agent-alpha-one": forged}),
            now=lambda: _NOW)
        with self.assertRaisesRegex(ParticipationRefused,
                                    "REGISTRATION_DECISION_TAMPERED"):
            gate.authorize(request())


class StatusAndFreshnessTests(unittest.TestCase):
    def _gate_for_status(self, status):
        adapter = synthetic_registration_adapter(
            {"agent-alpha-one": decision(status=status)})
        return RegisteredAgentGate(
            trusted_registration_adapter=adapter, now=lambda: _NOW)

    def test_registered_admitted(self):
        receipt = self._gate_for_status("registered").authorize(request())
        self.assertEqual(receipt["decision"], "AUTHORIZED_LOCAL_SYNTHETIC")

    def test_revoked_refused(self):
        with self.assertRaisesRegex(ParticipationRefused,
                                    "REGISTRATION_REVOKED"):
            self._gate_for_status("revoked").authorize(request())

    def test_suspended_refused(self):
        with self.assertRaisesRegex(ParticipationRefused,
                                    "REGISTRATION_SUSPENDED"):
            self._gate_for_status("suspended").authorize(request())

    def test_unregistered_refused(self):
        with self.assertRaisesRegex(ParticipationRefused,
                                    "REGISTRATION_UNREGISTERED"):
            self._gate_for_status("unregistered").authorize(request())

    def test_unknown_status_refused(self):
        with self.assertRaisesRegex(ParticipationRefused,
                                    "REGISTRATION_UNKNOWN_STATUS"):
            self._gate_for_status("unknown").authorize(request())

    def test_expired_evidence_refused(self):
        # Evidence expired between observation and the gate's clock.
        adapter = synthetic_registration_adapter(
            {"agent-alpha-one": decision(expires="2026-11-03T11:00:00Z")})
        gate = RegisteredAgentGate(
            trusted_registration_adapter=adapter, now=lambda: _NOW)
        with self.assertRaisesRegex(ParticipationRefused,
                                    "REGISTRATION_EVIDENCE_EXPIRED"):
            gate.authorize(request())

    def test_expiry_boundary_is_inclusive(self):
        # Evidence expiring exactly at the gate's clock instant is already
        # unusable for a fresh admission decision (<= means expired).
        adapter = synthetic_registration_adapter(
            {"agent-alpha-one": decision(expires="2026-11-03T12:00:00Z")})
        gate = RegisteredAgentGate(
            trusted_registration_adapter=adapter, now=lambda: _NOW)
        with self.assertRaisesRegex(ParticipationRefused,
                                    "REGISTRATION_EVIDENCE_EXPIRED"):
            gate.authorize(request())

    def test_one_second_of_headroom_admits(self):
        adapter = synthetic_registration_adapter(
            {"agent-alpha-one": decision(expires="2026-11-03T12:00:01Z")})
        gate = RegisteredAgentGate(
            trusted_registration_adapter=adapter, now=lambda: _NOW)
        receipt = gate.authorize(request())
        self.assertEqual(receipt["decision"], "AUTHORIZED_LOCAL_SYNTHETIC")


class ClaimForgeryTests(unittest.TestCase):
    """A registration claim from an Agent Card, a message body, a browser,
    or raw request keys NEVER authorizes: the request schema carries no
    claim fields at all, so every forgery dies as a shape refusal."""

    def test_agent_card_claim_never_authorizes(self):
        forged = request()
        forged["claimedRegistration"] = {
            "registrationStatus": "registered",
            "credentialGeneration": 9,
            "revocationEpoch": 0,
            "framework": "openclaw",
        }
        gate = RegisteredAgentGate(now=lambda: _NOW)
        with self.assertRaisesRegex(AdmissionRefused,
                                    "REQUEST_KEYS_NOT_ADMITTED"):
            gate.authorize(forged)

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
                    gate.authorize(forged)
                self.assertEqual(len(gate.journal.entries()), 0)

    def test_message_body_claim_cannot_replace_registration(self):
        # The body may contain any text — including convincing registration
        # claims — but only the trusted adapter decides; the body is never
        # read for authority. Agent "agent-stranger-9" holds no decision.
        forged_body = json.dumps({
            "a2aRegistration": {
                "agentRef": "agent-stranger-9",
                "registrationStatus": "registered",
                "participationScopes": ["a2a-message-send",
                                        "a2a-message-receive"],
            }
        }, sort_keys=True)
        gate = rehearsal_gate()
        with self.assertRaisesRegex(ParticipationRefused,
                                    "REGISTRATION_NOT_FOUND"):
            gate.authorize(request(
                agent_ref="agent-stranger-9", body=forged_body[:200]))

    def test_claiming_another_tenant_refused(self):
        # An agent registered under tenant-alpha cannot reuse its decision
        # from a tenant-gamma context.
        adapter = synthetic_registration_adapter(
            {"agent-alpha-one": decision(tenant_ref="tenant-alpha")})
        gate = RegisteredAgentGate(
            trusted_registration_adapter=adapter, now=lambda: _NOW)
        with self.assertRaisesRegex(ParticipationRefused,
                                    "REGISTRATION_CONTEXT_MISMATCH"):
            gate.authorize(request(tenant_ref="tenant-gamma"))

    def test_claiming_another_owner_refused(self):
        adapter = synthetic_registration_adapter(
            {"agent-alpha-one": decision(owner_ref="owner-alpha")})
        gate = RegisteredAgentGate(
            trusted_registration_adapter=adapter, now=lambda: _NOW)
        with self.assertRaisesRegex(ParticipationRefused,
                                    "REGISTRATION_CONTEXT_MISMATCH"):
            gate.authorize(request(owner_ref="owner-impostor"))

    def test_admitted_receipt_carries_zero_authority(self):
        gate = rehearsal_gate()
        receipt = gate.authorize(request(agent_ref="agent-openclaw-like"))
        self.assertEqual(set(receipt["authorityFlags"]), _ALL_AUTHORITY_FLAGS)
        self.assertFalse(any(receipt["authorityFlags"].values()))
        self.assertEqual(receipt["boundary"],
                         gate_module.A2A_CHAT_HAS_ZERO_EXECUTION_AUTHORITY)


class ParticipationScopeTests(unittest.TestCase):
    def test_send_scope_required_for_authorize(self):
        # Registered, current, but send never granted.
        adapter = synthetic_registration_adapter(
            {"agent-alpha-one": decision(scopes=("a2a-message-receive",))})
        gate = RegisteredAgentGate(
            trusted_registration_adapter=adapter, now=lambda: _NOW)
        with self.assertRaisesRegex(ParticipationRefused,
                                    "PARTICIPATION_SCOPE_NOT_AUTHORIZED"):
            gate.authorize(request())

    def test_receive_scope_required_for_recipient(self):
        adapter = synthetic_registration_adapter({
            "agent-alpha-one": decision(),
            "agent-beta-one": decision(agent_ref="agent-beta-one",
                                       scopes=("a2a-message-send",)),
        })
        gate = RegisteredAgentGate(
            trusted_registration_adapter=adapter, now=lambda: _NOW)
        with self.assertRaisesRegex(ParticipationRefused,
                                    "PARTICIPATION_SCOPE_NOT_AUTHORIZED"):
            gate.route(request(), recipient())

    def test_unknown_scope_shape_refused(self):
        gate = rehearsal_gate()
        with self.assertRaisesRegex(AdmissionRefused,
                                    "PARTICIPATION_SCOPE_NOT_ADMITTED"):
            gate.authorize(request(
                agent_ref="agent-openclaw-like",
                participation_scope="a2a-message-run-tools"))

    def test_route_requires_both_sides_registered(self):
        gate = rehearsal_gate()
        with self.assertRaisesRegex(ParticipationRefused,
                                    "REGISTRATION_NOT_FOUND"):
            gate.route(request(agent_ref="agent-openclaw-like"),
                       recipient(agent_ref="agent-unregistered-1"))


class RequestShapeTests(unittest.TestCase):
    def test_non_dict_refused(self):
        gate = rehearsal_gate()
        for bad in (None, [], "request", b"bytes"):
            with self.subTest(bad=bad):
                with self.assertRaisesRegex(AdmissionRefused,
                                            "REQUEST_SHAPE_INVALID"):
                    gate.authorize(bad)

    def test_exact_request_keys_enforced(self):
        gate = rehearsal_gate()
        for delta in ({"extraClaim": "x"},):
            forged = {**request(), **delta}
            with self.assertRaisesRegex(AdmissionRefused,
                                        "REQUEST_KEYS_NOT_ADMITTED"):
                gate.authorize(forged)
        missing = request()
        missing.pop("correlationId")
        with self.assertRaisesRegex(AdmissionRefused,
                                    "REQUEST_KEYS_NOT_ADMITTED"):
            gate.authorize(missing)

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
                    gate.authorize(bad)
        bad = request()
        bad["messageId"] = 7
        with self.assertRaisesRegex(AdmissionRefused,
                                    "REQUEST_MESSAGEID_NOT_ADMITTED"):
            gate.authorize(bad)

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
                    gate.authorize(bad)
        bad = dict(base)
        bad["message"] = {"messageType": "email", "body": "x"}
        with self.assertRaisesRegex(AdmissionRefused,
                                    "MESSAGE_TYPE_NOT_ADMITTED"):
            gate.authorize(bad)
        bad = dict(base)
        bad["message"] = {"messageType": "conversation_message", "body": ""}
        with self.assertRaisesRegex(AdmissionRefused,
                                    "MESSAGE_BODY_NOT_ADMITTED"):
            gate.authorize(bad)
        bad = dict(base)
        bad["message"] = {"messageType": "conversation_message",
                          "body": "y" * 257}
        with self.assertRaisesRegex(AdmissionRefused,
                                    "MESSAGE_BODY_NOT_ADMITTED"):
            gate.authorize(bad)

    def test_timestamp_shape_and_bounds(self):
        gate = rehearsal_gate()
        for occurred in ("2026-13-01T00:00:00Z", "nope", 1730600000,
                         "2026-02-30T00:00:00Z"):
            with self.subTest(occurred=occurred):
                with self.assertRaisesRegex(AdmissionRefused,
                                            "REQUEST_TIMESTAMP_NOT_ADMITTED"):
                    gate.authorize(request(occurred=occurred))

    def test_recipient_context_strictly_shaped(self):
        gate = rehearsal_gate()
        for bad in (None, "agent-hermes-like", {"agentRef": "agent-hermes-like"},
                    {"agentRef": "agent-hermes-like", "tenantRef": "tenant-alpha"},
                    dict(recipient(), extraClaim=True)):
            with self.subTest(bad=bad):
                with self.assertRaisesRegex(
                        AdmissionRefused, "RECIPIENT_KEYS_NOT_ADMITTED"):
                    gate.route(request(agent_ref="agent-openclaw-like"), bad)
        bad = recipient(agent_ref="Agent-Hermes")
        with self.assertRaisesRegex(AdmissionRefused,
                                    "RECIPIENT_REF_NOT_ADMITTED"):
            gate.route(request(agent_ref="agent-openclaw-like"), bad)

    def test_self_delivery_refused(self):
        gate = rehearsal_gate()
        with self.assertRaisesRegex(AdmissionRefused,
                                    "SELF_DELIVERY_NOT_ADMITTED"):
            gate.route(request(agent_ref="agent-openclaw-like"),
                       recipient(agent_ref="agent-openclaw-like",
                                 owner_ref="owner-alpha"))


class ReplayAndRestartTests(unittest.TestCase):
    def test_identical_replay_is_idempotent(self):
        gate = rehearsal_gate()
        req = request(agent_ref="agent-openclaw-like")
        first = gate.route(req, recipient(agent_ref="agent-hermes-like",
                                          owner_ref="owner-beta"))
        second = gate.route(req, recipient(agent_ref="agent-hermes-like",
                                           owner_ref="owner-beta"))
        self.assertEqual(first["journalResult"], "recorded")
        self.assertEqual(second["journalResult"], "replayed-idempotent")
        self.assertEqual(len(gate.journal.entries()), 1)

    def test_conflicting_replay_refused(self):
        gate = rehearsal_gate()
        gate.route(request(agent_ref="agent-openclaw-like",
                           message_id="msg-alpha-001"),
                   recipient(agent_ref="agent-hermes-like",
                             owner_ref="owner-beta"))
        with self.assertRaisesRegex(ParticipationRefused,
                                    "REPLAY_MESSAGE_ID_CONFLICT"):
            gate.route(request(agent_ref="agent-openclaw-like",
                               message_id="msg-alpha-001",
                               body="different content, same id"),
                       recipient(agent_ref="agent-hermes-like",
                                 owner_ref="owner-beta"))

    def test_journal_capacity_fails_closed(self):
        gate = RegisteredAgentGate(
            trusted_registration_adapter=synthetic_registration_adapter({
                "agent-alpha-one": decision(),
                "agent-beta-one": decision(agent_ref="agent-beta-one"),
            }),
            now=lambda: _NOW,
            journal=AdmissionJournal(capacity=1))
        gate.route(request(message_id="msg-alpha-001"), recipient())
        with self.assertRaisesRegex(ObservatoryRefusal,
                                    "ADMISSION_JOURNAL_FULL"):
            gate.route(request(message_id="msg-alpha-002"), recipient())

    def test_journal_capacity_out_of_bounds_at_construction(self):
        for bad in (0, -1, True, "many", gate_module.MAX_JOURNAL_ENTRIES + 1):
            with self.subTest(bad=bad):
                with self.assertRaisesRegex(
                        ObservatoryRefusal,
                        "ADMISSION_JOURNAL_CAPACITY_OUT_OF_BOUNDS"):
                    AdmissionJournal(capacity=bad)
        journal = AdmissionJournal(capacity=gate_module.MAX_JOURNAL_ENTRIES)
        self.assertEqual(journal.capacity, gate_module.MAX_JOURNAL_ENTRIES)

    def test_export_restore_replays_without_duplicate_entry(self):
        gate = rehearsal_gate()
        req = request(agent_ref="agent-openclaw-like")
        gate.route(req, recipient(agent_ref="agent-hermes-like", owner_ref="owner-beta"))
        state = gate.journal.export_state()
        restored = AdmissionJournal.restore(state)
        self.assertEqual(len(restored.entries()), 1)
        result = restored.check_and_record(
            "msg-alpha-001", gate_module._request_digest(req))
        self.assertEqual(result["journalResult"], "replayed-idempotent")
        self.assertEqual(len(restored.entries()), 1)

    def test_restore_refuses_broken_chain(self):
        gate = rehearsal_gate()
        gate.route(request(agent_ref="agent-openclaw-like"),
                   recipient(agent_ref="agent-hermes-like", owner_ref="owner-beta"))
        state = gate.journal.export_state()
        state["entries"][0]["digest"] = "0" * 64
        with self.assertRaisesRegex(ObservatoryRefusal,
                                    "ADMISSION_JOURNAL_CHAIN_BROKEN"):
            AdmissionJournal.restore(state)

    def test_restore_refuses_tampered_payload_hash(self):
        gate = rehearsal_gate()
        gate.route(request(agent_ref="agent-openclaw-like"),
                   recipient(agent_ref="agent-hermes-like", owner_ref="owner-beta"))
        state = gate.journal.export_state()
        state["entries"][0]["requestDigest"] = "f" * 64
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
        # not an implementation detail.
        gate = rehearsal_gate()
        gate.route(request(agent_ref="agent-openclaw-like"),
                   recipient(agent_ref="agent-hermes-like", owner_ref="owner-beta"))
        state = gate.journal.export_state()
        first = state["entries"][0]
        duplicate = {
            "messageId": first["messageId"],
            "requestDigest": "f" * 64,
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
        gate.route(secret_request, recipient(agent_ref="agent-hermes-like", owner_ref="owner-beta"))
        dumped = json.dumps(gate.journal.export_state())
        self.assertNotIn(SECRET_TEXT, dumped)
        self.assertNotIn("secret: ", dumped)
        for entry in gate.journal.entries():
            self.assertEqual(len(entry), 4)
            self.assertEqual(set(entry),
                             {"messageId", "requestDigest", "prev", "digest"})
            self.assertNotIn("message", entry)
            self.assertNotIn("body", entry)


class TenantIsolationTests(unittest.TestCase):
    def _gate(self):
        adapter = synthetic_registration_adapter({
            "agent-alpha-one": decision(tenant_ref="tenant-alpha"),
            "agent-beta-one": decision(agent_ref="agent-beta-one",
                                       tenant_ref="tenant-beta",
                                       owner_ref="owner-beta"),
        })
        return RegisteredAgentGate(
            trusted_registration_adapter=adapter, now=lambda: _NOW)

    def test_cross_tenant_delivery_refused(self):
        gate = self._gate()
        with self.assertRaisesRegex(ParticipationRefused,
                                    "CROSS_TENANT_DELIVERY_REFUSED"):
            gate.route(request(), recipient(
                agent_ref="agent-beta-one", tenant_ref="tenant-beta",
                owner_ref="owner-beta"))

    def test_cross_tenant_refusal_writes_no_journal_entry(self):
        gate = self._gate()
        entries_before = len(gate.journal.entries())
        with self.assertRaisesRegex(ParticipationRefused,
                                    "CROSS_TENANT_DELIVERY_REFUSED"):
            gate.route(request(), recipient(
                agent_ref="agent-beta-one", tenant_ref="tenant-beta",
                owner_ref="owner-beta"))
        self.assertEqual(len(gate.journal.entries()), entries_before)

    def test_recipient_tenant_mismatch_refused_as_context(self):
        gate = self._gate()
        # Recipient context pretends tenant-alpha, but the adapter decision
        # binds agent-beta-one to tenant-beta -> context mismatch first.
        with self.assertRaisesRegex(ParticipationRefused,
                                    "REGISTRATION_CONTEXT_MISMATCH"):
            gate.route(request(), recipient(agent_ref="agent-beta-one"))

    def test_delivery_receipt_binds_both_agents(self):
        gate = rehearsal_gate()
        receipt = gate.route(request(agent_ref="agent-openclaw-like"),
                             recipient(agent_ref="agent-hermes-like",
                                       owner_ref="owner-beta"))
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
            recipient(agent_ref="agent-hermes-like", owner_ref="owner-beta"))
        self.assertEqual(forward["decision"], "DELIVERED_LOCAL_SYNTHETIC")
        self.assertEqual(forward["senderRef"], "agent-openclaw-like")
        self.assertEqual(forward["recipientRef"], "agent-hermes-like")
        self.assertEqual(forward["framework"], "openclaw")
        self.assertEqual(forward["journalResult"], "recorded")

        backward = gate.route(
            request(agent_ref="agent-hermes-like", owner_ref="owner-beta",
                    message_id="msg-rehearsal-b1",
                    correlation="corr-rehearsal-b1"),
            recipient(agent_ref="agent-openclaw-like",
                      owner_ref="owner-alpha"))
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
                                       owner_ref="owner-beta"))
        self.assertEqual(receipt["decision"], "DELIVERED_LOCAL_SYNTHETIC")

    def test_authorize_writes_no_journal_entry(self):
        gate = rehearsal_gate()
        gate.authorize(request(agent_ref="agent-openclaw-like"))
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
        gate = RegisteredAgentGate(
            trusted_registration_adapter=synthetic_registration_adapter(revoked),
            now=lambda: _NOW)
        with self.assertRaisesRegex(ParticipationRefused,
                                    "REGISTRATION_REVOKED"):
            gate.route(request(agent_ref="agent-openclaw-like"),
                       recipient(agent_ref="agent-hermes-like",
                                 owner_ref="owner-beta"))
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

    def test_decision_and_receipt_kinds_distinct(self):
        record = decision()
        self.assertEqual(record["kind"], "toadaid-a2a-registration-decision")
        self.assertNotEqual(record["kind"], gate_module.GATE_KIND)


def _chain_digest(message_id, request_digest, prev):
    """Chain digest exactly as AdmissionJournal computes it."""
    import hashlib
    payload = canonical_json({
        "messageId": message_id,
        "requestDigest": request_digest,
        "prev": prev,
    }).encode("ascii")
    return hashlib.sha256(payload).hexdigest()


if __name__ == "__main__":
    unittest.main()