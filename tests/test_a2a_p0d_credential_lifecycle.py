"""CUT-A2A-P0D-A2-20261103 — offline adversarial qualification of the
trusted credential-lifecycle lifecycle seam.

Synthetic, stdlib-only, no network, no sockets, no live agents. Boundary
under test: CURRENT credential-lifecycle enforcement (P0D-A2) on top of
the P0D-A1 registered-agent gate — a registration decision carrying
credentialGeneration/revocationEpoch does NOT prove those values are
current, and no agent-supplied claim can establish its own state.
Constitutional rule under test: REVOCATION_OVERRIDES_PRIOR_APPROVAL.
NOT DEPLOYED; zero execution authority throughout.
"""

import admission
import copy
import datetime
import json
import unittest

import admission.lifecycle
from admission import gate as gate_module
from admission.gate import (
    AdmissionJournal,
    ParticipationRefused,
    RegisteredAgentGate,
    synthetic_caller_credential,
    synthetic_caller_verifier,
    synthetic_registration_adapter,
)
from admission.lifecycle import (
    LIFECYCLE_KIND,
    LIFECYCLE_STATE_KEYS,
    LIFECYCLE_STATUSES,
    MAX_LIFECYCLE_COUNTER,
    build_lifecycle_state,
    synthetic_lifecycle_source,
)
from admission.model import build_registration_decision
from observatory.model import ObservatoryRefusal

_NOW = datetime.datetime(2026, 11, 3, 12, 0, 0)
_OBSERVED = "2026-11-03T11:59:00Z"  # fresh per P0D-A2/R1 policy (60 s before _NOW)

_ALL_AUTHORITY_FLAGS = {
    "executionAuthorized", "toolUseAuthorized", "paymentAuthorized",
    "deploymentAuthorized", "agentRegistrationChangeAuthorized",
    "publicDirectoryExposed",
}


def decision(agent_ref="agent-alpha-one", tenant_ref="tenant-alpha",
             owner_ref="owner-alpha", status="registered",
             generation=2, epoch=1, scopes=("a2a-message-send",
                                            "a2a-message-receive")):
    return build_registration_decision(
        agent_ref=agent_ref,
        owner_ref=owner_ref,
        tenant_ref=tenant_ref,
        registration_status=status,
        credential_generation=generation,
        revocation_epoch=epoch,
        framework="unspecified",
        adapter_id="synthetic-offline-registration-adapter",
        decision_observed_at_utc=_OBSERVED,
        evidence_expires_at_utc="2026-11-04T10:00:00Z",
        participation_scopes=scopes,
    )


def lifecycle(agent_ref="agent-alpha-one", tenant_ref="tenant-alpha",
              owner_ref="owner-alpha", status="registered",
              generation=2, epoch=1, observed=_OBSERVED):
    return build_lifecycle_state(
        agent_ref=agent_ref,
        owner_ref=owner_ref,
        tenant_ref=tenant_ref,
        lifecycle_status=status,
        current_credential_generation=generation,
        current_revocation_epoch=epoch,
        observed_at_utc=observed,
    )


def mutable_lifecycle_source(states):
    """SYNTHETIC live source over a test-owned dict — tests mutate it to
    rotate / revoke / suspend / disable agents BETWEEN admissions, which
    is exactly the attack surface this seam exists for."""
    return lambda query: copy.deepcopy(states.get(query["agentRef"]))


_UNSET = object()


def single_party(lifecycle_source=_UNSET):
    """One registered sender, one matching caller credential.

    Returns (gate, credential, states, decisions). The decisions and
    states dicts are LIVE: tests may mutate them between admissions.
    Passing lifecycle_source=None or a non-callable injects exactly that
    broken seam (fail-closed on purpose).
    """
    cred = synthetic_caller_credential("fixture-lifecycle-alpha")
    decisions = {"agent-alpha-one": decision()}
    states = {"agent-alpha-one": lifecycle()}
    gate = RegisteredAgentGate(
        trusted_registration_adapter=synthetic_registration_adapter(decisions),
        trusted_caller_verifier=synthetic_caller_verifier({
            cred: {"agentRef": "agent-alpha-one", "tenantRef": "tenant-alpha",
                   "ownerRef": "owner-alpha"},
        }),
        trusted_lifecycle_source=mutable_lifecycle_source(states)
        if lifecycle_source is _UNSET else lifecycle_source,
        now=lambda: _NOW,
    )
    return gate, cred, states, decisions


def request(agent_ref="agent-alpha-one", tenant_ref="tenant-alpha",
            owner_ref="owner-alpha", participation_scope="a2a-message-send",
            message_id="msg-lc-001", correlation="corr-lc-001",
            body="bounded lifecycle adversarial message"):
    return {
        "agentRef": agent_ref,
        "tenantRef": tenant_ref,
        "ownerRef": owner_ref,
        "participationScope": participation_scope,
        "messageId": message_id,
        "correlationId": correlation,
        "occurredAtUtc": "2026-11-03T12:00:00Z",
        "message": {"messageType": "conversation_message", "body": body},
    }


def recipient(agent_ref="agent-beta-one", tenant_ref="tenant-alpha",
              owner_ref="owner-beta"):
    return {"agentRef": agent_ref, "tenantRef": tenant_ref,
            "ownerRef": owner_ref}


def two_party():
    """Sender agent-alpha-one (owner-alpha) -> recipient agent-beta-one
    (owner-beta) in shared tenant-alpha. Both sides get independently
    CURRENT trusted lifecycle state. Returns
    (gate, sender_cred, states, decisions)."""
    cred = synthetic_caller_credential("fixture-lifecycle-alpha")
    decisions = {
        "agent-alpha-one": decision(),
        "agent-beta-one": decision(agent_ref="agent-beta-one",
                                   owner_ref="owner-beta"),
    }
    states = {
        "agent-alpha-one": lifecycle(),
        "agent-beta-one": lifecycle(agent_ref="agent-beta-one",
                                    owner_ref="owner-beta"),
    }
    gate = RegisteredAgentGate(
        trusted_registration_adapter=synthetic_registration_adapter(decisions),
        trusted_caller_verifier=synthetic_caller_verifier({
            cred: {"agentRef": "agent-alpha-one", "tenantRef": "tenant-alpha",
                   "ownerRef": "owner-alpha"},
        }),
        trusted_lifecycle_source=mutable_lifecycle_source(states),
        now=lambda: _NOW,
    )
    return gate, cred, states, decisions


