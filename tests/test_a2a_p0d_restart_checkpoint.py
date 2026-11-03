"""CUT-A2A-P0D-A3A-20261103 — restart-safe credential-lifecycle checkpoint.

Offline adversarial suite for the OPTIONAL durable checkpoint of the
P0D-A2 admission gate (admission/checkpoint.py): real sqlite3 files in
temporary restricted directories, ACTUAL close/reopen of the database and
construction of NEW gate instances. Under test:

  * validated, FRESH lifecycle observations are durably committed BEFORE
    an admission result can be returned (including a newly severe status
    recorded BEFORE its refusal);
  * rotated generations, bumped revocation epochs and severe-status
    latches survive an ordinary process restart;
  * identity isolation of durable state — full (agentRef, tenantRef,
    ownerRef) keying, cross-tenant refusal intact;
  * persistence failures can never produce a successful admission;
  * the checkpoint is HISTORICAL anti-rollback state only — never a
    lifecycle authority, never durable message history.

Constitutional rules: REVOCATION_OVERRIDES_PRIOR_APPROVAL (every restart
scenario re-proves it), A2A_CHAT_HAS_ZERO_EXECUTION_AUTHORITY (all
receipt flags stay false). NOT DEPLOYED; synthetic offline fixtures
only; scoped to stdlib + the module under test.
"""

import datetime
import os
import shutil
import sqlite3
import tempfile
import threading
import unittest

import admission.checkpoint
import admission.gate
from admission.gate import (
    ParticipationRefused,
    RegisteredAgentGate,
    synthetic_caller_credential,
    synthetic_caller_verifier,
)
from admission.lifecycle import build_lifecycle_state
from admission.model import build_registration_decision
from admission.checkpoint import (
    CHECKPOINT_KIND,
    CHECKPOINT_SCHEMA_VERSION,
    CheckpointRefused,
    LifeCycleCheckpoint,
    provision_checkpoint,
)

_NOW = datetime.datetime(2026, 11, 3, 12, 0, 0)
_OBSERVED = "2026-11-03T11:59:00Z"  # fresh (60 s before _NOW)

_ALL_AUTHORITY_FLAGS = {
    "executionAuthorized", "toolUseAuthorized", "paymentAuthorized",
    "deploymentAuthorized", "agentRegistrationChangeAuthorized",
    "publicDirectoryExposed",
}


def decision(agent_ref="agent-alpha-one", tenant_ref="tenant-alpha",
             owner_ref="owner-alpha", status="registered",
             generation=2, epoch=1):
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
        participation_scopes=("a2a-message-send", "a2a-message-receive"),
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


def request(message_id="msg-cp-001", body="bounded checkpoint message"):
    return {
        "agentRef": "agent-alpha-one",
        "tenantRef": "tenant-alpha",
        "ownerRef": "owner-alpha",
        "participationScope": "a2a-message-send",
        "messageId": message_id,
        "correlationId": "corr-cp-001",
        "occurredAtUtc": "2026-11-03T12:00:00Z",
        "message": {"messageType": "conversation_message", "body": body},
    }


def recipient(agent_ref="agent-beta-one", tenant_ref="tenant-alpha",
              owner_ref="owner-beta"):
    return {"agentRef": agent_ref, "tenantRef": tenant_ref,
            "ownerRef": owner_ref}


class CheckpointWorld:
    """Mutable synthetic trusted seams keyed by the FULL identity triple.

    Unlike the agentRef-keyed factories, this world can represent two
    valid identities that share one agentRef across tenants/owners —
    exactly the isolation surface P0D-A3A must keep durable.
    """

    def __init__(self):
        self.decisions = {}
        self.states = {}

    def add(self, agent_ref, tenant_ref, owner_ref, **kwargs):
        key = (agent_ref, tenant_ref, owner_ref)
        gen = kwargs.get("generation", 2)
        self.decisions[key] = decision(agent_ref=agent_ref,
                                       tenant_ref=tenant_ref,
                                       owner_ref=owner_ref,
                                       generation=gen,
                                       epoch=kwargs.get("epoch", 1))
        self.states[key] = lifecycle(agent_ref=agent_ref,
                                     tenant_ref=tenant_ref,
                                     owner_ref=owner_ref, **kwargs)

    def adapter(self):
        return lambda query: dict(self.decisions.get(
            (query["agentRef"], query["tenantRef"], query["ownerRef"]), {}))

    def source(self):
        return lambda query: dict(self.states.get(
            (query["agentRef"], query["tenantRef"], query["ownerRef"]), {}))


def build_gate(world, checkpoint, cred_label="fixture-checkpoint-alpha"):
    cred = synthetic_caller_credential(cred_label)
    binding = cred  # one credential, bound below
    gate = RegisteredAgentGate(
        trusted_registration_adapter=world.adapter(),
        trusted_caller_verifier=synthetic_caller_verifier({
            cred: {"agentRef": "agent-alpha-one", "tenantRef": "tenant-alpha",
                   "ownerRef": "owner-alpha"},
        }),
        trusted_lifecycle_source=world.source(),
        now=lambda: _NOW,
        trusted_checkpoint=checkpoint,
    )
    return gate, cred


class RestartCheckpointTestCase(unittest.TestCase):
    """Shared restricted temporary directory handling."""

    def checkpoint_dir(self):
        directory = tempfile.mkdtemp(prefix="p0d-a3a-checkpoints-")
        self.addCleanup(shutil.rmtree, directory, ignore_errors=True)
        os.chmod(directory, 0o700)
        return directory

    def provision(self, filename="checkpoint.sqlite3", busy=None):
        path = os.path.join(self.checkpoint_dir(), filename)
        if busy is None:
            checkpoint = provision_checkpoint(path)
        else:
            checkpoint = provision_checkpoint(path, busy_timeout_ms=busy)
        self.addCleanup(checkpoint.close)
        return checkpoint


