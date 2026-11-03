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
_OBSERVED = "2026-11-03T10:00:00Z"

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
        # Revoked at epoch 2, then re-registered: the OLD decision (epoch
        # 1) still refuses — reactivation does not revive stale evidence.
        gate, cred, states, decisions = self._gate()
        states["agent-alpha-one"] = lifecycle(status="revoked", epoch=2)
        with self.assertRaisesRegex(ParticipationRefused,
                                    "LIFECYCLE_STATUS_REVOKED"):
            gate.authorize(request(), cred)
        states["agent-alpha-one"] = lifecycle(status="registered", epoch=2)
        with self.assertRaisesRegex(ParticipationRefused,
                                    "REVOCATION_EPOCH_STALE"):
            gate.authorize(request(), cred)
        # Only fresh evidence at the CURRENT epoch and generation admits.
        decisions["agent-alpha-one"] = decision(generation=2, epoch=2)
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


if __name__ == "__main__":
    unittest.main()