class LifecycleModelTests(unittest.TestCase):
    def test_state_binds_every_required_field(self):
        record = lifecycle()
        self.assertEqual(set(record), LIFECYCLE_STATE_KEYS)
        self.assertEqual(record["kind"], "toadaid-a2a-credential-lifecycle-state")
        self.assertFalse(any([
            record["lifecycleStatus"] not in LIFECYCLE_STATUSES,
            record["currentCredentialGeneration"] < 0,
            record["currentRevocationEpoch"] < 0,
        ]))

    def test_status_vocabulary_is_closed(self):
        # registered admits; suspended, revoked, and EMERGENCY DISABLEMENT
        # refuse; nothing else exists.
        self.assertEqual(LIFECYCLE_STATUSES,
                         frozenset({"registered", "suspended", "revoked",
                                    "disabled"}))

    def test_no_kwargs_smuggling(self):
        with self.assertRaises(TypeError):
            build_lifecycle_state(
                **lifecycle(), claimedCurrent=True, agentAttested=True)

    def test_refusals_at_construction(self):
        cases = (
            ({"agent_ref": "Agent-Bad-Ref"},
             "LIFECYCLE_STATE_AGENT_REF_NOT_ADMITTED"),
            ({"agent_ref": 7}, "LIFECYCLE_STATE_AGENT_REF_NOT_ADMITTED"),
            ({"owner_ref": "ab"}, "LIFECYCLE_STATE_OWNER_REF_NOT_ADMITTED"),
            ({"tenant_ref": "tenant_bad"},
             "LIFECYCLE_STATE_TENANT_REF_NOT_ADMITTED"),
            ({"status": "online"}, "LIFECYCLE_STATUS_NOT_ADMITTED"),
            ({"status": ["registered"]}, "LIFECYCLE_STATUS_NOT_ADMITTED"),
            ({"status": {"registered": True}}, "LIFECYCLE_STATUS_NOT_ADMITTED"),
            ({"status": None}, "LIFECYCLE_STATUS_NOT_ADMITTED"),
            ({"generation": "2"}, "LIFECYCLE_GENERATION_NOT_ADMITTED"),
            ({"generation": True}, "LIFECYCLE_GENERATION_NOT_ADMITTED"),
            ({"generation": -1}, "LIFECYCLE_GENERATION_NOT_ADMITTED"),
            ({"generation": MAX_LIFECYCLE_COUNTER + 1},
             "LIFECYCLE_GENERATION_NOT_ADMITTED"),
            ({"epoch": "1"}, "LIFECYCLE_REVOCATION_EPOCH_NOT_ADMITTED"),
            ({"epoch": True}, "LIFECYCLE_REVOCATION_EPOCH_NOT_ADMITTED"),
            ({"epoch": -3}, "LIFECYCLE_REVOCATION_EPOCH_NOT_ADMITTED"),
            ({"observed": "2026-02-30T10:00:00Z"},
             "LIFECYCLE_OBSERVED_AT_NOT_ADMITTED"),
            ({"observed": "2026-13-01T10:00:00Z"},
             "LIFECYCLE_OBSERVED_AT_NOT_ADMITTED"),
            ({"observed": "not-a-stamp"},
             "LIFECYCLE_OBSERVED_AT_NOT_ADMITTED"),
            ({"observed": 5}, "LIFECYCLE_OBSERVED_AT_NOT_ADMITTED"),
            ({"observed": "Z" * 257}, "LIFECYCLE_OBSERVED_AT_NOT_ADMITTED"),
        )
        for kwargs, code in cases:
            with self.subTest(code=code, kwargs=kwargs):
                with self.assertRaisesRegex(ObservatoryRefusal, code):
                    lifecycle(**kwargs)


class LifecycleSourceTests(unittest.TestCase):
    def test_source_declares_itself_synthetic(self):
        self.assertIn("SYNTHETIC OFFLINE ONLY",
                      synthetic_lifecycle_source.__doc__)

    def test_factory_shape_and_key_checks(self):
        with self.assertRaisesRegex(ObservatoryRefusal,
                                    "LIFECYCLE_SOURCE_STATES_SHAPE_INVALID"):
            synthetic_lifecycle_source(["not-a-dict"])
        with self.assertRaisesRegex(ObservatoryRefusal,
                                    "LIFECYCLE_SOURCE_KEY_MISMATCH"):
            synthetic_lifecycle_source({"agent-alpha-one":
                                        lifecycle(agent_ref="agent-other-1")})
        with self.assertRaisesRegex(ObservatoryRefusal,
                                    "LIFECYCLE_SOURCE_KEY_NOT_ADMITTED"):
            synthetic_lifecycle_source({"Bad Key": lifecycle()})
        for broken, code in (
            (None, "LIFECYCLE_STATE_SHAPE_INVALID"),
            ([lifecycle()], "LIFECYCLE_STATE_SHAPE_INVALID"),
            ("state", "LIFECYCLE_STATE_SHAPE_INVALID"),
            ({"kind": "forged-kind", **{k: v for k, v in lifecycle().items()
              if k != "kind"}}, "LIFECYCLE_STATE_KIND_INVALID"),
            ({**lifecycle(), "extraClaim": True},
             "LIFECYCLE_STATE_SHAPE_INVALID"),
            ({k: v for k, v in lifecycle().items() if k != "lifecycleStatus"},
             "LIFECYCLE_STATE_SHAPE_INVALID"),
        ):
            with self.subTest(code=code, broken=str(broken)[:40]):
                with self.assertRaisesRegex(ObservatoryRefusal, code):
                    synthetic_lifecycle_source({"agent-alpha-one": broken})

    def test_source_returns_independent_copies(self):
        source = synthetic_lifecycle_source({"agent-alpha-one": lifecycle()})
        first = source({"agentRef": "agent-alpha-one", "tenantRef":
                        "tenant-alpha", "ownerRef": "owner-alpha"})
        first["lifecycleStatus"] = "revoked"
        second = source({"agentRef": "agent-alpha-one", "tenantRef":
                         "tenant-alpha", "ownerRef": "owner-alpha"})
        self.assertEqual(second["lifecycleStatus"], "registered")

    def test_no_trusted_source_refuses_everything(self):
        # No state source means refusal — for authorize AND route.
        gate, cred, _, _ = single_party(lifecycle_source=None)
        with self.assertRaisesRegex(ParticipationRefused,
                                    "LIFECYCLE_SOURCE_NOT_TRUSTED"):
            gate.authorize(request(), cred)
        for bad_source in (None, 7, "source", {"agent-alpha-one":
                                               lifecycle()}):
            with self.subTest(bad_source=bad_source):
                gate, cred, _, _ = single_party(lifecycle_source=bad_source)
                with self.assertRaisesRegex(ParticipationRefused,
                                            "LIFECYCLE_SOURCE_NOT_TRUSTED"):
                    gate.authorize(request(), cred)

    def test_non_callable_source_on_route_refused(self):
        gate, cred, _, _ = single_party(lifecycle_source=42)
        with self.assertRaisesRegex(ParticipationRefused,
                                    "LIFECYCLE_SOURCE_NOT_TRUSTED"):
            gate.route(request(), recipient(), cred)
        self.assertEqual(len(gate.journal.entries()), 0)

    def test_unavailable_state_refused(self):
        # State-source disappearance: the agent vanishes from the source.
        gate, cred, states, _ = single_party()
        states.pop("agent-alpha-one")
        with self.assertRaisesRegex(ParticipationRefused,
                                    "LIFECYCLE_STATE_UNAVAILABLE"):
            gate.authorize(request(), cred)
        with self.assertRaisesRegex(ParticipationRefused,
                                    "LIFECYCLE_STATE_UNAVAILABLE"):
            gate.route(request(), recipient(), cred)
        self.assertEqual(len(gate.journal.entries()), 0)

    def test_malformed_source_responses_refused(self):
        state = lifecycle()
        for garbage in ("registered-now-trust-me", 7, ["registered"], True):
            with self.subTest(garbage=str(garbage)[:40]):
                source = lambda query, g=garbage: copy.deepcopy(g)
                gate, cred, _, _ = single_party(
                    lifecycle_source=source)
                with self.assertRaisesRegex(
                        ParticipationRefused, "LIFECYCLE_STATE_SHAPE_INVALID"):
                    gate.authorize(request(), cred)
        # Right keys, wrong values: the rebuild refuses the value.
        source = lambda query: copy.deepcopy(
            {**state, "lifecycleStatus": "paused"})
        gate, cred, _, _ = single_party(lifecycle_source=source)
        with self.assertRaisesRegex(ObservatoryRefusal,
                                    "LIFECYCLE_STATUS_NOT_ADMITTED"):
            gate.authorize(request(), cred)
        # Right values, wrong kind: the gate rebuilds the record, so a
        # forged kind is caught as a tampered payload.
        source = lambda query: copy.deepcopy(
            {**state, "kind": "agent-attestation-blob"})
        gate, cred, _, _ = single_party(lifecycle_source=source)
        with self.assertRaisesRegex(ParticipationRefused,
                                    "LIFECYCLE_STATE_TAMPERED"):
            gate.authorize(request(), cred)

    def test_state_identity_binding_mismatch_refused(self):
        # The state bound to agent-alpha-one must carry the SAME
        # agent/tenant/owner identity the query pins — per field. For the
        # agentRef case the factory would refuse the record at
        # construction (key mismatch), so a raw source stands in to prove
        # the GATE's own identity check; tenantRef/ownerRef reach the
        # gate through the normal factory.
        for field, value, through_factory in (
                ("tenantRef", "tenant-impersonate", True),
                ("ownerRef", "owner-impersonate", True),
                ("agentRef", "agent-phantom-0001", False)):
            forged = lifecycle()
            forged[field] = value
            with self.subTest(field=field):
                if through_factory:
                    source = synthetic_lifecycle_source(
                        {"agent-alpha-one": forged})
                else:
                    source = (lambda query, forged=forged:
                              copy.deepcopy(forged))
                gate, cred, _, _ = single_party(lifecycle_source=source)
                with self.assertRaisesRegex(
                        ParticipationRefused,
                        "LIFECYCLE_STATE_IDENTITY_MISMATCH"):
                    gate.authorize(request(), cred)
        # An agentRef mismatch cannot even be registered under a foreign
        # key by the trusted source factory.
        with self.assertRaisesRegex(ObservatoryRefusal,
                                    "LIFECYCLE_SOURCE_KEY_MISMATCH"):
            synthetic_lifecycle_source(
                {"agent-alpha-one": lifecycle(agent_ref="agent-phantom-0001")})