class CheckpointContractTests(RestartCheckpointTestCase):
    """§3/§4 — versioned schema, explicit provisioning, fail-closed."""

    def test_provision_creates_versioned_schema(self):
        checkpoint = self.provision()
        self.assertEqual(checkpoint.path.endswith(".sqlite3"), True)
        connection = sqlite3.connect(checkpoint.path)
        tables = {row[0] for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'")}
        self.assertIn("checkpoint_meta", tables)
        self.assertIn("lifecycle_checkpoint", tables)
        meta = connection.execute(
            "SELECT kind, schemaVersion FROM checkpoint_meta").fetchone()
        self.assertEqual(meta[0], CHECKPOINT_KIND)
        self.assertEqual(meta[1], CHECKPOINT_SCHEMA_VERSION)
        columns = [row[1] for row in connection.execute(
            "PRAGMA table_info(lifecycle_checkpoint)")]
        self.assertEqual(set(columns), {
            "agentRef", "tenantRef", "ownerRef",
            "highCredentialGeneration", "highRevocationEpoch",
            "severeLatchEpoch"})
        connection.close()

    def test_no_message_body_column_exists(self):
        checkpoint = self.provision()
        connection = sqlite3.connect(checkpoint.path)
        for table in ("checkpoint_meta", "lifecycle_checkpoint"):
            columns = [row[1].lower() for row in connection.execute(
                "PRAGMA table_info(%s)" % table)]
            for banned in ("message", "body", "prompt", "credential",
                           "wallet", "reasoning", "token"):
                self.assertNotIn(banned, columns)
        connection.close()

    def test_open_refuses_missing_database(self):
        path = os.path.join(self.checkpoint_dir(), "absent.db")
        with self.assertRaises(CheckpointRefused) as ctx:
            LifeCycleCheckpoint(path)
        self.assertEqual(ctx.exception.args[0], "CHECKPOINT_NOT_PROVISIONED")

    def test_open_refuses_symlink_path(self):
        checkpoint = self.provision()
        link = os.path.join(self.checkpoint_dir(), "planted-link.db")
        os.symlink(checkpoint.path, link)
        with self.assertRaises(CheckpointRefused) as ctx:
            LifeCycleCheckpoint(link)
        self.assertEqual(ctx.exception.args[0], "CHECKPOINT_PATH_NOT_ADMITTED")
        with self.assertRaises(CheckpointRefused) as ctx:
            provision_checkpoint(link)
        self.assertEqual(ctx.exception.args[0], "CHECKPOINT_PATH_NOT_ADMITTED")

    def test_provision_refuses_relative_and_missing_parent(self):
        with self.assertRaises(CheckpointRefused) as ctx:
            provision_checkpoint("relative-checkpoint.db")
        self.assertEqual(ctx.exception.args[0], "CHECKPOINT_PATH_NOT_ADMITTED")
        with self.assertRaises(CheckpointRefused) as ctx:
            provision_checkpoint(os.path.join(
                self.checkpoint_dir(), "no-such-dir", "cp.db"))
        self.assertEqual(ctx.exception.args[0], "CHECKPOINT_PATH_NOT_ADMITTED")

    def test_provision_refuses_existing_database(self):
        checkpoint = self.provision()
        with self.assertRaises(CheckpointRefused) as ctx:
            provision_checkpoint(checkpoint.path)
        self.assertEqual(ctx.exception.args[0], "CHECKPOINT_PATH_NOT_ADMITTED")

    def test_apply_rejects_malformed_scalars(self):
        checkpoint = self.provision()
        for agent_ref, tenant_ref, owner_ref, status, generation, epoch, code in [
            ("BAD_REF", "tenant-alpha", "owner-alpha", "registered", 2, 1,
             "CHECKPOINT_IDENTITY_NOT_ADMITTED"),
            ("agent-alpha-one", "", "owner-alpha", "registered", 2, 1,
             "CHECKPOINT_IDENTITY_NOT_ADMITTED"),
            ("agent-alpha-one", "tenant-alpha", "owner-alpha", "root", 2, 1,
             "CHECKPOINT_STATUS_NOT_ADMITTED"),
            ("agent-alpha-one", "tenant-alpha", "owner-alpha", "registered",
             True, 1, "CHECKPOINT_COUNTER_NOT_ADMITTED"),
            ("agent-alpha-one", "tenant-alpha", "owner-alpha", "registered",
             "2", 1, "CHECKPOINT_COUNTER_NOT_ADMITTED"),
            ("agent-alpha-one", "tenant-alpha", "owner-alpha", "registered",
             -1, 1, "CHECKPOINT_COUNTER_NOT_ADMITTED"),
        ]:
            with self.assertRaises(CheckpointRefused) as ctx:
                checkpoint.apply_observation(agent_ref, tenant_ref, owner_ref,
                                             status, generation, epoch)
            self.assertEqual(ctx.exception.args[0], code)

    def test_observations_carry_only_the_six_bound_columns(self):
        checkpoint = self.provision()
        checkpoint.apply_observation("agent-alpha-one", "tenant-alpha",
                                     "owner-alpha", "registered", 3, 2)
        connection = sqlite3.connect(checkpoint.path)
        row = connection.execute(
            "SELECT * FROM lifecycle_checkpoint").fetchall()
        connection.close()
        self.assertEqual(len(row), 1)
        self.assertEqual(row[0], ("agent-alpha-one", "tenant-alpha",
                                  "owner-alpha", 3, 2, None))


class RestartRotationTests(RestartCheckpointTestCase):
    """Scenario A — credential rotation survives restart."""

    def test_rollback_after_restart_refused_durably(self):
        checkpoint = self.provision()
        world = CheckpointWorld()
        world.add("agent-alpha-one", "tenant-alpha", "owner-alpha",
                  generation=3, epoch=1)
        gate, cred = build_gate(world, checkpoint)
        receipt = gate.authorize(request(), caller_credential=cred)
        self.assertEqual(receipt["decision"], "AUTHORIZED_LOCAL_SYNTHETIC")
        self.assertEqual(checkpoint.checkpoint_state(
            "agent-alpha-one", "tenant-alpha", "owner-alpha"),
            {"highCredentialGeneration": 3, "highRevocationEpoch": 1,
             "severeLatchEpoch": None})

        # Actual restart: close the database, open a NEW checkpoint
        # handle from the same approved file, and build a NEW gate.
        checkpoint.close()
        reopened = LifeCycleCheckpoint(checkpoint.path)
        self.addCleanup(reopened.close)
        world.states[("agent-alpha-one", "tenant-alpha", "owner-alpha")] = \
            lifecycle(generation=2, epoch=1)  # rolled-back rotation
        gate2, cred2 = build_gate(world, reopened)
        with self.assertRaises(ParticipationRefused) as ctx:
            gate2.authorize(request(message_id="msg-cp-002"),
                            caller_credential=cred2)
        self.assertEqual(ctx.exception.args[0], "CREDENTIAL_STATE_ROLLBACK")
        self.assertEqual(len(gate2.journal.entries()), 0)


class RestartRevocationTests(RestartCheckpointTestCase):
    """Scenario B — revocation survives restart."""

    def test_severe_status_recorded_before_refusal(self):
        checkpoint = self.provision()
        world = CheckpointWorld()
        world.add("agent-alpha-one", "tenant-alpha", "owner-alpha",
                  generation=2, epoch=1)
        gate, cred = build_gate(world, checkpoint)
        gate.authorize(request(), caller_credential=cred)
        world.states[("agent-alpha-one", "tenant-alpha", "owner-alpha")] = \
            lifecycle(status="revoked", generation=2, epoch=2)
        with self.assertRaises(ParticipationRefused) as ctx:
            gate.authorize(request(message_id="msg-cp-002"),
                           caller_credential=cred)
        self.assertEqual(ctx.exception.args[0], "LIFECYCLE_STATUS_REVOKED")
        # The latch is DURABLE before the refusal is returned — the
        # operator can verify it the instant the exception propagates.
        self.assertEqual(checkpoint.checkpoint_state(
            "agent-alpha-one", "tenant-alpha", "owner-alpha"),
            {"highCredentialGeneration": 2, "highRevocationEpoch": 2,
             "severeLatchEpoch": 2})

    def test_same_epoch_reactivation_refused_after_restart(self):
        checkpoint = self.provision()
        world = CheckpointWorld()
        world.add("agent-alpha-one", "tenant-alpha", "owner-alpha",
                  generation=2, epoch=1)
        gate, cred = build_gate(world, checkpoint)
        gate.authorize(request(), caller_credential=cred)
        world.states[("agent-alpha-one", "tenant-alpha", "owner-alpha")] = \
            lifecycle(status="revoked", generation=2, epoch=2)
        with self.assertRaises(ParticipationRefused):
            gate.authorize(request(message_id="msg-cp-002"),
                           caller_credential=cred)

        checkpoint.close()
        reopened = LifeCycleCheckpoint(checkpoint.path)
        self.addCleanup(reopened.close)
        world.states[("agent-alpha-one", "tenant-alpha", "owner-alpha")] = \
            lifecycle(status="registered", generation=2, epoch=2)
        gate2, cred2 = build_gate(world, reopened)
        with self.assertRaises(ParticipationRefused) as ctx:
            gate2.authorize(request(message_id="msg-cp-003"),
                            caller_credential=cred2)
        self.assertEqual(ctx.exception.args[0],
                         "LIFECYCLE_REACTIVATION_NOT_CURRENT")
        self.assertEqual(len(gate2.journal.entries()), 0)


class RestartRecoveryTests(RestartCheckpointTestCase):
    """Scenario C — correct recovery at a strictly newer epoch."""

    def test_recovery_at_newer_epoch_admits_old_decision_refuses(self):
        checkpoint = self.provision()
        world = CheckpointWorld()
        world.add("agent-alpha-one", "tenant-alpha", "owner-alpha",
                  generation=2, epoch=1)
        gate, cred = build_gate(world, checkpoint)
        gate.authorize(request(), caller_credential=cred)
        world.states[("agent-alpha-one", "tenant-alpha", "owner-alpha")] = \
            lifecycle(status="revoked", generation=2, epoch=2)
        with self.assertRaises(ParticipationRefused):
            gate.authorize(request(message_id="msg-cp-002"),
                           caller_credential=cred)

        checkpoint.close()
        reopened = LifeCycleCheckpoint(checkpoint.path)
        self.addCleanup(reopened.close)
        world.states[("agent-alpha-one", "tenant-alpha", "owner-alpha")] = \
            lifecycle(status="registered", generation=2, epoch=3)
        world.decisions[("agent-alpha-one", "tenant-alpha", "owner-alpha")] = \
            decision(generation=2, epoch=3)
        gate2, cred2 = build_gate(world, reopened)
        receipt = gate2.authorize(request(message_id="msg-cp-003"),
                                  caller_credential=cred2)
        self.assertEqual(receipt["decision"], "AUTHORIZED_LOCAL_SYNTHETIC")

        # The OLD epoch-2 decision still refuses after recovery
        # (REVOCATION_OVERRIDES_PRIOR_APPROVAL — durable edition).
        world.states[("agent-alpha-one", "tenant-alpha", "owner-alpha")] = \
            lifecycle(status="registered", generation=2, epoch=3)
        world2_decision = decision(generation=2, epoch=2)
        world.decisions[("agent-alpha-one", "tenant-alpha", "owner-alpha")] = \
            world2_decision
        with self.assertRaises(ParticipationRefused) as ctx:
            gate2.authorize(request(message_id="msg-cp-004"),
                            caller_credential=cred2)
        self.assertEqual(ctx.exception.args[0], "REVOCATION_EPOCH_STALE")


class RestartDisablementTests(RestartCheckpointTestCase):
    """Scenario D — emergency disablement survives restart."""

    def test_disabled_latch_survives_restart_no_same_epoch_recovery(self):
        checkpoint = self.provision()
        world = CheckpointWorld()
        world.add("agent-alpha-one", "tenant-alpha", "owner-alpha",
                  generation=2, epoch=1)
        gate, cred = build_gate(world, checkpoint)
        gate.authorize(request(), caller_credential=cred)
        world.states[("agent-alpha-one", "tenant-alpha", "owner-alpha")] = \
            lifecycle(status="disabled", generation=2, epoch=2)
        with self.assertRaises(ParticipationRefused) as ctx:
            gate.authorize(request(message_id="msg-cp-002"),
                           caller_credential=cred)
        self.assertEqual(ctx.exception.args[0], "LIFECYCLE_STATUS_DISABLED")
        self.assertEqual(checkpoint.checkpoint_state(
            "agent-alpha-one", "tenant-alpha", "owner-alpha")
            ["severeLatchEpoch"], 2)

        checkpoint.close()
        reopened = LifeCycleCheckpoint(checkpoint.path)
        self.addCleanup(reopened.close)
        world.states[("agent-alpha-one", "tenant-alpha", "owner-alpha")] = \
            lifecycle(status="registered", generation=2, epoch=2)
        gate2, cred2 = build_gate(world, reopened)
        with self.assertRaises(ParticipationRefused) as ctx:
            gate2.authorize(request(message_id="msg-cp-003"),
                            caller_credential=cred2)
        self.assertEqual(ctx.exception.args[0],
                         "LIFECYCLE_REACTIVATION_NOT_CURRENT")
        # Generation-only advancement cannot bypass the durable latch.
        world.states[("agent-alpha-one", "tenant-alpha", "owner-alpha")] = \
            lifecycle(status="registered", generation=3, epoch=2)
        with self.assertRaises(ParticipationRefused) as ctx:
            gate2.authorize(request(message_id="msg-cp-004"),
                            caller_credential=cred2)
        self.assertEqual(ctx.exception.args[0],
                         "LIFECYCLE_REACTIVATION_NOT_CURRENT")


class RestartSuspensionTests(RestartCheckpointTestCase):
    """Scenario E — suspension stays distinct and recoverable."""

    def test_suspension_recovery_at_unchanged_epoch_after_restart(self):
        checkpoint = self.provision()
        world = CheckpointWorld()
        world.add("agent-alpha-one", "tenant-alpha", "owner-alpha",
                  generation=2, epoch=1)
        gate, cred = build_gate(world, checkpoint)
        gate.authorize(request(), caller_credential=cred)
        world.states[("agent-alpha-one", "tenant-alpha", "owner-alpha")] = \
            lifecycle(status="suspended", generation=2, epoch=2)
        with self.assertRaises(ParticipationRefused) as ctx:
            gate.authorize(request(message_id="msg-cp-002"),
                           caller_credential=cred)
        self.assertEqual(ctx.exception.args[0], "LIFECYCLE_STATUS_SUSPENDED")
        # Suspension NEVER latches: no severe record must exist.
        self.assertIsNone(checkpoint.checkpoint_state(
            "agent-alpha-one", "tenant-alpha", "owner-alpha")
            ["severeLatchEpoch"])

        checkpoint.close()
        reopened = LifeCycleCheckpoint(checkpoint.path)
        self.addCleanup(reopened.close)
        world.states[("agent-alpha-one", "tenant-alpha", "owner-alpha")] = \
            lifecycle(status="registered", generation=2, epoch=2)
        # Scenario E: recovery is legitimate only if EVERY other admission
        # condition passes — supply the matching epoch-2 decision.
        world.decisions[("agent-alpha-one", "tenant-alpha", "owner-alpha")] = \
            decision(generation=2, epoch=2)
        gate2, cred2 = build_gate(world, reopened)
        receipt = gate2.authorize(request(message_id="msg-cp-003"),
                                  caller_credential=cred2)
        self.assertEqual(receipt["decision"], "AUTHORIZED_LOCAL_SYNTHETIC")


class IdentityIsolationPersistenceTests(RestartCheckpointTestCase):
    """Scenario F — durable state does not leak across identity contexts."""

    def test_shared_agent_ref_durable_states_are_independent(self):
        checkpoint = self.provision()
        world = CheckpointWorld()
        # Two valid identities share an agentRef; owners/tenants differ.
        world.add("agent-shared-ref", "tenant-alpha", "owner-alpha",
                  generation=1, epoch=1)
        world.add("agent-shared-ref", "tenant-beta", "owner-gamma",
                  generation=1, epoch=1)
        cred = synthetic_caller_credential("fixture-checkpoint-shared")

        def gate_for(tenant, owner, cp):
            return RegisteredAgentGate(
                trusted_registration_adapter=world.adapter(),
                trusted_caller_verifier=synthetic_caller_verifier({
                    cred: {"agentRef": "agent-shared-ref",
                           "tenantRef": tenant, "ownerRef": owner},
                }),
                trusted_lifecycle_source=world.source(),
                now=lambda: _NOW,
                trusted_checkpoint=cp,
            )

        gate1 = gate_for("tenant-alpha", "owner-alpha", checkpoint)
        req1 = {
            "agentRef": "agent-shared-ref", "tenantRef": "tenant-alpha",
            "ownerRef": "owner-alpha", "participationScope": "a2a-message-send",
            "messageId": "msg-cp-sh-1", "correlationId": "corr-cp-sh-1",
            "occurredAtUtc": "2026-11-03T12:00:00Z",
            "message": {"messageType": "conversation_message",
                        "body": "bounded shared-ref message"},
        }
        self.assertIsNotNone(gate1.authorize(req1, caller_credential=cred))
        # Identity ONE advances to epoch 3 — independently observed.
        world.states[("agent-shared-ref", "tenant-alpha", "owner-alpha")] = \
            lifecycle(agent_ref="agent-shared-ref", tenant_ref="tenant-alpha",
                      owner_ref="owner-alpha", generation=1, epoch=3)
        world.decisions[("agent-shared-ref", "tenant-alpha", "owner-alpha")] = \
            decision(agent_ref="agent-shared-ref", tenant_ref="tenant-alpha",
                     owner_ref="owner-alpha", generation=1, epoch=3)
        self.assertIsNotNone(gate1.authorize(
            dict(req1, messageId="msg-cp-sh-2"), caller_credential=cred))

        checkpoint.close()
        reopened = LifeCycleCheckpoint(checkpoint.path)
        self.addCleanup(reopened.close)

        # Identity TWO (different owner+tenant, SAME agentRef) is at
        # epoch 1 — the durable epoch-3 record of identity one must
        # NOT trip a rollback for identity two.
        gate2 = gate_for("tenant-beta", "owner-gamma", reopened)
        req2 = {
            "agentRef": "agent-shared-ref", "tenantRef": "tenant-beta",
            "ownerRef": "owner-gamma", "participationScope": "a2a-message-send",
            "messageId": "msg-cp-sh-3", "correlationId": "corr-cp-sh-2",
            "occurredAtUtc": "2026-11-03T12:00:00Z",
            "message": {"messageType": "conversation_message",
                        "body": "bounded other-identity message"},
        }
        self.assertIsNotNone(gate2.authorize(req2, caller_credential=cred))

        # And identity one's severe status stays ITS OWN after restart.
        world.states[("agent-shared-ref", "tenant-alpha", "owner-alpha")] = \
            lifecycle(agent_ref="agent-shared-ref", tenant_ref="tenant-alpha",
                      owner_ref="owner-alpha", status="revoked",
                      generation=1, epoch=4)
        with self.assertRaises(ParticipationRefused) as ctx:
            gate1 = gate_for("tenant-alpha", "owner-alpha", reopened)
            gate1.authorize(dict(req1, messageId="msg-cp-sh-4"),
                            caller_credential=cred)
        self.assertEqual(ctx.exception.args[0], "LIFECYCLE_STATUS_REVOKED")
        gate10 = gate_for("tenant-alpha", "owner-alpha", reopened)
        world.states[("agent-shared-ref", "tenant-alpha", "owner-alpha")] = \
            lifecycle(agent_ref="agent-shared-ref", tenant_ref="tenant-alpha",
                      owner_ref="owner-alpha", status="registered",
                      generation=1, epoch=4)
        with self.assertRaises(ParticipationRefused) as ctx:
            gate10.authorize(dict(req1, messageId="msg-cp-sh-5"),
                             caller_credential=cred)
        self.assertEqual(ctx.exception.args[0],
                         "LIFECYCLE_REACTIVATION_NOT_CURRENT")
        # Identity two remains perfectly admissible at its own epoch.
        self.assertIsNotNone(gate2.authorize(
            dict(req2, messageId="msg-cp-sh-6"), caller_credential=cred))

    def test_cross_tenant_delivery_still_refused_with_checkpoint(self):
        checkpoint = self.provision()
        world = CheckpointWorld()
        world.add("agent-alpha-one", "tenant-alpha", "owner-alpha")
        world.add("agent-beta-one", "tenant-beta", "owner-beta")
        cred = synthetic_caller_credential("fixture-checkpoint-route")
        gate = RegisteredAgentGate(
            trusted_registration_adapter=world.adapter(),
            trusted_caller_verifier=synthetic_caller_verifier({
                cred: {"agentRef": "agent-alpha-one",
                       "tenantRef": "tenant-alpha", "ownerRef": "owner-alpha"},
            }),
            trusted_lifecycle_source=world.source(),
            now=lambda: _NOW,
            trusted_checkpoint=checkpoint,
        )
        with self.assertRaises(ParticipationRefused) as ctx:
            gate.route(request(), recipient("agent-beta-one", "tenant-beta",
                                            "owner-beta"),
                       caller_credential=cred)
        self.assertEqual(ctx.exception.args[0], "CROSS_TENANT_DELIVERY_REFUSED")
        self.assertEqual(len(gate.journal.entries()), 0)


class PersistenceFailureTests(RestartCheckpointTestCase):
    """§7 — persistence failures can never yield successful admission."""

    def _gate_with(self, checkpoint, world=None):
        world = world or CheckpointWorld()
        world.add("agent-alpha-one", "tenant-alpha", "owner-alpha")
        self.addCleanup(world.decisions.clear)
        gate, cred = build_gate(world, checkpoint)
        return gate, cred, world

    def test_closed_checkpoint_refuses_authorization(self):
        checkpoint = self.provision()
        gate, cred, world = self._gate_with(checkpoint)
        checkpoint.close()
        with self.assertRaises(ParticipationRefused) as ctx:
            gate.authorize(request(), caller_credential=cred)
        self.assertEqual(ctx.exception.args[0], "CHECKPOINT_WRITE_FAILED")
        self.assertEqual(len(gate.journal.entries()), 0)

    def test_corrupt_database_refuses_to_open(self):
        checkpoint = self.provision()
        path = checkpoint.path
        checkpoint.close()
        with open(path, "wb") as handle:
            handle.write(b"definitely not a sqlite database header" * 32)
        with self.assertRaises(CheckpointRefused) as ctx:
            LifeCycleCheckpoint(path)
        self.assertEqual(ctx.exception.args[0], "CHECKPOINT_CORRUPT")

    def test_foreign_checkpoint_schema_version_refuses(self):
        checkpoint = self.provision()
        connection = sqlite3.connect(checkpoint.path)
        connection.execute(
            "UPDATE checkpoint_meta SET schemaVersion = '9.9.9'")
        connection.commit()
        connection.close()
        with self.assertRaises(CheckpointRefused) as ctx:
            LifeCycleCheckpoint(checkpoint.path)
        self.assertEqual(ctx.exception.args[0],
                         "CHECKPOINT_SCHEMA_UNSUPPORTED")

    def test_foreign_kind_refuses(self):
        checkpoint = self.provision()
        connection = sqlite3.connect(checkpoint.path)
        connection.execute(
            "UPDATE checkpoint_meta SET kind = 'someone-elses-checkpoint'")
        connection.commit()
        connection.close()
        with self.assertRaises(CheckpointRefused) as ctx:
            LifeCycleCheckpoint(checkpoint.path)
        self.assertEqual(ctx.exception.args[0],
                         "CHECKPOINT_SCHEMA_UNSUPPORTED")

    def test_malformed_record_refuses_to_open(self):
        checkpoint = self.provision()
        checkpoint.apply_observation("agent-alpha-one", "tenant-alpha",
                                     "owner-alpha", "registered", 2, 1)
        connection = sqlite3.connect(checkpoint.path)
        connection.execute(
            "UPDATE lifecycle_checkpoint SET highCredentialGeneration = -5")
        connection.commit()
        connection.close()
        with self.assertRaises(CheckpointRefused) as ctx:
            LifeCycleCheckpoint(checkpoint.path)
        self.assertEqual(ctx.exception.args[0], "CHECKPOINT_RECORD_MALFORMED")

    def test_duplicate_identity_records_cannot_exist(self):
        checkpoint = self.provision()
        connection = sqlite3.connect(checkpoint.path)
        connection.execute(
            "INSERT INTO lifecycle_checkpoint (agentRef, tenantRef, ownerRef,"
            " highCredentialGeneration, highRevocationEpoch,"
            " severeLatchEpoch) VALUES (?, ?, ?, 1, 1, NULL)",
            ("agent-alpha-one", "tenant-alpha", "owner-alpha"))
        connection.commit()
        with self.assertRaises(sqlite3.IntegrityError):
            connection.execute(
                "INSERT INTO lifecycle_checkpoint (agentRef, tenantRef,"
                " ownerRef, highCredentialGeneration, highRevocationEpoch,"
                " severeLatchEpoch) VALUES (?, ?, ?, 1, 1, NULL)",
                ("agent-alpha-one", "tenant-alpha", "owner-alpha"))
        connection.close()
        # The module's own open path still validates the file: the one
        # raw-inserted row holds exactly the recorded values.
        reopened = LifeCycleCheckpoint(checkpoint.path)
        self.addCleanup(reopened.close)
        self.assertEqual(reopened.checkpoint_state(
            "agent-alpha-one", "tenant-alpha", "owner-alpha"),
            {"highCredentialGeneration": 1, "highRevocationEpoch": 1,
             "severeLatchEpoch": None})

    def test_readonly_database_refuses_writes_and_admission(self):
        checkpoint = self.provision()
        gate, cred, world = self._gate_with(checkpoint)
        os.chmod(checkpoint.path, 0o444)
        try:
            # Close the still-writable handle and reopen against the
            # now read-only file: the fresh connection must refuse.
            checkpoint.close()
            readonly = LifeCycleCheckpoint(checkpoint.path)
            self.addCleanup(readonly.close)
            gate, cred, world = self._gate_with(readonly)
            with self.assertRaises(ParticipationRefused) as ctx:
                gate.authorize(request(), caller_credential=cred)
            self.assertEqual(ctx.exception.args[0], "CHECKPOINT_WRITE_FAILED")
        finally:
            os.chmod(checkpoint.path, 0o600)
        self.assertEqual(len(gate.journal.entries()), 0)

    def test_interrupted_transaction_discards_and_recovers(self):
        checkpoint = self.provision()
        checkpoint.apply_observation("agent-alpha-one", "tenant-alpha",
                                     "owner-alpha", "registered", 2, 1)
        # Simulate a writer that dies mid-transaction: the sqlite
        # recovery model must discard the uncommitted row and leave
        # the prior committed state intact after reopen.
        raw = sqlite3.connect(checkpoint.path, isolation_level=None)
        raw.execute("BEGIN IMMEDIATE")
        raw.execute(
            "INSERT INTO lifecycle_checkpoint (agentRef, tenantRef, ownerRef,"
            " highCredentialGeneration, highRevocationEpoch, severeLatchEpoch)"
            " VALUES ('agent-zz-nine', 'tenant-alpha', 'owner-alpha',"
            " 7, 7, NULL)")
        raw.close()  # abandoned transaction, never committed
        reopened = LifeCycleCheckpoint(checkpoint.path)
        self.addCleanup(reopened.close)
        self.assertIsNone(reopened.checkpoint_state(
            "agent-zz-nine", "tenant-alpha", "owner-alpha"))
        self.assertEqual(reopened.checkpoint_state(
            "agent-alpha-one", "tenant-alpha", "owner-alpha"),
            {"highCredentialGeneration": 2, "highRevocationEpoch": 1,
             "severeLatchEpoch": None})

    def test_concurrent_writer_lock_refuses_then_retry_succeeds(self):
        checkpoint = self.provision(busy=50)
        raw = sqlite3.connect(checkpoint.path, isolation_level=None)
        self.addCleanup(raw.close)
        raw.execute("BEGIN IMMEDIATE")  # another instance holds the write
        with self.assertRaises(CheckpointRefused) as ctx:
            checkpoint.apply_observation("agent-alpha-one", "tenant-alpha",
                                         "owner-alpha", "registered", 2, 1)
        self.assertEqual(ctx.exception.args[0], "CHECKPOINT_WRITE_FAILED")
        raw.execute("COMMIT")
        result = checkpoint.apply_observation("agent-alpha-one",
                                              "tenant-alpha", "owner-alpha",
                                              "registered", 2, 1)
        self.assertEqual(result["highCredentialGeneration"], 2)

    def test_concurrent_gate_instances_cannot_both_authorize_stale(self):
        """Four independent checkpoint handles (one per future gate
        instance) race ascending epoch bumps on one shared file. The
        database engine — NOT a process-local Python lock — serializes
        them: every success observes the committed maximum, failures
        refuse, and the durable end state is exactly the global max."""
        checkpoint = self.provision(busy=5000)
        checkpoint.apply_observation("agent-alpha-one", "tenant-alpha",
                                     "owner-alpha", "registered", 1, 1)
        path = checkpoint.path
        checkpoint.close()
        errors, successes = [], []

        def worker(seed):
            try:
                instance = LifeCycleCheckpoint(path)
                try:
                    for epoch in range(seed, seed + 5):
                        try:
                            instance.apply_observation(
                                "agent-alpha-one", "tenant-alpha",
                                "owner-alpha", "registered", 1, epoch)
                            successes.append(("ok", epoch, seed))
                        except CheckpointRefused as refused:
                            # Stale/writer contention => refused, never
                            # authorized from an outdated snapshot.
                            errors.append("refused:" + refused.args[0])
                finally:
                    instance.close()
            except Exception as exc:  # noqa: BLE001 — record and let the
                errors.append("error:%s" % exc)  # assertions fail loudly

        threads = [threading.Thread(target=worker, args=(seed,))
                   for seed in (1, 3, 5, 7)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        reopened = LifeCycleCheckpoint(path)
        self.addCleanup(reopened.close)
        final = reopened.checkpoint_state("agent-alpha-one", "tenant-alpha",
                                          "owner-alpha")
        self.assertEqual(final["highRevocationEpoch"], 11)  # max(seed+4)
        self.assertGreater(len(successes), 0)
        for code in ("CHECKPOINT_CORRUPT", "CHECKPOINT_RECORD_MALFORMED",
                     "CHECKPOINT_SCHEMA_UNSUPPORTED"):
            for entry in errors:
                self.assertNotIn(code, entry)


class DurabilityBoundaryTests(RestartCheckpointTestCase):
    """§7 trust limitation and §8 journal boundary — DISCLOSED, not assumed."""

    def test_whole_database_rollback_is_documented_not_detected(self):
        """The documented trust limitation, demonstrated deliberately:
        SQLite cannot establish that a database was not replaced with an
        older VALID copy. A privileged attacker who copies an earlier
        checkpoint file over it rewinds the record — protection against
        this requires external trust/recovery mechanisms that DO NOT
        EXIST in this offline prototype. This test PINS the disclosure:
        it asserts the rewind succeeds, because that is the boundary of
        the claimed guarantee."""
        checkpoint = self.provision()
        checkpoint.apply_observation("agent-alpha-one", "tenant-alpha",
                                     "owner-alpha", "registered", 2, 1)
        path = checkpoint.path
        with open(path, "rb") as handle:
            older = handle.read()
        checkpoint.apply_observation("agent-alpha-one", "tenant-alpha",
                                     "owner-alpha", "registered", 3, 3)
        checkpoint.close()
        with open(path, "wb") as handle:
            handle.write(older)  # privileged whole-database rollback
        reopened = LifeCycleCheckpoint(path)
        self.addCleanup(reopened.close)
        self.assertEqual(reopened.checkpoint_state(
            "agent-alpha-one", "tenant-alpha", "owner-alpha"),
            {"highCredentialGeneration": 2, "highRevocationEpoch": 1,
             "severeLatchEpoch": None})

    def test_journal_stays_in_memory_and_metadata_only(self):
        """P0D-A3A does NOT make the journal durable: delivery results are
        still NOT recorded in the checkpoint, and a restarted gate has NO
        replay history (the gap between a durable lifecycle checkpoint
        and recorded delivery results is explicitly asserted)."""
        checkpoint = self.provision()
        world = CheckpointWorld()
        world.add("agent-alpha-one", "tenant-alpha", "owner-alpha")
        world.add("agent-beta-one", "tenant-alpha", "owner-beta")
        cred = synthetic_caller_credential("fixture-checkpoint-journal")
        gate = RegisteredAgentGate(
            trusted_registration_adapter=world.adapter(),
            trusted_caller_verifier=synthetic_caller_verifier({
                cred: {"agentRef": "agent-alpha-one",
                       "tenantRef": "tenant-alpha", "ownerRef": "owner-alpha"},
            }),
            trusted_lifecycle_source=world.source(),
            now=lambda: _NOW,
            trusted_checkpoint=checkpoint,
        )
        receipt = gate.route(request(), recipient("agent-beta-one",
                                                  "tenant-alpha",
                                                  "owner-beta"),
                             caller_credential=cred)
        self.assertEqual(receipt["decision"], "DELIVERED_LOCAL_SYNTHETIC")
        self.assertEqual(receipt["journalResult"], "recorded")
        self.assertEqual(len(gate.journal.entries()), 1)
        # The durable checkpoint holds ONLY lifecycle anti-rollback
        # state — no delivery result, no message metadata whatsoever.
        connection = sqlite3.connect(checkpoint.path)
        rows = connection.execute(
            "SELECT * FROM lifecycle_checkpoint").fetchall()
        connection.close()
        for row in rows:
            for value in row:
                if isinstance(value, str):
                    self.assertNotIn("msg-cp-001", value)
        checkpoint.close()
        reopened_gate = RegisteredAgentGate(
            trusted_registration_adapter=world.adapter(),
            trusted_caller_verifier=synthetic_caller_verifier({
                cred: {"agentRef": "agent-alpha-one",
                       "tenantRef": "tenant-alpha", "ownerRef": "owner-alpha"},
            }),
            trusted_lifecycle_source=world.source(),
            now=lambda: _NOW,
            trusted_checkpoint=LifeCycleCheckpoint(checkpoint.path),
        )
        # The restarted gate restored NO replay history: the identical
        # delivery would be journaled as a NEW entry (in-memory only).
        self.assertEqual(len(reopened_gate.journal.entries()), 0)

    def test_disclosure_documentation_assertions(self):
        gate_doc = admission.gate.__doc__ or ""
        checkpoint_doc = admission.checkpoint.__doc__ or ""
        combined = gate_doc + checkpoint_doc
        self.assertIn("NOT durable message history", combined)
        self.assertIn("whole-database rollback", combined)
        self.assertIn("NOT a lifecycle authority", combined)
        # the path checks are NOT atomic with the open (check-vs-open
        # race must be disclosed, never claimed away)
        self.assertIn("NOT atomic with the open", checkpoint_doc)


# imported last so the docstring assertion above can reference the
# module object without touching gate's import cycle assumptions


class InMemoryModeParityTests(RestartCheckpointTestCase):
    """Without an injected checkpoint, the gate MUST behave exactly as
    in P0D-A2 (backward compatibility of the synthetic in-memory mode)."""

    def test_no_checkpoint_means_in_memory_watermark_and_latch(self):
        world = CheckpointWorld()
        world.add("agent-alpha-one", "tenant-alpha", "owner-alpha",
                  generation=2, epoch=1)
        cred = synthetic_caller_credential("fixture-checkpoint-legacy")
        gate = RegisteredAgentGate(
            trusted_registration_adapter=world.adapter(),
            trusted_caller_verifier=synthetic_caller_verifier({
                cred: {"agentRef": "agent-alpha-one",
                       "tenantRef": "tenant-alpha", "ownerRef": "owner-alpha"},
            }),
            trusted_lifecycle_source=world.source(),
            now=lambda: _NOW,
        )
        self.assertIsNotNone(gate.authorize(request(), caller_credential=cred))
        world.states[("agent-alpha-one", "tenant-alpha", "owner-alpha")] = \
            lifecycle(status="revoked", generation=2, epoch=2)
        with self.assertRaises(ParticipationRefused):
            gate.authorize(request(message_id="msg-cp-002"),
                           caller_credential=cred)
        world.states[("agent-alpha-one", "tenant-alpha", "owner-alpha")] = \
            lifecycle(status="registered", generation=2, epoch=2)
        with self.assertRaises(ParticipationRefused) as ctx:
            gate.authorize(request(message_id="msg-cp-003"),
                           caller_credential=cred)
        self.assertEqual(ctx.exception.args[0],
                         "LIFECYCLE_REACTIVATION_NOT_CURRENT")


def _child_process_racer(path, seed, outcome_pipe):
    """ONE SEPARATE OS PROCESS racing a shared checkpoint file.

    Opens its OWN sqlite connection (never inherited from the parent),
    applies its own ascending epoch lane, and reports each outcome as
    ("ok", epoch) or ("refused", code). Purpose: demonstrate that
    serialization is provided by the DATABASE ENGINE across genuinely
    independent processes — not by Python threads or a process-local
    lock (Director review question 2026-11-03: threads are NOT multi-
    process evidence)."""
    try:
        instance = LifeCycleCheckpoint(path)
        try:
            for epoch in range(seed, seed + 4):
                try:
                    instance.apply_observation(
                        "agent-alpha-one", "tenant-alpha",
                        "owner-alpha", "registered", 1, epoch)
                    outcome_pipe.send(("ok", epoch))
                except CheckpointRefused as refused:
                    outcome_pipe.send(("refused", refused.args[0]))
        finally:
            instance.close()
    except Exception as exc:  # reported; the parent asserts on it
        outcome_pipe.send(("error", repr(exc)))


def _child_process_lock_holder(path, control_pipe):
    """ONE SEPARATE OS PROCESS holding the database write lock
    (raw BEGIN IMMEDIATE) until an explicit release arrives."""
    try:
        connection = sqlite3.connect(path, isolation_level=None)
        connection.execute("PRAGMA busy_timeout = 5000")
        connection.execute("BEGIN IMMEDIATE")
        control_pipe.send("locked")
        control_pipe.recv()  # blocks until the parent orders release
        connection.execute("ROLLBACK")
        connection.close()
    except Exception as exc:  # noqa: BLE001
        control_pipe.send(("error", repr(exc)))


if hasattr(os, "fork"):
    import multiprocessing

    class MultiprocessConcurrencyTests(RestartCheckpointTestCase):
        """Cross-PROCESS qualification — deliberately distinct from the
        in-process four-thread race (PersistenceFailureTests). Separate
        OS PROCESSES with separate sqlite connections serialize through
        BEGIN IMMEDIATE at the database level. Bounded: one shared
        file, four children, small epoch lanes, fork context."""

        def test_separate_processes_serialize_shared_checkpoint(self):
            checkpoint = self.provision(busy=5000)
            identity = ("agent-alpha-one", "tenant-alpha", "owner-alpha")
            checkpoint.apply_observation(*identity, "registered", 1, 1)
            path = checkpoint.path
            checkpoint.close()  # the parent holds NO open handle across fork
            context = multiprocessing.get_context("fork")
            pipes, processes = [], []
            for seed in (2, 4, 6, 8):
                parent_end, child_end = context.Pipe(duplex=False)
                process = context.Process(
                    target=_child_process_racer,
                    args=(path, seed, child_end))
                process.start()
                child_end.close()
                pipes.append(parent_end)
                processes.append(process)
            for process in processes:
                process.join(timeout=30)
                self.assertEqual(process.exitcode, 0)
            outcomes = []
            for parent_end in pipes:
                while True:
                    try:
                        outcomes.append(parent_end.recv())
                    except EOFError:
                        break
                parent_end.close()
            self.assertEqual(len(outcomes), 16)
            self.assertEqual(
                {kind for kind, _ in outcomes}, {"ok", "refused"})
            accepted = {epoch for kind, epoch in outcomes if kind == "ok"}
            refused_codes = {code for kind, code in outcomes
                             if kind == "refused"}
            self.assertEqual(refused_codes, {"CREDENTIAL_STATE_ROLLBACK"})
            self.assertIn(11, accepted)  # lane (8..11) fully serialized
            reopened = LifeCycleCheckpoint(path)
            self.addCleanup(reopened.close)
            self.assertEqual(
                reopened.checkpoint_state(*identity),
                {"highCredentialGeneration": 1,
                 "highRevocationEpoch": 11,  # the GLOBAL maximum survives
                 "severeLatchEpoch": None})

        def test_cross_process_write_lock_yields_write_failed(self):
            checkpoint = self.provision(busy=100)
            identity = ("agent-alpha-one", "tenant-alpha", "owner-alpha")
            checkpoint.apply_observation(*identity, "registered", 1, 1)
            context = multiprocessing.get_context("fork")
            parent_end, child_end = context.Pipe(duplex=True)
            process = context.Process(
                target=_child_process_lock_holder,
                args=(checkpoint.path, child_end))
            process.start()
            child_end.close()
            self.assertEqual(parent_end.recv(), "locked")
            with self.assertRaises(CheckpointRefused) as ctx:
                checkpoint.apply_observation(*identity, "registered", 1, 2)
            self.assertEqual(ctx.exception.args[0],
                             "CHECKPOINT_WRITE_FAILED")
            parent_end.send("release")
            parent_end.close()
            process.join(timeout=30)
            self.assertEqual(process.exitcode, 0)
            # after the foreign writer releases the write lock, the SAME
            # open handle makes progress again — refuse, never guess
            checkpoint.apply_observation(*identity, "registered", 1, 2)
            self.assertEqual(
                checkpoint.checkpoint_state(*identity)["highRevocationEpoch"],
                2)


if __name__ == "__main__":
    unittest.main()