class CredentialGenerationTests(unittest.TestCase):
    def test_current_generation_permits(self):
        gate, cred, _, _ = single_party()
        receipt = gate.authorize(request(), cred)
        self.assertEqual(receipt["decision"], "AUTHORIZED_LOCAL_SYNTHETIC")

    def test_older_generation_refused(self):
        # A decision from generation 1 cannot speak for a generation-2
        # credential: agent-supplied staleness claims don't exist; the
        # trusted source simply is at 2.
        decisions = {"agent-alpha-one": decision(generation=1)}
        states = {"agent-alpha-one": lifecycle(generation=2)}
        cred = synthetic_caller_credential("fixture-lifecycle-alpha")
        gate = RegisteredAgentGate(
            trusted_registration_adapter=synthetic_registration_adapter(decisions),
            trusted_caller_verifier=synthetic_caller_verifier({
                cred: {"agentRef": "agent-alpha-one", "tenantRef":
                       "tenant-alpha", "ownerRef": "owner-alpha"}}),
            trusted_lifecycle_source=mutable_lifecycle_source(states),
            now=lambda: _NOW)
        with self.assertRaisesRegex(ParticipationRefused,
                                    "CREDENTIAL_GENERATION_STALE"):
            gate.authorize(request(), cred)

    def test_future_generation_claim_refused(self):
        # A decision claiming generation 3 while the trusted source is at
        # 2 proves nothing — higher is not automatically trusted.
        decisions = {"agent-alpha-one": decision(generation=3)}
        states = {"agent-alpha-one": lifecycle(generation=2)}
        cred = synthetic_caller_credential("fixture-lifecycle-alpha")
        gate = RegisteredAgentGate(
            trusted_registration_adapter=synthetic_registration_adapter(decisions),
            trusted_caller_verifier=synthetic_caller_verifier({
                cred: {"agentRef": "agent-alpha-one", "tenantRef":
                       "tenant-alpha", "ownerRef": "owner-alpha"}}),
            trusted_lifecycle_source=mutable_lifecycle_source(states),
            now=lambda: _NOW)
        with self.assertRaisesRegex(ParticipationRefused,
                                    "CREDENTIAL_GENERATION_NOT_CURRENT"):
            gate.authorize(request(), cred)

    def test_malformed_decision_generation_refused(self):
        # A tampered decision record never reaches the lifecycle stage:
        # the rebuild refuses the value outright.
        gate, cred, _, decisions = single_party()
        gate.trusted_registration_adapter = synthetic_registration_adapter(
            {"agent-alpha-one": {**decisions["agent-alpha-one"],
                                 "credentialGeneration": "2"}})
        with self.assertRaisesRegex(ObservatoryRefusal,
                                    "CREDENTIAL_GENERATION_NOT_ADMITTED"):
            gate.authorize(request(), cred)

    def test_rotation_invalidates_previous_generation_decisions(self):
        gate, cred, states, decisions = single_party()
        first = gate.authorize(request(), cred)
        self.assertEqual(first["decision"], "AUTHORIZED_LOCAL_SYNTHETIC")
        # Rotation: the trusted source moves to generation 3. The OLD
        # decision (generation 2) must stop authorizing immediately.
        states["agent-alpha-one"] = lifecycle(generation=3)
        with self.assertRaisesRegex(ParticipationRefused,
                                    "CREDENTIAL_GENERATION_STALE"):
            gate.authorize(request(), cred)
        with self.assertRaisesRegex(ParticipationRefused,
                                    "CREDENTIAL_GENERATION_STALE"):
            gate.route(request(), recipient(), cred)
        self.assertEqual(len(gate.journal.entries()), 0)
        # Only a NEW adapter decision at the CURRENT generation admits.
        decisions["agent-alpha-one"] = decision(generation=3)
        gate.trusted_registration_adapter = synthetic_registration_adapter(
            decisions)
        second = gate.authorize(request(), cred)
        self.assertEqual(second["decision"], "AUTHORIZED_LOCAL_SYNTHETIC")

    def test_rotated_credentials_not_automatically_trusted(self):
        # A rotation does not hand automatic trust to whoever shows a
        # higher generation: an adapter decision claiming generation 3
        # before the trusted source advances refuses as a future claim.
        decisions = {"agent-alpha-one": decision(generation=3)}
        states = {"agent-alpha-one": lifecycle(generation=2)}
        cred = synthetic_caller_credential("fixture-lifecycle-alpha")
        gate = RegisteredAgentGate(
            trusted_registration_adapter=synthetic_registration_adapter(decisions),
            trusted_caller_verifier=synthetic_caller_verifier({
                cred: {"agentRef": "agent-alpha-one", "tenantRef":
                       "tenant-alpha", "ownerRef": "owner-alpha"}}),
            trusted_lifecycle_source=mutable_lifecycle_source(states),
            now=lambda: _NOW)
        with self.assertRaisesRegex(ParticipationRefused,
                                    "CREDENTIAL_GENERATION_NOT_CURRENT"):
            gate.authorize(request(), cred)


class RevocationEpochTests(unittest.TestCase):
    def _gate(self, decision_record=None, state=None,
              decision_gen=2, decision_epoch=1):
        decisions = {"agent-alpha-one": decision_record
                     or decision(generation=decision_gen,
                                 epoch=decision_epoch)}
        states = {"agent-alpha-one": state or lifecycle()}
        cred = synthetic_caller_credential("fixture-lifecycle-alpha")
        gate = RegisteredAgentGate(
            trusted_registration_adapter=synthetic_registration_adapter(decisions),
            trusted_caller_verifier=synthetic_caller_verifier({
                cred: {"agentRef": "agent-alpha-one", "tenantRef":
                       "tenant-alpha", "ownerRef": "owner-alpha"}}),
            trusted_lifecycle_source=mutable_lifecycle_source(states),
            now=lambda: _NOW)
        return gate, cred, states, decisions

    def test_current_epoch_permits(self):
        gate, cred, _, _ = self._gate()
        receipt = gate.authorize(request(), cred)
        self.assertEqual(receipt["decision"], "AUTHORIZED_LOCAL_SYNTHETIC")

    def test_stale_epoch_refused(self):
        # The trusted source says a revocation already happened (epoch 1);
        # a decision minted before it (epoch 0) must not authorize.
        gate, cred, _, _ = self._gate(decision_epoch=0)
        with self.assertRaisesRegex(ParticipationRefused,
                                    "REVOCATION_EPOCH_STALE"):
            gate.authorize(request(), cred)

    def test_future_epoch_claim_refused(self):
        gate, cred, _, _ = self._gate(decision_epoch=2)
        with self.assertRaisesRegex(ParticipationRefused,
                                    "REVOCATION_EPOCH_NOT_CURRENT"):
            gate.authorize(request(), cred)

    def test_explicit_revocation_refuses(self):
        gate, cred, states, _ = self._gate()
        states["agent-alpha-one"] = lifecycle(status="revoked", epoch=2)
        with self.assertRaisesRegex(ParticipationRefused,
                                    "LIFECYCLE_STATUS_REVOKED"):
            gate.authorize(request(), cred)

    def test_suspension_refuses(self):
        gate, cred, states, _ = self._gate()
        states["agent-alpha-one"] = lifecycle(status="suspended")
        with self.assertRaisesRegex(ParticipationRefused,
                                    "LIFECYCLE_STATUS_SUSPENDED"):
            gate.authorize(request(), cred)

    def test_emergency_disablement_refuses(self):
        gate, cred, states, _ = self._gate()
        states["agent-alpha-one"] = lifecycle(status="disabled", epoch=2)
        with self.assertRaisesRegex(ParticipationRefused,
                                    "LIFECYCLE_STATUS_DISABLED"):
            gate.authorize(request(), cred)
        with self.assertRaisesRegex(ParticipationRefused,
                                    "LIFECYCLE_STATUS_DISABLED"):
            gate.route(request(), recipient(), cred)
        self.assertEqual(len(gate.journal.entries()), 0)

    def test_reactivation_cannot_silently_restore_stale_credentials(self):
        # R1 policy change (review 5756293645, Director-approved): this
        # test previously permitted SAME-EPOCH severe-status recovery —
        # after revoked@2 it admitted a fresh decision at registered@2.
        # The approved severe-status latch makes that rule stricter, and
        # this test was UPDATED to demonstrate it explicitly: a strictly
        # newer revocation epoch (2 -> 3) is now REQUIRED. The old
        # epoch-1 decision still refuses; the same-epoch fresh decision
        # now refuses LIFECYCLE_REACTIVATION_NOT_CURRENT (newly enforced)
        # where REVOCATION_EPOCH_STALE used to fire first; only an
        # epoch-3 source and a fresh epoch-3 decision admit.
        gate, cred, states, decisions = self._gate()
        states["agent-alpha-one"] = lifecycle(status="revoked", epoch=2)
        with self.assertRaisesRegex(ParticipationRefused,
                                    "LIFECYCLE_STATUS_REVOKED"):
            gate.authorize(request(), cred)
        states["agent-alpha-one"] = lifecycle(status="registered", epoch=2)
        with self.assertRaisesRegex(ParticipationRefused,
                                    "LIFECYCLE_REACTIVATION_NOT_CURRENT"):
            gate.authorize(request(), cred)
        # A strictly newer epoch re-registers, but the OLD epoch-1
        # decision still refuses on its own.
        states["agent-alpha-one"] = lifecycle(status="registered", epoch=3)
        with self.assertRaisesRegex(ParticipationRefused,
                                    "REVOCATION_EPOCH_STALE"):
            gate.authorize(request(), cred)
        # Only a fresh decision matching the CURRENT epoch and
        # generation admits.
        decisions["agent-alpha-one"] = decision(generation=2, epoch=3)
        gate.trusted_registration_adapter = synthetic_registration_adapter(
            decisions)
        receipt = gate.authorize(request(), cred)
        self.assertEqual(receipt["decision"], "AUTHORIZED_LOCAL_SYNTHETIC")

    def test_state_rollback_after_revocation_detected(self):
        # The source may not walk the epoch backwards: after the gate saw
        # epoch 2, a source reporting epoch 1 again is a rollback attack.
        gate, cred, states, _ = self._gate()
        states["agent-alpha-one"] = lifecycle(status="revoked", epoch=2)
        with self.assertRaisesRegex(ParticipationRefused,
                                    "LIFECYCLE_STATUS_REVOKED"):
            gate.authorize(request(), cred)
        states["agent-alpha-one"] = lifecycle(status="registered", epoch=1)
        with self.assertRaisesRegex(ParticipationRefused,
                                    "CREDENTIAL_STATE_ROLLBACK"):
            gate.authorize(request(), cred)


class RollbackHighWatermarkTests(unittest.TestCase):
    def test_generation_rollback_refused(self):
        gate, cred, states, decisions = single_party()
        decisions["agent-alpha-one"] = decision(generation=3)
        gate.trusted_registration_adapter = synthetic_registration_adapter(
            decisions)
        states["agent-alpha-one"] = lifecycle(generation=3)
        receipt = gate.authorize(request(), cred)
        self.assertEqual(receipt["decision"], "AUTHORIZED_LOCAL_SYNTHETIC")
        # Now the source walks the generation BACKWARDS.
        states["agent-alpha-one"] = lifecycle(generation=2)
        with self.assertRaisesRegex(ParticipationRefused,
                                    "CREDENTIAL_STATE_ROLLBACK"):
            gate.authorize(request(), cred)

    def test_epoch_rollback_refused(self):
        gate, cred, states, _ = single_party()
        states["agent-alpha-one"] = lifecycle(generation=2, epoch=1)
        gate.authorize(request(), cred)
        states["agent-alpha-one"] = lifecycle(generation=2, epoch=0)
        with self.assertRaisesRegex(ParticipationRefused,
                                    "CREDENTIAL_STATE_ROLLBACK"):
            gate.authorize(request(), cred)

    def test_equal_counters_do_not_trip_the_watermark(self):
        gate, cred, states, _ = single_party()
        gate.authorize(request(), cred)
        states["agent-alpha-one"] = lifecycle(generation=2, epoch=1)
        receipt = gate.authorize(request(), cred)
        self.assertEqual(receipt["decision"], "AUTHORIZED_LOCAL_SYNTHETIC")

    def test_watermark_is_per_agent(self):
        # A rollback for one agent never implicates another.
        gate, cred, states, decisions = single_party()
        states["agent-alpha-one"] = lifecycle(generation=3)
        decisions["agent-alpha-one"] = decision(generation=3)
        gate.trusted_registration_adapter = synthetic_registration_adapter(
            decisions)
        gate.authorize(request(), cred)
        states["agent-alpha-one"] = lifecycle(generation=2)
        with self.assertRaisesRegex(ParticipationRefused,
                                    "CREDENTIAL_STATE_ROLLBACK"):
            gate.authorize(request(), cred)

    def test_rollback_refusal_writes_no_journal_entry(self):
        gate, cred, states, _ = single_party()
        states["agent-alpha-one"] = lifecycle(status="disabled", epoch=3)
        with self.assertRaisesRegex(ParticipationRefused,
                                    "LIFECYCLE_STATUS_DISABLED"):
            gate.route(request(), recipient(), cred)
        states["agent-alpha-one"] = lifecycle(status="disabled", epoch=2)
        with self.assertRaisesRegex(ParticipationRefused,
                                    "CREDENTIAL_STATE_ROLLBACK"):
            gate.route(request(), recipient(), cred)
        self.assertEqual(len(gate.journal.entries()), 0)

    def test_watermark_is_in_memory_only_disclosed(self):
        # The watermark is explicitly NOT durable: a restarted gate loses
        # it. That limitation is documented, not hidden.
        gate, cred, states, _ = single_party()
        decisions3 = {"agent-alpha-one": decision(generation=3, epoch=1)}
        gate.trusted_registration_adapter = synthetic_registration_adapter(
            decisions3)
        states["agent-alpha-one"] = lifecycle(generation=3)
        gate.authorize(request(), cred)
        states["agent-alpha-one"] = lifecycle(generation=2)
        with self.assertRaisesRegex(ParticipationRefused,
                                    "CREDENTIAL_STATE_ROLLBACK"):
            gate.authorize(request(), cred)
        # A NEW gate instance (process restart) has an empty watermark:
        # the same rolled-back state is accepted again there.
        restarted_cred = synthetic_caller_credential("fixture-lifecycle-alpha")
        restarted_states = {"agent-alpha-one": lifecycle(generation=2,
                                                         epoch=0)}
        restarted = RegisteredAgentGate(
            trusted_registration_adapter=synthetic_registration_adapter(
                {"agent-alpha-one": decision(generation=2, epoch=0)}),
            trusted_caller_verifier=synthetic_caller_verifier({
                restarted_cred: {"agentRef": "agent-alpha-one",
                                 "tenantRef": "tenant-alpha",
                                 "ownerRef": "owner-alpha"}}),
            trusted_lifecycle_source=mutable_lifecycle_source(restarted_states),
            now=lambda: _NOW,
            journal=AdmissionJournal())
        receipt = restarted.authorize(request(), restarted_cred)
        self.assertEqual(receipt["decision"], "AUTHORIZED_LOCAL_SYNTHETIC")
        # The in-memory-only limitation is disclosed, not hidden.
        self.assertIn("IN-MEMORY", gate_module.__doc__)
        self.assertIn("durable rollback protection", gate_module.__doc__)
        self.assertIn("IN-MEMORY", admission.__doc__)


class RouteLifecycleTests(unittest.TestCase):
    """Dual-sided delivery controls: EVERY route enforces CURRENT
    lifecycle state for BOTH sender and recipient."""

    def test_baseline_delivery_admits(self):
        gate, cred, _, _ = two_party()
        receipt = gate.route(request(), recipient(), cred)
        self.assertEqual(receipt["decision"], "DELIVERED_LOCAL_SYNTHETIC")
        self.assertFalse(any(receipt["authorityFlags"].values()))
        self.assertEqual(receipt["authorityFlags"], {
            "executionAuthorized": False,
            "toolUseAuthorized": False,
            "paymentAuthorized": False,
            "deploymentAuthorized": False,
            "agentRegistrationChangeAuthorized": False,
            "publicDirectoryExposed": False,
        })

    def test_old_sender_credential_after_rotation_refused(self):
        gate, cred, states, decisions = two_party()
        first = gate.route(request(), recipient(), cred)
        self.assertEqual(first["journalResult"], "recorded")
        states["agent-alpha-one"] = lifecycle(generation=3)
        with self.assertRaisesRegex(ParticipationRefused,
                                    "CREDENTIAL_GENERATION_STALE"):
            gate.route(request(message_id="msg-lc-002",
                               correlation="corr-lc-002"), recipient(), cred)
        self.assertEqual(len(gate.journal.entries()), 1)

    def test_old_recipient_credential_after_rotation_refused(self):
        gate, cred, states, _ = two_party()
        first = gate.route(request(), recipient(), cred)
        self.assertEqual(first["journalResult"], "recorded")
        states["agent-beta-one"] = lifecycle(agent_ref="agent-beta-one",
                                             owner_ref="owner-beta",
                                             generation=3)
        with self.assertRaisesRegex(ParticipationRefused,
                                    "CREDENTIAL_GENERATION_STALE"):
            gate.route(request(message_id="msg-lc-002",
                               correlation="corr-lc-002"), recipient(), cred)
        self.assertEqual(len(gate.journal.entries()), 1)

    def test_revocation_between_consecutive_messages(self):
        gate, cred, states, _ = two_party()
        first = gate.route(request(), recipient(), cred)
        self.assertEqual(first["decision"], "DELIVERED_LOCAL_SYNTHETIC")
        states["agent-alpha-one"] = lifecycle(status="revoked", epoch=2)
        with self.assertRaisesRegex(ParticipationRefused,
                                    "LIFECYCLE_STATUS_REVOKED"):
            gate.route(request(message_id="msg-lc-002",
                               correlation="corr-lc-002"), recipient(), cred)
        self.assertEqual(len(gate.journal.entries()), 1)

    def test_suspension_between_consecutive_messages(self):
        gate, cred, states, _ = two_party()
        gate.route(request(), recipient(), cred)
        states["agent-alpha-one"] = lifecycle(status="suspended")
        with self.assertRaisesRegex(ParticipationRefused,
                                    "LIFECYCLE_STATUS_SUSPENDED"):
            gate.route(request(message_id="msg-lc-002",
                               correlation="corr-lc-002"), recipient(), cred)
        self.assertEqual(len(gate.journal.entries()), 1)

    def test_emergency_disablement_of_recipient_between_messages(self):
        gate, cred, states, _ = two_party()
        gate.route(request(), recipient(), cred)
        states["agent-beta-one"] = lifecycle(agent_ref="agent-beta-one",
                                             owner_ref="owner-beta",
                                             status="disabled", epoch=2)
        with self.assertRaisesRegex(ParticipationRefused,
                                    "LIFECYCLE_STATUS_DISABLED"):
            gate.route(request(message_id="msg-lc-002",
                               correlation="corr-lc-002"), recipient(), cred)
        self.assertEqual(len(gate.journal.entries()), 1)

    def test_state_source_disappearance_between_messages(self):
        gate, cred, states, _ = two_party()
        gate.route(request(), recipient(), cred)
        states.pop("agent-beta-one")
        with self.assertRaisesRegex(ParticipationRefused,
                                    "LIFECYCLE_STATE_UNAVAILABLE"):
            gate.route(request(message_id="msg-lc-002",
                               correlation="corr-lc-002"), recipient(), cred)
        self.assertEqual(len(gate.journal.entries()), 1)

    def test_replayed_message_after_revocation_refused(self):
        # An identical replay must not bypass a revocation that occurred
        # since its original admission — and appends NO journal entry.
        gate, cred, states, _ = two_party()
        req = request()
        first = gate.route(req, recipient(), cred)
        self.assertEqual(first["journalResult"], "recorded")
        states["agent-alpha-one"] = lifecycle(status="revoked", epoch=2)
        with self.assertRaisesRegex(ParticipationRefused,
                                    "LIFECYCLE_STATUS_REVOKED"):
            gate.route(req, recipient(), cred)
        self.assertEqual(len(gate.journal.entries()), 1)

    def test_conflicting_replay_after_revocation_also_refused(self):
        gate, cred, states, _ = two_party()
        gate.route(request(), recipient(), cred)
        states["agent-alpha-one"] = lifecycle(status="revoked", epoch=2)
        with self.assertRaisesRegex(ParticipationRefused,
                                    "LIFECYCLE_STATUS_REVOKED"):
            gate.route(request(body="conflicting content, same id"),
                       recipient(), cred)
        self.assertEqual(len(gate.journal.entries()), 1)

    def test_identical_replay_still_idempotent_when_current(self):
        gate, cred, _, _ = two_party()
        req = request()
        first = gate.route(req, recipient(), cred)
        second = gate.route(req, recipient(), cred)
        self.assertEqual(first["journalResult"], "recorded")
        self.assertEqual(second["journalResult"], "replayed-idempotent")
        self.assertEqual(len(gate.journal.entries()), 1)

    def test_malformed_response_between_messages_refused(self):
        gate, cred, states, _ = two_party()
        gate.route(request(), recipient(), cred)
        states["agent-alpha-one"] = json.dumps({
            "agentRef": "agent-alpha-one", "lifecycleStatus": "registered"})
        with self.assertRaisesRegex(ParticipationRefused,
                                    "LIFECYCLE_STATE_SHAPE_INVALID"):
            gate.route(request(message_id="msg-lc-002",
                               correlation="corr-lc-002"), recipient(), cred)
        self.assertEqual(len(gate.journal.entries()), 1)

    def test_two_owners_same_tenant_still_permitted(self):
        gate, cred, _, _ = two_party()
        receipt = gate.route(request(), recipient(), cred)
        self.assertEqual(receipt["decision"], "DELIVERED_LOCAL_SYNTHETIC")
        self.assertEqual(receipt["recipientRef"], "agent-beta-one")
        self.assertEqual(receipt["tenantRef"], "tenant-alpha")

    def test_cross_tenant_refusal_preserved(self):
        # A THIRD registered agent lives in tenant-beta; delivery of a
        # tenant-alpha message to it is a policy refusal after both
        # lifecycle checks pass individually.
        gate, cred, states, decisions = two_party()
        states["agent-gamma-one"] = lifecycle(agent_ref="agent-gamma-one",
                                              tenant_ref="tenant-beta",
                                              owner_ref="owner-gamma")
        source = synthetic_lifecycle_source(states)
        gate.trusted_lifecycle_source = source
        gate.trusted_registration_adapter = synthetic_registration_adapter(
            {**decisions,
             "agent-gamma-one": decision(agent_ref="agent-gamma-one",
                                         tenant_ref="tenant-beta",
                                         owner_ref="owner-gamma")})
        with self.assertRaisesRegex(ParticipationRefused,
                                    "CROSS_TENANT_DELIVERY_REFUSED"):
            gate.route(request(), recipient(agent_ref="agent-gamma-one",
                                            tenant_ref="tenant-beta",
                                            owner_ref="owner-gamma"), cred)
        self.assertEqual(len(gate.journal.entries()), 0)

    def test_authorize_with_revoked_state_writes_nothing(self):
        gate, cred, states, _ = two_party()
        states["agent-alpha-one"] = lifecycle(status="revoked", epoch=2)
        with self.assertRaisesRegex(ParticipationRefused,
                                    "LIFECYCLE_STATUS_REVOKED"):
            gate.authorize(request(), cred)
        self.assertEqual(len(gate.journal.entries()), 0)


class LifecycleContractTests(unittest.TestCase):
    def test_zero_execution_authority_invariant_preserved(self):
        self.assertEqual(gate_module.A2A_CHAT_HAS_ZERO_EXECUTION_AUTHORITY,
                         "A2A_CHAT_HAS_ZERO_EXECUTION_AUTHORITY")
        self.assertIn("A2A_CHAT_HAS_ZERO_EXECUTION_AUTHORITY",
                      gate_module.__doc__)

    def test_lifecycle_kind_is_distinct_and_declared(self):
        record = lifecycle()
        self.assertEqual(record["kind"], LIFECYCLE_KIND)
        self.assertEqual(LIFECYCLE_KIND,
                         "toadaid-a2a-credential-lifecycle-state")
        self.assertNotEqual(record["kind"], gate_module.GATE_KIND)

    def test_revocation_overrides_prior_approval_declared(self):
        self.assertIn("REVOCATION_OVERRIDES_PRIOR_APPROVAL",
                      gate_module.__doc__)
        self.assertIn("REVOCATION_OVERRIDES_PRIOR_APPROVAL",
                      admission.lifecycle.__doc__)

    def test_no_agent_claim_establishes_current_state_declared(self):
        claim_line = ("No agent-supplied claim can establish its own "
                      "current credential")
        self.assertIn(claim_line, gate_module.__doc__)
        self.assertIn(claim_line, admission.lifecycle.__doc__)

    def test_gate_status_unchanged_not_deployed(self):
        self.assertEqual(gate_module.GATE_STATUS,
                         "LOCAL_SYNTHETIC_ENGINE_NOT_DEPLOYED")

    def test_lifecycle_states_never_carry_execution_authority(self):
        for status in sorted(LIFECYCLE_STATUSES):
            record = lifecycle(status=status)
            self.assertNotIn("authorityFlags", record)


class SevereStatusLatchTests(unittest.TestCase):
    """A2A-P0D-A2-R1 — the severe-status latch (review 5756293645, R1-A).

    Policy (Director-approved): once a VALID lifecycle observation
    reports "revoked" or "disabled" for an identity, the gate refuses
    later "registered" observations unless the trusted source reports a
    STRICTLY newer revocation epoch (LIFECYCLE_REACTIVATION_NOT_CURRENT).
    A generation-only increase is insufficient. Suspension never latches,
    so unchanged-epoch suspension recovery stays legitimate. The latch is
    IN-MEMORY ONLY — it provides no protection against revocations missed
    between observations or across a process restart."""

    def _authorize(self, gate, cred):
        return gate.authorize(request(), cred)

    def test_reactivation_same_epoch_after_revocation_refused(self):
        # Control 1 — registered -> revoked -> registered, same epoch.
        gate, cred, states, _ = single_party()
        self._authorize(gate, cred)
        states["agent-alpha-one"] = lifecycle(status="revoked")
        with self.assertRaisesRegex(ParticipationRefused,
                                    "LIFECYCLE_STATUS_REVOKED"):
            self._authorize(gate, cred)
        states["agent-alpha-one"] = lifecycle(status="registered")
        with self.assertRaisesRegex(ParticipationRefused,
                                    "LIFECYCLE_REACTIVATION_NOT_CURRENT"):
            self._authorize(gate, cred)

    def test_reactivation_same_epoch_after_disablement_refused(self):
        # Control 2 — the same shape with emergency disablement.
        gate, cred, states, _ = single_party()
        self._authorize(gate, cred)
        states["agent-alpha-one"] = lifecycle(status="disabled")
        with self.assertRaisesRegex(ParticipationRefused,
                                    "LIFECYCLE_STATUS_DISABLED"):
            self._authorize(gate, cred)
        states["agent-alpha-one"] = lifecycle(status="registered")
        with self.assertRaisesRegex(ParticipationRefused,
                                    "LIFECYCLE_REACTIVATION_NOT_CURRENT"):
            self._authorize(gate, cred)

    def test_generation_increase_alone_does_not_lift_the_latch(self):
        # Control 3 — gen 3 with the SAME revocation epoch: insufficient.
        gate, cred, states, decisions = single_party()
        self._authorize(gate, cred)
        states["agent-alpha-one"] = lifecycle(status="revoked")  # epoch 1
        with self.assertRaisesRegex(ParticipationRefused,
                                    "LIFECYCLE_STATUS_REVOKED"):
            self._authorize(gate, cred)
        states["agent-alpha-one"] = lifecycle(status="registered",
                                              generation=3)
        decisions["agent-alpha-one"] = decision(generation=3)
        gate.trusted_registration_adapter = synthetic_registration_adapter(
            decisions)
        with self.assertRaisesRegex(ParticipationRefused,
                                    "LIFECYCLE_REACTIVATION_NOT_CURRENT"):
            self._authorize(gate, cred)

    def test_identical_replay_after_same_epoch_reactivation_refused(self):
        # Control 4 — an identical journal replay must not survive a
        # same-epoch severe-status cycle (and appends NO journal entry).
        gate, cred, states, _ = two_party()
        req = request()
        first = gate.route(req, recipient(), cred)
        self.assertEqual(first["journalResult"], "recorded")
        states["agent-alpha-one"] = lifecycle(status="revoked")
        with self.assertRaisesRegex(ParticipationRefused,
                                    "LIFECYCLE_STATUS_REVOKED"):
            gate.route(req, recipient(), cred)
        self.assertEqual(len(gate.journal.entries()), 1)
        states["agent-alpha-one"] = lifecycle(status="registered")
        with self.assertRaisesRegex(ParticipationRefused,
                                    "LIFECYCLE_REACTIVATION_NOT_CURRENT"):
            gate.route(req, recipient(), cred)
        self.assertEqual(len(gate.journal.entries()), 1)

    def test_severe_at_epoch_2_then_registration_at_epoch_2_refused(self):
        # Control 5 — registration AT the severe-observation epoch is not
        # "strictly newer": refused.
        gate, cred, states, _ = single_party()
        self._authorize(gate, cred)
        states["agent-alpha-one"] = lifecycle(status="revoked", epoch=2)
        with self.assertRaisesRegex(ParticipationRefused,
                                    "LIFECYCLE_STATUS_REVOKED"):
            self._authorize(gate, cred)
        states["agent-alpha-one"] = lifecycle(status="registered", epoch=2)
        with self.assertRaisesRegex(ParticipationRefused,
                                    "LIFECYCLE_REACTIVATION_NOT_CURRENT"):
            self._authorize(gate, cred)

    def test_severe_at_epoch_2_then_epoch_3_fresh_decision_admits(self):
        # Control 6 — a strictly newer epoch with a fresh matching
        # decision admits.
        gate, cred, states, decisions = single_party()
        self._authorize(gate, cred)
        states["agent-alpha-one"] = lifecycle(status="revoked", epoch=2)
        with self.assertRaisesRegex(ParticipationRefused,
                                    "LIFECYCLE_STATUS_REVOKED"):
            self._authorize(gate, cred)
        states["agent-alpha-one"] = lifecycle(status="registered", epoch=3)
        decisions["agent-alpha-one"] = decision(generation=2, epoch=3)
        gate.trusted_registration_adapter = synthetic_registration_adapter(
            decisions)
        receipt = self._authorize(gate, cred)
        self.assertEqual(receipt["decision"], "AUTHORIZED_LOCAL_SYNTHETIC")

    def test_old_epoch_2_decision_after_recovery_at_epoch_3_refused(self):
        # Control 7 — the pre-revocation decision stays stale evidence
        # even after legitimate re-registration.
        gate, cred, states, _ = single_party()
        self._authorize(gate, cred)
        states["agent-alpha-one"] = lifecycle(status="revoked", epoch=2)
        with self.assertRaisesRegex(ParticipationRefused,
                                    "LIFECYCLE_STATUS_REVOKED"):
            self._authorize(gate, cred)
        states["agent-alpha-one"] = lifecycle(status="registered", epoch=3)
        with self.assertRaisesRegex(ParticipationRefused,
                                    "REVOCATION_EPOCH_STALE"):
            self._authorize(gate, cred)

    def test_suspension_recovery_unchanged_epoch_admits(self):
        # Control 8 — suspension is NOT severe: trusted-source recovery
        # at an unchanged epoch is legitimate when all else passes.
        gate, cred, states, _ = single_party()
        self._authorize(gate, cred)
        states["agent-alpha-one"] = lifecycle(status="suspended")
        with self.assertRaisesRegex(ParticipationRefused,
                                    "LIFECYCLE_STATUS_SUSPENDED"):
            self._authorize(gate, cred)
        states["agent-alpha-one"] = lifecycle(status="registered")
        receipt = self._authorize(gate, cred)
        self.assertEqual(receipt["decision"], "AUTHORIZED_LOCAL_SYNTHETIC")

    def test_latch_is_in_memory_only_and_disclosed(self):
        # A restarted gate has no latch memory: the limitation is
        # disclosed, not hidden.
        gate, cred, states, _ = single_party()
        self._authorize(gate, cred)
        states["agent-alpha-one"] = lifecycle(status="revoked")
        with self.assertRaisesRegex(ParticipationRefused,
                                    "LIFECYCLE_STATUS_REVOKED"):
            self._authorize(gate, cred)
        resumed_cred = synthetic_caller_credential("fixture-lifecycle-alpha")
        resumed_states = {"agent-alpha-one": lifecycle(status="registered")}
        resumed = RegisteredAgentGate(
            trusted_registration_adapter=synthetic_registration_adapter(
                {"agent-alpha-one": decision()}),
            trusted_caller_verifier=synthetic_caller_verifier({
                resumed_cred: {"agentRef": "agent-alpha-one",
                               "tenantRef": "tenant-alpha",
                               "ownerRef": "owner-alpha"},
            }),
            trusted_lifecycle_source=mutable_lifecycle_source(
                resumed_states),
            now=lambda: _NOW, journal=AdmissionJournal())
        receipt = resumed.authorize(request(), resumed_cred)
        self.assertEqual(receipt["decision"], "AUTHORIZED_LOCAL_SYNTHETIC")
        self.assertIn("IN-MEMORY", gate_module.__doc__)
        self.assertIn("revocations missed", gate_module.__doc__)


class ObservationFreshnessTests(unittest.TestCase):
    """A2A-P0D-A2-R1 — Director-approved observation-freshness policy.

    Trusted-clock window: LIFECYCLE_MAX_OBSERVATION_AGE_SECONDS (300)
    maximum age and LIFECYCLE_MAX_OBSERVATION_FUTURE_SKEW_SECONDS (30)
    maximum future skew, both INCLUSIVE at the exact boundary (exactly
    300 s old and exactly 30 s ahead admit), no grace period. Trusted
    gate configuration — never request-provided values. Timestamp
    validation is not cryptographic evidence authentication."""

    def _gate_with_observation(self, observed):
        states = {"agent-alpha-one": lifecycle(observed=observed)}
        cred = synthetic_caller_credential("fixture-lifecycle-alpha")
        gate = RegisteredAgentGate(
            trusted_registration_adapter=synthetic_registration_adapter(
                {"agent-alpha-one": decision()}),
            trusted_caller_verifier=synthetic_caller_verifier({
                cred: {"agentRef": "agent-alpha-one",
                       "tenantRef": "tenant-alpha",
                       "ownerRef": "owner-alpha"},
            }),
            trusted_lifecycle_source=mutable_lifecycle_source(states),
            now=lambda: _NOW)
        return gate, cred

    def test_freshness_boundary_semantics(self):
        cases = [
            ("exactly 300 seconds old", "2026-11-03T11:55:00Z", None),
            ("301 seconds old", "2026-11-03T11:54:59Z",
             "LIFECYCLE_OBSERVATION_STALE"),
            ("one second old", "2026-11-03T11:59:59Z", None),
            ("exactly 30 seconds in the future", "2026-11-03T12:00:30Z",
             None),
            ("31 seconds in the future", "2026-11-03T12:00:31Z",
             "LIFECYCLE_OBSERVATION_SKEW_EXCEEDED"),
            ("months-old evidence", "2026-01-01T00:00:00Z",
             "LIFECYCLE_OBSERVATION_STALE"),
            ("years-in-future evidence", "2030-01-01T00:00:00Z",
             "LIFECYCLE_OBSERVATION_SKEW_EXCEEDED"),
            ("valid recent evidence", "2026-11-03T11:59:00Z", None),
        ]
        for label, stamp, refusal in cases:
            with self.subTest(observation=label):
                gate, cred = self._gate_with_observation(stamp)
                if refusal is None:
                    receipt = gate.authorize(request(), cred)
                    self.assertEqual(receipt["decision"],
                                     "AUTHORIZED_LOCAL_SYNTHETIC")
                else:
                    with self.assertRaisesRegex(ParticipationRefused,
                                                refusal):
                        gate.authorize(request(), cred)

    def test_stale_observation_refusal_writes_no_journal_entry(self):
        gate, cred, states, _ = two_party()
        states["agent-alpha-one"] = lifecycle(
            observed="2026-01-01T00:00:00Z")
        states["agent-beta-one"] = lifecycle(
            agent_ref="agent-beta-one", owner_ref="owner-beta",
            observed="2026-01-01T00:00:00Z")
        with self.assertRaisesRegex(ParticipationRefused,
                                    "LIFECYCLE_OBSERVATION_STALE"):
            gate.route(request(), recipient(), cred)
        self.assertEqual(len(gate.journal.entries()), 0)

    def test_stale_recipient_refused_independently(self):
        # Sender and recipient must EACH pass freshness: only the
        # recipient's observation is stale here.
        gate, cred, states, _ = two_party()
        states["agent-beta-one"] = lifecycle(
            agent_ref="agent-beta-one", owner_ref="owner-beta",
            observed="2026-01-01T00:00:00Z")
        with self.assertRaisesRegex(ParticipationRefused,
                                    "LIFECYCLE_OBSERVATION_STALE"):
            gate.route(request(), recipient(), cred)
        self.assertEqual(len(gate.journal.entries()), 0)

    def test_missing_clock_refuses(self):
        # The trusted clock is a required seam everywhere lifecycle
        # freshness can be evaluated; without it nothing admits.
        cred = synthetic_caller_credential("fixture-lifecycle-alpha")
        gate = RegisteredAgentGate(
            trusted_registration_adapter=synthetic_registration_adapter(
                {"agent-alpha-one": decision()}),
            trusted_caller_verifier=synthetic_caller_verifier({
                cred: {"agentRef": "agent-alpha-one",
                       "tenantRef": "tenant-alpha",
                       "ownerRef": "owner-alpha"},
            }),
            trusted_lifecycle_source=mutable_lifecycle_source(
                {"agent-alpha-one": lifecycle()}),
            now=None)
        with self.assertRaisesRegex(ParticipationRefused,
                                    "CLOCK_SOURCE_REQUIRED"):
            gate.authorize(request(), cred)

    def test_malformed_observation_stamp_refused_at_model(self):
        # The strict syntax/calendar stamp check keeps firing at the
        # model boundary; freshness recency is a separate, second check.
        states = {"agent-alpha-one": dict(
            lifecycle(), observedAtUtc="not-a-stamp")}
        cred = synthetic_caller_credential("fixture-lifecycle-alpha")
        gate = RegisteredAgentGate(
            trusted_registration_adapter=synthetic_registration_adapter(
                {"agent-alpha-one": decision()}),
            trusted_caller_verifier=synthetic_caller_verifier({
                cred: {"agentRef": "agent-alpha-one",
                       "tenantRef": "tenant-alpha",
                       "ownerRef": "owner-alpha"},
            }),
            trusted_lifecycle_source=mutable_lifecycle_source(states),
            now=lambda: _NOW)
        with self.assertRaisesRegex(ObservatoryRefusal,
                                    "LIFECYCLE_OBSERVED_AT_NOT_ADMITTED"):
            gate.authorize(request(), cred)

    def test_expired_registration_evidence_refused_despite_fresh_lifecycle(self):
        # Decision evidence expiry (P0D-A1) still dominates: fresh
        # lifecycle observation cannot resurrect expired registration
        # evidence. The decision's own observation stamp is 11:59:00Z;
        # its evidence expired a second later, still over the gate's
        # freshness window for the lifecycle record.
        expired_decision = build_registration_decision(
            agent_ref="agent-alpha-one", owner_ref="owner-alpha",
            tenant_ref="tenant-alpha", registration_status="registered",
            credential_generation=2, revocation_epoch=1,
            framework="unspecified",
            adapter_id="synthetic-offline-registration-adapter",
            decision_observed_at_utc="2026-11-03T11:59:00Z",
            evidence_expires_at_utc="2026-11-03T11:59:59Z",
            participation_scopes=("a2a-message-send",
                                  "a2a-message-receive"))
        states = {"agent-alpha-one": lifecycle(observed="2026-11-03T11:59:00Z")}
        cred = synthetic_caller_credential("fixture-lifecycle-alpha")
        gate = RegisteredAgentGate(
            trusted_registration_adapter=synthetic_registration_adapter(
                {"agent-alpha-one": expired_decision}),
            trusted_caller_verifier=synthetic_caller_verifier({
                cred: {"agentRef": "agent-alpha-one",
                       "tenantRef": "tenant-alpha",
                       "ownerRef": "owner-alpha"},
            }),
            trusted_lifecycle_source=mutable_lifecycle_source(states),
            now=lambda: _NOW)
        with self.assertRaisesRegex(ParticipationRefused,
                                    "REGISTRATION_EVIDENCE_EXPIRED"):
            gate.authorize(request(), cred)

    def test_freshness_limits_are_trusted_gate_configuration(self):
        self.assertEqual(
            gate_module.LIFECYCLE_MAX_OBSERVATION_AGE_SECONDS, 300)
        self.assertEqual(
            gate_module.LIFECYCLE_MAX_OBSERVATION_FUTURE_SKEW_SECONDS, 30)
        self.assertIn("cryptographic evidence authentication",
                      gate_module.__doc__)


class IdentityContextIsolationTests(unittest.TestCase):
    """A2A-P0D-A2-R1 mission §4 — tracker-key isolation.

    The watermark and severe-status latch must key on the FULL verified
    identity context (agentRef, tenantRef, ownerRef), not the agentRef
    alone: with an agentRef-only key, two otherwise-valid identities
    sharing an agentRef contaminate each other's trackers (a low-epoch
    state for one identity trips the other's CREDENTIAL_STATE_ROLLBACK;
    a severe latch for one identity blocks the other). The shipped
    synthetic ADAPTER cannot represent two identities under one agentRef
    (its dict is agentRef-keyed), but both the adapter and the lifecycle
    source are INJECTED seams — general implementations may key on the
    full context — so the isolation property is proven here with an
    explicit identity-aware adapter/source pair. Cross-tenant DELIVERY
    refusal is untouched."""

    @staticmethod
    def _cross_identity_gate():
        cred_a = synthetic_caller_credential("probe-r1-alpha")
        cred_b = synthetic_caller_credential("probe-r1-gamma")
        decisions = {
            ("agent-shared-ref", "tenant-alpha", "owner-alpha"):
                decision(agent_ref="agent-shared-ref",
                         tenant_ref="tenant-alpha", owner_ref="owner-alpha",
                         generation=2, epoch=5),
            ("agent-shared-ref", "tenant-beta", "owner-gamma"):
                decision(agent_ref="agent-shared-ref",
                         tenant_ref="tenant-beta", owner_ref="owner-gamma",
                         generation=2, epoch=1),
        }
        states = {
            ("agent-shared-ref", "tenant-alpha", "owner-alpha"):
                lifecycle(agent_ref="agent-shared-ref",
                          tenant_ref="tenant-alpha", owner_ref="owner-alpha",
                          generation=2, epoch=5),
            ("agent-shared-ref", "tenant-beta", "owner-gamma"):
                lifecycle(agent_ref="agent-shared-ref",
                          tenant_ref="tenant-beta", owner_ref="owner-gamma",
                          generation=2, epoch=1),
        }
        adapter = lambda q: copy.deepcopy(
            decisions[(q["agentRef"], q["tenantRef"], q["ownerRef"])])
        source = lambda q: copy.deepcopy(
            states[(q["agentRef"], q["tenantRef"], q["ownerRef"])])
        gate = RegisteredAgentGate(
            trusted_registration_adapter=adapter,
            trusted_caller_verifier=synthetic_caller_verifier({
                cred_a: {"agentRef": "agent-shared-ref",
                         "tenantRef": "tenant-alpha",
                         "ownerRef": "owner-alpha"},
                cred_b: {"agentRef": "agent-shared-ref",
                         "tenantRef": "tenant-beta",
                         "ownerRef": "owner-gamma"},
            }),
            trusted_lifecycle_source=source,
            now=lambda: _NOW)
        return gate, cred_a, cred_b

    def test_shared_agent_ref_has_independent_watermarks(self):
        # The tenant-alpha identity legitimately observed epoch 5; the
        # tenant-beta identity legitimately sits at epoch 1. An
        # agentRef-only key would refuse the second admission with
        # CREDENTIAL_STATE_ROLLBACK — cross-identity contamination.
        gate, cred_a, cred_b = self._cross_identity_gate()
        receipt_a = gate.authorize(request(
            agent_ref="agent-shared-ref", tenant_ref="tenant-alpha",
            owner_ref="owner-alpha"), cred_a)
        self.assertEqual(receipt_a["decision"], "AUTHORIZED_LOCAL_SYNTHETIC")
        receipt_b = gate.authorize(request(
            agent_ref="agent-shared-ref", tenant_ref="tenant-beta",
            owner_ref="owner-gamma"), cred_b)
        self.assertEqual(receipt_b["decision"], "AUTHORIZED_LOCAL_SYNTHETIC")

    def test_shared_agent_ref_has_independent_latches(self):
        # A severe status observed for the tenant-beta identity must not
        # latch the tenant-alpha identity (same agentRef, different
        # owner/tenant).
        gate, cred_a, cred_b = self._cross_identity_gate()
        states = {
            ("agent-shared-ref", "tenant-beta", "owner-gamma"):
                lifecycle(agent_ref="agent-shared-ref",
                          tenant_ref="tenant-beta", owner_ref="owner-gamma",
                          status="revoked", generation=2, epoch=9),
        }
        gate.trusted_lifecycle_source = lambda q: copy.deepcopy(
            states.get((q["agentRef"], q["tenantRef"], q["ownerRef"])))
        with self.assertRaisesRegex(ParticipationRefused,
                                    "LIFECYCLE_STATUS_REVOKED"):
            gate.authorize(request(
                agent_ref="agent-shared-ref", tenant_ref="tenant-beta",
                owner_ref="owner-gamma"), cred_b)
        # The OTHER identity (tenant-alpha) is unaffected: its own valid
        # source state still admits.
        alpha_states = {("agent-shared-ref", "tenant-alpha", "owner-alpha"):
                        lifecycle(agent_ref="agent-shared-ref",
                                  tenant_ref="tenant-alpha",
                                  owner_ref="owner-alpha",
                                  generation=2, epoch=5)}
        gate.trusted_lifecycle_source = lambda q: copy.deepcopy(
            alpha_states.get((q["agentRef"], q["tenantRef"], q["ownerRef"])))
        receipt = gate.authorize(request(
            agent_ref="agent-shared-ref", tenant_ref="tenant-alpha",
            owner_ref="owner-alpha"), cred_a)
        self.assertEqual(receipt["decision"], "AUTHORIZED_LOCAL_SYNTHETIC")


if __name__ == "__main__":
    unittest.main()